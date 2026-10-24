#!/usr/bin/env Rscript
# Avvio da qualunque directory: Rscript Code/R/run.R [input_dir] [output_dir]
args_all <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args_all[grepl("^--file=", args_all)])
if (!length(script)) stop("Avviare con Rscript", call. = FALSE)
code_r <- dirname(normalizePath(script, winslash = "/", mustWork = TRUE))
root <- normalizePath(file.path(code_r, "..", ".."), winslash = "/", mustWork = TRUE)
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 2L) stop("Uso: Rscript Code/R/run.R [input_dir] [output_dir]", call. = FALSE)
input_dir <- if (length(args) >= 1L) args[1] else root
output_dir <- if (length(args) >= 2L) args[2] else file.path(root, "Output", "R")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
output_dir <- normalizePath(output_dir, winslash = "/", mustWork = TRUE)
Sys.setenv(TZ = "Europe/Rome")
# Ordinamento ripetibile indipendente dalla lingua del sistema.
invisible(Sys.setlocale("LC_COLLATE", "C"))
source(file.path(code_r, "functions.R"), encoding = "UTF-8")
source(file.path(code_r, "tests.R"), encoding = "UTF-8")
source(file.path(code_r, "report.R"), encoding = "UTF-8")
run_tests()

inputs <- file.path(input_dir, c("DEAL.csv", "CurveOrariePower.csv"))
before_hash <- tools::md5sum(inputs)
raw_d <- read_source(inputs[1], deal_columns)
raw_c <- read_source(inputs[2], curve_columns)
deals <- prepare_deals(raw_d)
long <- curves_to_long(raw_c)
result <- calculate_pnl(enrich_deals(deals, long))
result <- result[order(result$delivery_date, result$delivery_hour, result$market,
                       result$counterparty, result$purpose, result$deal_row_id, na.last = TRUE), ]
rownames(result) <- NULL
monthly <- monthly_summary(result)
reconcile_monthly(result, monthly)

# Nessuna tabella numerica e' arrotondata prima dell'esportazione.
detail_path <- file.path(output_dir, "deals_enriched_pnl.csv")
monthly_path <- file.path(output_dir, "monthly_summary.csv")
assert(!any(normalizePath(c(detail_path, monthly_path), winslash = "/", mustWork = FALSE) %in%
              normalizePath(inputs, winslash = "/", mustWork = TRUE)), "Output sovrapposto agli input")
export_csv(result, detail_path)
export_csv(monthly, monthly_path)
verify_csv(result, detail_path)
verify_csv(monthly, monthly_path)
write_diagnostics(raw_d, raw_c, result, long, file.path(output_dir, "diagnostics.md"))
write_report(result, monthly, file.path(output_dir, "report_it.md"))
after_hash <- tools::md5sum(inputs)
assert(identical(before_hash, after_hash), "File originali modificati")

log <- c("VALIDAZIONE COMPLETATA", "Test sintetici mirati: OK", "Chiavi curve univoche: OK",
         "Left join conservativo (righe, originali, IMPORTO, VOLUME): OK",
         "Identita formule P&L sulle righe calcolabili: OK", "Riconciliazione dettaglio/mensile: OK",
         "Rilettura integrale di entrambi i CSV: OK", "Originali invariati (MD5): OK", "",
         paste("Righe deal:", nrow(result)), paste("Righe curve larghe/lunghe:", nrow(raw_c), nrow(long)),
         paste("Gruppi mensili:", nrow(monthly)), paste("Righe con problemi:", sum(result$row_problem)),
         paste("Righe ENERGY con P&L:", sum(result$pnl_calculable)),
         paste("Righe non applicabili:", sum(!result$pnl_applicable)), "", "MD5 input:",
         paste(basename(inputs), unname(before_hash)), "", "MD5 CSV esportati:",
         paste(basename(c(detail_path, monthly_path)), unname(tools::md5sum(c(detail_path, monthly_path)))),
         "", "MD5 codice R:", paste(basename(list.files(code_r, pattern = "[.]R$", full.names = TRUE)),
                                    unname(tools::md5sum(list.files(code_r, pattern = "[.]R$", full.names = TRUE)))),
         "", "Ambiente R:", capture.output(sessionInfo()))
writeLines(log, file.path(output_dir, "validation.txt"))
message(paste("Completato:", nrow(result), "deal;", nrow(monthly), "gruppi mensili. Output:", output_dir))
