# Test mirati ai rischi del business case; nessun framework necessario.
expect_error <- function(expr) {
  err <- tryCatch({ force(expr); FALSE }, error = function(e) TRUE)
  assert(err, "Era atteso un errore bloccante")
}

run_tests <- function() {
  raw <- data.frame(business_unit = "TEST", DATA = "25/10/2026", ORA = "25",
                    proposer_description = "TEST", counterparty = "TEST",
                    purpose = c("Buy", "Sell", "Buy", "Sell", "Buy", "Sell"),
                    market = "ITALY", commodity = c(rep("ENERGY", 5), "SERVICE_POWER"),
                    IMPORTO = c("-160", "240", "40", "-20", "0", "100"),
                    VOLUME = c("2", "2", "2", "2", "0", "1"), stringsAsFactors = FALSE)
  cv <- data.frame(DDATE = "25/10/2026", HOUR = "25", stringsAsFactors = FALSE)
  for (nm in unname(market_map)) cv[[nm]] <- "100"
  long <- curves_to_long(cv)
  d <- calculate_pnl(enrich_deals(prepare_deals(raw), long))
  assert(near(d$pnl[1:4], c(40, 40, 240, -220)), "Segni Buy/Sell o prezzi negativi errati")
  assert(near(d$contract_price[1:4], c(80, 120, -20, -10)), "Prezzo contrattuale errato")
  # Anche curva negativa: Buy a -20 contro -10 => +20; Sell a -10 contro -20 => +20.
  cv_negative <- cv
  cv_negative[[market_map[["ITALY"]]]] <- "-10"
  dn <- calculate_pnl(enrich_deals(prepare_deals(raw), curves_to_long(cv_negative)))
  assert(near(dn$pnl[3], 20), "Buy con curva negativa errato")
  cv_negative[[market_map[["ITALY"]]]] <- "-20"
  dn <- calculate_pnl(enrich_deals(prepare_deals(raw), curves_to_long(cv_negative)))
  assert(near(dn$pnl[4], 20), "Sell con curva negativa errato")
  assert(is.na(d$pnl[5]) && is.na(d$contract_price[5]) && d$row_problem[5], "Volume zero non gestito")
  assert(!d$pnl_applicable[6] && is.na(d$pnl[6]) && !d$row_problem[6] && d$curve_match_count[6] == 1,
         "Trattamento SERVICE_POWER errato")
  assert(all(d$delivery_hour == 25) && all(d$HOUR == "25"), "Ora 25 persa")
  assert(nrow(d) == nrow(raw) && identical(d[deal_columns], raw[deal_columns]), "Join non conservativo")
  expect_error(curves_to_long(rbind(cv, cv)))
  cv_missing <- cv
  cv_missing[[market_map[["ITALY"]]]] <- ""
  missing <- calculate_pnl(enrich_deals(prepare_deals(raw), curves_to_long(cv_missing)))
  assert(all(is.na(missing$pnl)) && all(missing$curve_match_count == 1), "Prezzo assente sostituito")
  wrong <- raw
  wrong$ORA[1] <- "24"
  wrong$IMPORTO[2] <- "non_numero"
  wrong$DATA[3] <- "31/02/2026"
  wrong$market[4] <- "UNKNOWN"
  wrong$purpose[5] <- "OTHER"
  bad <- calculate_pnl(enrich_deals(prepare_deals(wrong), long))
  assert(all(!bad$pnl_calculable[1:5]) && all(bad$row_problem[1:5]), "Dati invalidi non segnalati")
  m <- monthly_summary(d)
  assert(is.na(m$pnl_energy[m$purpose == "Buy"]), "Gruppo incompleto presentato come completo")
  assert(near(m$pnl_energy_calculable_subtotal[m$purpose == "Buy"], 280), "Subtotale parziale errato")
  only_service <- monthly_summary(d[6, ])
  assert(is.na(only_service$pnl_energy) && is.na(only_service$volume_energy), "Servizi senza ENERGY diventati zero")
  assert(is.na(strict_sum(c(1, NA_real_))) && is.na(strict_sum(numeric())), "Somma nasconde assenze")
  duplicated_deals <- prepare_deals(rbind(raw, raw[1, ]))
  assert(nrow(enrich_deals(duplicated_deals, long)) == nrow(raw) + 1, "Deal uguali eliminati")
  assert(all(is.na(parse_decimal(c("1.23", "1,2,3", "", "Inf")))), "Parsing numerico troppo permissivo")
  assert(all(is.na(parse_date(c("31/02/2026", "2026-01-01", "1/1/2026")))), "Parsing data troppo permissivo")
  assert(all(is.na(parse_hour(c("0", "26", "1,5")))), "Parsing ora troppo permissivo")
  ce <- contractual_statement(d)
  assert(near(ce$revenue_energy, 220) && near(ce$cost_energy, 120) &&
           near(ce$revenue_service, 100) && near(ce$known_margin, 200),
         "CE: classificazione Buy/Sell a prezzi negativi errata")
  unknown_ce <- d
  unknown_ce$commodity[1] <- "OTHER"
  assert(is.na(contractual_statement(unknown_ce)$known_margin), "CE ignora una categoria non classificata")
  reconcile_monthly(d, m)
  tmp <- tempfile(fileext = ".csv")
  on.exit(unlink(tmp), add = TRUE)
  export_csv(d, tmp)
  verify_csv(d, tmp)
  message("Test mirati: OK")
  invisible(TRUE)
}
