# Documentazione dinamica: tutti i risultati provengono dal calcolo R.
fmt <- function(x, digits = 2) {
  x[!is.na(x) & abs(x) < 0.5 * 10^(-digits)] <- 0 # Evita -0,00 solo nella presentazione.
  ifelse(is.na(x), "NA / non disponibile", formatC(x, format = "f", digits = digits,
                                                   big.mark = ".", decimal.mark = ","))
}
md_table <- function(x) {
  x[] <- lapply(x, function(v) gsub("|", "/", as.character(v), fixed = TRUE))
  c(paste0("| ", paste(names(x), collapse = " | "), " |"),
    paste0("| ", paste(rep("---", ncol(x)), collapse = " | "), " |"),
    apply(x, 1, function(v) paste0("| ", paste(v, collapse = " | "), " |")))
}
count_table <- function(x, name) {
  t <- as.data.frame(table(x, useNA = "ifany"), stringsAsFactors = FALSE)
  names(t) <- c(name, "righe")
  md_table(t)
}

write_diagnostics <- function(raw_d, raw_c, d, long, path) {
  lines <- c("# Diagnostica dei dati", "", "Generata da R; le numerosita attese sono riferimenti, non parametri del calcolo.", "")
  reference <- data.frame(controllo = c("Righe deals", "Righe curve larghe", "Anno deals iniziale", "Anno deals finale",
                                       "Anno curve iniziale", "Anno curve finale", "Righe SERVICE_POWER"),
                          riferimento = c(216804, 17520, 2026, 2026, 2026, 2027, 6),
                          osservato = c(nrow(d), nrow(raw_c), min(as.integer(format(d$delivery_date, "%Y")), na.rm = TRUE),
                                        max(as.integer(format(d$delivery_date, "%Y")), na.rm = TRUE),
                                        min(as.integer(format(long$delivery_date, "%Y"))),
                                        max(as.integer(format(long$delivery_date, "%Y"))), sum(d$commodity == "SERVICE_POWER")))
  reference$esito <- ifelse(reference$riferimento == reference$osservato, "confermato", "diverso: investigare")
  lines <- c(lines, md_table(reference), "", "## Campi originali e parsing", "",
             "Le colonne originali sono lette come testo per preservarle. I tipi analitici sono Date, integer e double.", "")
  fields <- data.frame(campo = names(raw_d), tipo_originale = "character",
                        mancanti_o_vuoti = vapply(raw_d, function(x) sum(blank(x)), integer(1)))
  lines <- c(lines, md_table(fields), "", md_table(data.frame(
    campo_analitico = c("delivery_date", "delivery_hour", "importo_value", "volume_value"),
    tipo = c("Date", "integer", "double", "double"),
    parsing_NA = c(sum(is.na(d$delivery_date)), sum(is.na(d$delivery_hour)),
                   sum(is.na(d$importo_value)), sum(is.na(d$volume_value))))), "",
    md_table(data.frame(campo_curva = names(raw_c), mancanti_o_vuoti = vapply(raw_c, function(x) sum(blank(x)), integer(1)))), "",
    paste("Prezzi curva mancanti/non validi nel formato lungo:", sum(is.na(long$market_price))), "",
    "## Categorie e segni", "")
  for (nm in c("business_unit", "proposer_description", "counterparty", "purpose", "market", "commodity"))
    lines <- c(lines, count_table(d[[nm]], nm), "")
  signs <- as.data.frame(with(d, table(commodity, purpose, segno_importo = sign(importo_value))))
  lines <- c(lines, md_table(signs), "",
             paste("VOLUME zero:", sum(d$volume_value == 0, na.rm = TRUE),
                   "; negativo:", sum(d$volume_value < 0, na.rm = TRUE),
                   "; minimo/massimo:", paste(range(d$volume_value, na.rm = TRUE), collapse = " / ")), "",
             paste("Righe interamente duplicate (mantenute):", sum(duplicated(raw_d))), "",
             "## Calendario di consegna", "")
  day_groups <- split(seq_len(nrow(raw_c)), raw_c$DDATE)
  day <- do.call(rbind, lapply(day_groups, function(ix) {
    h <- parse_hour(raw_c$HOUR[ix])
    data.frame(data = raw_c$DDATE[ix[1]], ore = length(h), minimo = min(h), massimo = max(h),
               sequenza_1_n = identical(sort(h), seq_len(length(h))))
  }))
  day <- day[order(parse_date(day$data)), ]
  lines <- c(lines, count_table(day$ore, "ore_per_giorno"), "", md_table(day[day$ore != 24, ]), "",
             paste("Tutti i giorni della curva seguono la sequenza 1..n:", all(day$sequenza_1_n)), "",
             "Le giornate brevi hanno etichette 1..23 e quelle lunghe 1..25: non sono ore civili disambiguate.",
             "Non si deduce quale etichetta rappresenti l'ora civile ripetuta; occorre la specifica del fornitore.", "",
             paste("Righe deal con ORA=25:", sum(d$delivery_hour == 25, na.rm = TRUE),
                   "; righe curve larghe HOUR=25:", sum(parse_hour(raw_c$HOUR) == 25)), "")
  delivery_days <- split(d$delivery_hour[!is.na(d$delivery_date)], d$DATA[!is.na(d$delivery_date)])
  observed <- do.call(rbind, lapply(names(delivery_days), function(dt) {
    h <- sort(unique(delivery_days[[dt]]))
    curve_h <- sort(parse_hour(raw_c$HOUR[raw_c$DDATE == dt]))
    data.frame(data = dt, ore_distinte_deal = length(h), ore_curva = length(curve_h),
               stesse_etichette = identical(h, curve_h))
  }))
  lines <- c(lines, "Ore distinte osservate nei deals (unione delle righe per giorno, non controllo della completezza di ogni contratto):", "",
             count_table(observed$ore_distinte_deal, "ore_distinte_per_giorno_deal"), "",
             paste("Giorni deal con etichette diverse dalla curva:", sum(!observed$stesse_etichette)), "")
  special <- unique(d[d$delivery_hour == 25 & !is.na(d$delivery_hour), c("DATA", "ORA", "market", "match_status")])
  lines <- c(lines, md_table(special), "", "## Join e calcolabilita", "",
             paste("Righe curve lunghe:", nrow(long), "; chiavi duplicate:",
                   sum(duplicated(make_key(long$delivery_date, long$delivery_hour, long$market)))), "",
             count_table(d$match_status, "match_status"), "", count_table(d$pnl_status, "pnl_status"), "",
             count_table(d$issue_codes, "issue_codes"), "", "## Prezzi ENERGY ricostruiti", "")
  en <- d[d$commodity == "ENERGY", ]
  pstats <- do.call(rbind, lapply(split(en, en$purpose), function(x)
    data.frame(purpose = x$purpose[1], righe = nrow(x), prezzo_minimo = fmt(min(x$contract_price, na.rm = TRUE), 6),
               prezzo_massimo = fmt(max(x$contract_price, na.rm = TRUE), 6),
               prezzi_negativi = sum(x$contract_price < 0, na.rm = TRUE))))
  lines <- c(lines, md_table(pstats), "",
             paste("Prezzi di curva negativi (tutti i mercati e anni):", sum(long$market_price < 0, na.rm = TRUE)), "",
             "## Righe SERVICE_POWER (non valutate contro la curva)", "", md_table(raw_d[raw_d$commodity == "SERVICE_POWER", ]))
  writeLines(enc2utf8(lines), path, useBytes = TRUE)
}

