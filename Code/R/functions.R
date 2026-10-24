# Funzioni del business case. Nessuna dipendenza esterna.
market_map <- c(ITALY = "MkIndex_EE_ITA_ICE", GERMANYDE = "MkIndex_EE_GER_DE_ICE",
                FRANCE = "MkIndex_EE_FRA_ICE", SPAIN = "MkIndex_EE_SPA_ICE")
deal_columns <- c("business_unit", "DATA", "ORA", "proposer_description", "counterparty",
                  "purpose", "market", "commodity", "IMPORTO", "VOLUME")
curve_columns <- c("DDATE", "HOUR", unname(market_map))

assert <- function(ok, message) {
  if (!isTRUE(ok)) stop(message, call. = FALSE)
}
near <- function(x, y) isTRUE(all.equal(x, y, tolerance = 1e-12, check.attributes = FALSE))
blank <- function(x) is.na(x) | trimws(x) == ""

read_source <- function(path, required) {
  assert(file.exists(path), paste("File assente:", path))
  # Tutti i campi originali restano testo, inclusi decimali e zeri iniziali.
  x <- read.table(path, header = TRUE, sep = ";", quote = '"', dec = ",",
                  colClasses = "character", na.strings = NULL, check.names = FALSE,
                  comment.char = "", strip.white = FALSE, fill = FALSE,
                  fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE)
  assert(!anyDuplicated(names(x)), "Intestazioni duplicate nel file di input")
  assert(setequal(names(x), required), paste("Schema inatteso:", basename(path)))
  assert(nrow(x) > 0L, paste("File vuoto:", path))
  x
}

parse_decimal <- function(x) {
  good <- !blank(x) & grepl("^[+-]?[0-9]+(,[0-9]+)?$", x)
  out <- rep(NA_real_, length(x))
  out[good] <- suppressWarnings(as.numeric(sub(",", ".", x[good], fixed = TRUE)))
  out[!is.finite(out)] <- NA_real_
  out
}
parse_hour <- function(x) {
  out <- parse_decimal(x)
  out[!grepl("^[0-9]+$", x) | is.na(out) | out < 1 | out > 25] <- NA_real_
  as.integer(out)
}
parse_date <- function(x) {
  out <- suppressWarnings(as.Date(x, format = "%d/%m/%Y"))
  valid <- !is.na(out) & !blank(x) & grepl("^[0-9]{2}/[0-9]{2}/[0-9]{4}$", x)
  valid[valid] <- format(out[valid], "%d/%m/%Y") == x[valid]
  out[!valid] <- as.Date(NA)
  out
}

# Codifica senza collisioni anche se una categoria contenesse separatori.
encode_field <- function(x) {
  x <- as.character(x)
  ifelse(is.na(x), "N;", paste0("V", nchar(x, type = "bytes"), ":", x, ";"))
}
make_key <- function(...) do.call(paste0, lapply(list(...), encode_field))

prepare_deals <- function(raw) {
  d <- raw
  d$deal_row_id <- seq_len(nrow(d)) # Posizione nel file, NON identificativo di contratto.
  d$delivery_date <- parse_date(d$DATA)
  d$delivery_hour <- parse_hour(d$ORA)
  d$importo_value <- parse_decimal(d$IMPORTO)
  d$volume_value <- parse_decimal(d$VOLUME)
  d$direction <- unname(c(Buy = -1, Sell = 1)[d$purpose])
  d$curve_index_expected <- unname(market_map[d$market])
  d
}

curves_to_long <- function(raw) {
  date <- parse_date(raw$DDATE)
  hour <- parse_hour(raw$HOUR)
  assert(!anyNA(date) && !anyNA(hour), "Chiave curva non valida: correggere data/ora alla fonte")
  long <- do.call(rbind, lapply(names(market_map), function(mkt) {
    idx <- market_map[[mkt]]
    data.frame(curve_row_id = seq_len(nrow(raw)), DDATE = raw$DDATE,
               HOUR = raw$HOUR, delivery_date = date, delivery_hour = hour,
               market = mkt, curve_index = idx, market_price_raw = raw[[idx]],
               market_price = parse_decimal(raw[[idx]]), stringsAsFactors = FALSE)
  }))
  rownames(long) <- NULL
  key <- make_key(long$delivery_date, long$delivery_hour, long$market)
  if (anyDuplicated(key)) {
    bad <- which(duplicated(key) | duplicated(key, fromLast = TRUE))
    stop(paste("Chiave curva data+ora+mercato duplicata; nessuna scelta arbitraria. Righe long:",
               paste(head(bad, 10), collapse = ", ")), call. = FALSE)
  }
  long
}

enrich_deals <- function(d, long) {
  assert(!anyDuplicated(make_key(long$delivery_date, long$delivery_hour, long$market)),
         "Join rifiutato: chiave curva duplicata")
  key <- make_key(d$delivery_date, d$delivery_hour, d$market)
  hit <- match(key, make_key(long$delivery_date, long$delivery_hour, long$market))
  invalid_key <- is.na(d$delivery_date) | is.na(d$delivery_hour) | is.na(d$curve_index_expected)
  hit[invalid_key] <- NA_integer_
  out <- d
  out$curve_match_count <- as.integer(!is.na(hit))
  out$curve_row_id <- long$curve_row_id[hit]
  out$DDATE <- long$DDATE[hit]
  out$HOUR <- long$HOUR[hit]
  out$curve_index <- long$curve_index[hit]
  out$market_price_raw <- long$market_price_raw[hit]
  out$market_price <- long$market_price[hit]
  out$match_status <- ifelse(invalid_key, "invalid_delivery_key_or_market",
                            ifelse(is.na(hit), "no_curve_match",
                                   ifelse(is.na(out$market_price), "matched_missing_or_invalid_price", "matched")))
  assert(nrow(out) == nrow(d), "Il join ha cambiato il numero di righe")
  assert(identical(out[deal_columns], d[deal_columns]), "Il join ha modificato gli originali")
  assert(identical(out$importo_value, d$importo_value) && identical(out$volume_value, d$volume_value),
         "Il join ha modificato importi o volumi")
  out
}

calculate_pnl <- function(d) {
  d$pnl_applicable <- d$commodity == "ENERGY"
  issues <- rep("", nrow(d))
  add_issue <- function(mask, label) {
    mask[is.na(mask)] <- TRUE
    issues[mask] <<- ifelse(issues[mask] == "", label, paste(issues[mask], label, sep = "|"))
  }
  add_issue(is.na(d$delivery_date), "invalid_date")
  add_issue(is.na(d$delivery_hour), "invalid_hour")
  add_issue(is.na(d$direction), "unknown_purpose")
  add_issue(is.na(d$curve_index_expected), "unknown_market")
  add_issue(!d$commodity %in% c("ENERGY", "SERVICE_POWER"), "unknown_commodity")
  add_issue(is.na(d$importo_value), "missing_or_invalid_importo")
  add_issue(is.na(d$volume_value), "missing_or_invalid_volume")
  add_issue(!is.na(d$volume_value) & d$volume_value <= 0, "nonpositive_volume")
  add_issue(blank(d$counterparty) | blank(d$business_unit) | blank(d$proposer_description), "missing_dimension")
  add_issue(d$match_status != "matched", "curve_unavailable")
  d$row_problem <- issues != ""
  d$issue_codes <- ifelse(d$row_problem, issues, "OK")
  valid_contract <- d$pnl_applicable & !is.na(d$importo_value) & !is.na(d$volume_value) &
    d$volume_value > 0 & !is.na(d$direction)
  d$contract_price <- NA_real_
  d$contract_price[valid_contract] <- d$importo_value[valid_contract] /
    (d$direction[valid_contract] * d$volume_value[valid_contract])
  d$pnl_calculable <- d$pnl_applicable & !d$row_problem
  d$market_value_signed <- d$pnl <- rep(NA_real_, nrow(d))
  i <- d$pnl_calculable
  d$market_value_signed[i] <- d$direction[i] * d$volume_value[i] * d$market_price[i]
  d$pnl[i] <- d$importo_value[i] - d$market_value_signed[i]
  d$pnl_status <- ifelse(!d$pnl_applicable, "not_applicable_commodity",
                         ifelse(i, "calculated", "not_calculable_data_issue"))
  # Controllo della formula equivalente, indipendente dalla sottrazione dei valori.
  expected <- d$direction[i] * (d$contract_price[i] - d$market_price[i]) * d$volume_value[i]
  assert(near(d$pnl[i], expected), "Formule P&L non coerenti")
  assert(all(is.finite(d$pnl[i])), "Overflow nel calcolo P&L")
  d
}

strict_sum <- function(x, empty = NA_real_) {
  if (!length(x)) return(empty)
  if (any(!is.finite(x))) return(NA_real_)
  sum(x)
}