write_report <- function(d, m, path) {
  en <- d$commodity == "ENERGY"
  sv <- d$commodity == "SERVICE_POWER"
  statement <- contractual_statement(d)
  pnl <- strict_sum(d$pnl[en])
  ce <- data.frame(Voce = c("Ricavi da vendita di energia", "Ricavi da servizi", "Totale ricavi",
                            "Costi di acquisto di energia", "Margine di contribuzione (dataset)"),
                   EUR = fmt(c(statement$revenue_energy, statement$revenue_service,
                               statement$revenue_energy + statement$revenue_service,
                               statement$cost_energy, statement$known_margin)))
  agg <- do.call(rbind, lapply(split(d[en, ], d$market[en]), function(x)
    data.frame(Mercato = x$market[1], PnL_ENERGY_EUR = fmt(strict_sum(x$pnl)))))
  lines <- c("# Sorgenia Trading - Sintesi del business case", "",
    "Elaborazione in R dei profili di consegna e delle curve power, con dettaglio orario, riepilogo mensile e bozza di Conto Economico riferita ai deal forniti.", "",
    "## 1-2. Lettura dei deal e delle curve", "",
    sprintf("DEAL.csv contiene %s righe del %s: %s ENERGY e %s SERVICE_POWER, sui mercati italiano, tedesco e francese. CurveOrariePower.csv contiene i prezzi orari dei quattro mercati Italia, Germania, Francia e Spagna.",
            fmt(nrow(d), 0), paste(sort(unique(format(d$delivery_date, "%Y"))), collapse = ", "), fmt(sum(en), 0), fmt(sum(sv), 0)), "",
    "I file sono letti con separatore punto e virgola, virgola decimale e date gg/mm/aaaa. Per il business case si assumono importi in EUR, volumi ENERGY in MWh e prezzi in EUR/MWh.", "",
    "## 3. Associazione del prezzo di mercato", "",
    "Le curve sono trasformate dal formato largo al formato lungo e associate ai deal per data, numero d'ora e mercato. ITALY corrisponde alla curva ITA, GERMANYDE a GER_DE e FRANCE a FRA. Il join mantiene ogni riga deal e verifica l'unicita della chiave curva. Le ore dei giorni da 23 e 25 ore sono preservate.", "",
    sprintf("Risultato: %s righe associate a una curva utilizzabile su %s; %s righe con problemi nei dati.",
            fmt(sum(d$match_status == "matched"), 0), fmt(nrow(d), 0), fmt(sum(d$row_problem), 0)), "",
    "## 4. Calcolo del P&L", "",
    "Si adotta la convenzione IMPORTO firmato, coerente con i dati: direction = +1 per Sell e -1 per Buy. Il prezzo contrattuale e il P&L ENERGY sono calcolati come segue:", "",
    "```text", "contract_price = IMPORTO / (direction * VOLUME)",
    "pnl = IMPORTO - direction * VOLUME * market_price", "```", "",
    "Per Buy il risultato e' (prezzo mercato - prezzo contratto) x volume; per Sell e' (prezzo contratto - prezzo mercato) x volume. Un P&L positivo indica condizioni contrattuali favorevoli rispetto alla curva. I prezzi negativi mantengono il proprio segno.", "",
    "Esempio: un acquisto a 80 con mercato a 100 e volume 2 genera +40; una vendita a -10 con mercato a -20 e volume 2 genera +20.", "",
    "SERVICE_POWER e' trattato come corrispettivo per servizi: le righe sono mantenute e associate alla curva, con P&L NA perche' la prestazione non e' direttamente confrontabile con il prezzo dell'energia.", "",
    md_table(agg), "", paste("**P&L ENERGY complessivo:", fmt(pnl), "EUR.**"), "",
    "## 5-6. Aggregazione mensile ed esportazione", "",
    sprintf("Le righe sono aggregate esclusivamente per anno, mese, counterparty, purpose e market: il risultato contiene %s gruppi. Gli importi e il P&L orari vengono sommati; volumi ENERGY e importi servizi restano distinti.", fmt(nrow(m), 0)), "",
    "I risultati sono esportati in [deals_enriched_pnl.csv](deals_enriched_pnl.csv), con prezzi e P&L per riga, e [monthly_summary.csv](monthly_summary.csv), con gli aggregati mensili. Entrambi usano il formato CSV per Excel italiano: separatore punto e virgola, virgola decimale e UTF-8 con BOM.", "",
    "## 7. Bozza di Conto Economico", "",
    "Prospetto gestionale relativo al dataset. La classificazione usa commodity e purpose: ENERGY Sell nei ricavi energia, SERVICE_POWER Sell nei ricavi servizi ed ENERGY Buy nei costi, con segno invertito rispetto a IMPORTO.", "",
    md_table(ce), "",
    "Margine di contribuzione = ricavi energia + ricavi servizi - costi di acquisto energia. Nel perimetro analizzato i costi di acquisto superano i ricavi complessivi.", "",
    "Il margine coincide qui con il saldo degli importi contrattuali. Il P&L ENERGY misura invece lo scostamento rispetto alle curve: i due risultati rispondono a domande diverse e non si sommano. Il P&L e' un confronto economico con il benchmark fornito, non una misura di risultato realizzato.", "",
    "I controlli su chiavi, segni, ore di consegna, conservazione delle righe e riconciliazione mensile sono documentati in [diagnostics.md](diagnostics.md) e [validation.txt](validation.txt). Metodologia tecnica e dizionario delle colonne: [NOTE_TECNICHE_R.md](../../Code/NOTE_TECNICHE_R.md).")
  writeLines(enc2utf8(lines), path, useBytes = TRUE)
}