contractual_statement <- function(d) {
  energy_sell <- d$commodity == "ENERGY" & d$purpose == "Sell"
  energy_buy <- d$commodity == "ENERGY" & d$purpose == "Buy"
  service_sell <- d$commodity == "SERVICE_POWER" & d$purpose == "Sell"
  mapped <- energy_sell | energy_buy | service_sell
  revenues <- strict_sum(d$importo_value[energy_sell], empty = 0)
  costs <- -strict_sum(d$importo_value[energy_buy], empty = 0)
  services <- strict_sum(d$importo_value[service_sell], empty = 0)
  # Un eventuale acquisto di servizi o una nuova categoria richiede una voce dedicata.
  margin <- if (all(mapped)) revenues + services - costs else NA_real_
  balance <- strict_sum(d$importo_value)
  if (all(mapped)) assert(near(margin, balance), "Bozza CE non riconciliata con il perimetro classificato")
  list(revenue_energy = revenues, cost_energy = costs, revenue_service = services,
       known_margin = margin, balance = balance, n_unclassified = sum(!mapped))
}

monthly_summary <- function(d) {
  year <- as.integer(format(d$delivery_date, "%Y"))
  month <- as.integer(format(d$delivery_date, "%m"))
  key <- make_key(year, month, d$counterparty, d$purpose, d$market)
  groups <- split(seq_len(nrow(d)), key)
  rows <- lapply(groups, function(ix) {
    x <- d[ix, , drop = FALSE]
    en <- x$commodity == "ENERGY"
    sv <- x$commodity == "SERVICE_POWER"
    ok <- x$pnl_calculable
    volumes <- x$volume_value[en]
    volumes[!is.na(volumes) & volumes <= 0] <- NA_real_
    data.frame(anno = year[ix[1]], mese = month[ix[1]], counterparty = x$counterparty[1],
               purpose = x$purpose[1], market = x$market[1], n_rows = nrow(x),
               importo_total = strict_sum(x$importo_value), n_energy = sum(en),
               volume_energy = strict_sum(volumes),
               market_value_signed_energy = strict_sum(x$market_value_signed[en]),
               pnl_energy = strict_sum(x$pnl[en]), n_service_power = sum(sv),
               importo_service_power = strict_sum(x$importo_value[sv], empty = 0),
               n_pnl_calculable = sum(ok), n_problem_rows = sum(x$row_problem),
               n_energy_not_calculable = sum(en & !ok), n_pnl_not_applicable = sum(!en),
               n_curve_unavailable = sum(x$match_status != "matched"),
               pnl_energy_calculable_subtotal = strict_sum(x$pnl[ok]),
               stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out <- out[order(out$anno, out$mese, out$counterparty, out$purpose, out$market, na.last = TRUE), ]
  rownames(out) <- NULL
  assert(!anyDuplicated(out[c("anno", "mese", "counterparty", "purpose", "market")]), "Chiave mensile duplicata")
  assert(sum(out$n_rows) == nrow(d), "Riconciliazione mensile: numero righe")
  out
}

reconcile_monthly <- function(d, m) {
  assert(sum(m$n_rows) == nrow(d), "Totale righe mensili errato")
  assert(sum(m$n_pnl_calculable) == sum(d$pnl_calculable), "Copertura P&L mensile errata")
  assert(sum(m$n_problem_rows) == sum(d$row_problem), "Conteggio problemi mensile errato")
  checks <- list(importo_total = d$importo_value,
                 volume_energy = d$volume_value[d$commodity == "ENERGY"],
                 market_value_signed_energy = d$market_value_signed[d$commodity == "ENERGY"],
                 pnl_energy = d$pnl[d$commodity == "ENERGY"],
                 importo_service_power = d$importo_value[d$commodity == "SERVICE_POWER"])
  for (nm in names(checks)) {
    mask <- if (nm %in% c("volume_energy", "market_value_signed_energy", "pnl_energy")) m$n_energy > 0 else rep(TRUE, nrow(m))
    # Il confronto globale serve quando il perimetro e' interamente valido.
    if (all(is.finite(checks[[nm]])) && all(is.finite(m[[nm]][mask])))
      assert(near(strict_sum(checks[[nm]], empty = 0), strict_sum(m[[nm]][mask], empty = 0)),
             paste("Riconciliazione fallita:", nm))
  }
  # Verifica indipendente per gruppo tramite rowsum, invece di richiamare l'aggregatore.
  detail_key <- make_key(as.integer(format(d$delivery_date, "%Y")),
                         as.integer(format(d$delivery_date, "%m")), d$counterparty, d$purpose, d$market)
  monthly_key <- make_key(m$anno, m$mese, m$counterparty, m$purpose, m$market)
  group_id <- match(detail_key, monthly_key)
  assert(!anyNA(group_id), "Un deal e' assente dai gruppi mensili")
  en <- d$commodity == "ENERGY"
  sv <- d$commodity == "SERVICE_POWER"
  volume <- d$volume_value
  volume[!is.na(volume) & volume <= 0] <- NA_real_
  contributions <- cbind(n_rows = 1, importo_total = d$importo_value, n_energy = as.integer(en),
                         volume_energy = ifelse(en, volume, 0),
                         market_value_signed_energy = ifelse(en, d$market_value_signed, 0),
                         pnl_energy = ifelse(en, d$pnl, 0), n_service_power = as.integer(sv),
                         importo_service_power = ifelse(sv, d$importo_value, 0),
                         n_pnl_calculable = as.integer(d$pnl_calculable),
                         n_problem_rows = as.integer(d$row_problem),
                         n_energy_not_calculable = as.integer(en & !d$pnl_calculable),
                         n_pnl_not_applicable = as.integer(!en),
                         n_curve_unavailable = as.integer(d$match_status != "matched"),
                         pnl_energy_calculable_subtotal = ifelse(d$pnl_calculable, d$pnl, 0))
  independent <- rowsum(contributions, group_id, reorder = FALSE, na.rm = FALSE)
  independent <- independent[as.character(seq_len(nrow(m))), , drop = FALSE]
  independent[independent[, "n_energy"] == 0,
              c("volume_energy", "market_value_signed_energy", "pnl_energy")] <- NA_real_
  independent[independent[, "n_pnl_calculable"] == 0, "pnl_energy_calculable_subtotal"] <- NA_real_
  for (nm in colnames(independent))
    assert(near(m[[nm]], independent[, nm]), paste("Riconciliazione per gruppo fallita:", nm))
  invisible(TRUE)
}

export_csv <- function(x, path) {
  y <- x
  for (nm in names(y)) {
    if (inherits(y[[nm]], "Date")) {
      y[[nm]] <- format(y[[nm]], "%d/%m/%Y")
    } else if (is.numeric(y[[nm]])) {
      y[[nm]] <- trimws(formatC(y[[nm]], digits = 17, format = "g", decimal.mark = ","))
      y[[nm]][is.na(x[[nm]])] <- NA_character_
    }
    if (is.character(y[[nm]])) y[[nm]] <- enc2utf8(y[[nm]])
  }
  # BOM UTF-8 per Excel italiano; 17 cifre per il round-trip double.
  old <- options(digits = 17, scipen = 999)
  on.exit(options(old), add = TRUE)
  con <- file(path, open = "wb")
  on.exit(close(con), add = TRUE)
  writeBin(as.raw(c(0xef, 0xbb, 0xbf)), con)
  write.table(y, con, sep = ";", dec = ",", row.names = FALSE, col.names = TRUE,
              quote = TRUE, na = "NA", eol = "\r\n", qmethod = "double", fileEncoding = "UTF-8")
}

verify_csv <- function(expected, path) {
  actual <- read.table(path, header = TRUE, sep = ";", dec = ",", quote = '"',
                       colClasses = "character", na.strings = NULL, check.names = FALSE,
                       comment.char = "", fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE)
  assert(identical(dim(expected), dim(actual)) && identical(names(expected), names(actual)),
         paste("Schema o righe alterati nel CSV:", path))
  for (nm in names(expected)) {
    value <- expected[[nm]]
    if (is.numeric(value)) {
      parsed <- suppressWarnings(as.numeric(sub(",", ".", actual[[nm]], fixed = TRUE)))
      assert(identical(is.na(value), is.na(parsed)) && near(value, parsed),
             paste("Round-trip numerico fallito:", nm))
      assert(near(strict_sum(value[!is.na(value)], empty = 0), strict_sum(parsed[!is.na(parsed)], empty = 0)),
             paste("Totale alterato nel CSV:", nm))
    } else {
      if (inherits(value, "Date")) value <- format(value, "%d/%m/%Y")
      value <- as.character(value)
      value[is.na(value)] <- "NA"
      assert(identical(value, actual[[nm]]), paste("Round-trip testuale/data fallito:", nm))
    }
  }
  invisible(TRUE)
}
