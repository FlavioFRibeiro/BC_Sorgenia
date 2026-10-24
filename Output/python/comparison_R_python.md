# Confronto R / Python

## Report: coincidenza esatta del 100%

Il contenuto dei due report coincide integralmente dopo aver neutralizzato soltanto il nome del linguaggio e il link delle rispettive note tecniche. Nessun numero, importo o risultato viene modificato per il confronto: non si applica alcuna tolleranza al report.

## CSV: confronto integrale

Si controllano schema, ordine, ogni riga, ogni campo originale, chiavi, stati, NA e numeri. Le differenze non esatte dei double sono contate esplicitamente. La tolleranza numerica tra linguaggi e' relativa 1e-12 e assoluta 1e-12; la rilettura del CSV Python usa invece uguaglianza numerica esatta.

### deals_enriched_pnl.csv

Righe: 216804; colonne: 33; righe numericamente esatte: 216734; celle numeriche non esatte ma entro tolleranza: 210.

File identici anche byte per byte: NO.

| colonna | celle verificate | differenze double | massimo scarto assoluto | massimo scarto relativo |
| --- | --- | --- | --- | --- |
| business_unit | 216804 | 0 | 0 | 0 |
| DATA | 216804 | 0 | 0 | 0 |
| ORA | 216804 | 0 | 0 | 0 |
| proposer_description | 216804 | 0 | 0 | 0 |
| counterparty | 216804 | 0 | 0 | 0 |
| purpose | 216804 | 0 | 0 | 0 |
| market | 216804 | 0 | 0 | 0 |
| commodity | 216804 | 0 | 0 | 0 |
| IMPORTO | 216804 | 0 | 0 | 0 |
| VOLUME | 216804 | 0 | 0 | 0 |
| deal_row_id | 216804 | 0 | 0 | 0 |
| delivery_date | 216804 | 0 | 0 | 0 |
| delivery_hour | 216804 | 0 | 0 | 0 |
| importo_value | 216804 | 0 | 0 | 0 |
| volume_value | 216804 | 0 | 0 | 0 |
| direction | 216804 | 0 | 0 | 0 |
| curve_index_expected | 216804 | 0 | 0 | 0 |
| curve_match_count | 216804 | 0 | 0 | 0 |
| curve_row_id | 216804 | 0 | 0 | 0 |
| DDATE | 216804 | 0 | 0 | 0 |
| HOUR | 216804 | 0 | 0 | 0 |
| curve_index | 216804 | 0 | 0 | 0 |
| market_price_raw | 216804 | 0 | 0 | 0 |
| market_price | 216804 | 70 | 2.8421709430404007e-14 | 1.9478092111559121e-16 |
| match_status | 216804 | 0 | 0 | 0 |
| pnl_applicable | 216804 | 0 | 0 | 0 |
| row_problem | 216804 | 0 | 0 | 0 |
| issue_codes | 216804 | 0 | 0 | 0 |
| contract_price | 216804 | 0 | 0 | 0 |
| pnl_calculable | 216804 | 0 | 0 | 0 |
| pnl | 216804 | 70 | 9.0949470177292824e-13 | 7.1950023305656156e-15 |
| market_value_signed | 216804 | 70 | 9.0949470177292824e-13 | 2.5970789482078827e-16 |
| pnl_status | 216804 | 0 | 0 | 0 |

### monthly_summary.csv

Righe: 117; colonne: 19; righe numericamente esatte: 116; celle numeriche non esatte ma entro tolleranza: 2.

File identici anche byte per byte: NO.

| colonna | celle verificate | differenze double | massimo scarto assoluto | massimo scarto relativo |
| --- | --- | --- | --- | --- |
| anno | 117 | 0 | 0 | 0 |
| mese | 117 | 0 | 0 | 0 |
| counterparty | 117 | 0 | 0 | 0 |
| purpose | 117 | 0 | 0 | 0 |
| market | 117 | 0 | 0 | 0 |
| n_rows | 117 | 0 | 0 | 0 |
| importo_total | 117 | 0 | 0 | 0 |
| n_energy | 117 | 0 | 0 | 0 |
| volume_energy | 117 | 0 | 0 | 0 |
| market_value_signed_energy | 117 | 0 | 0 | 0 |
| pnl_energy | 117 | 1 | 2.9103830456733704e-11 | 1.5147378757435981e-16 |
| n_service_power | 117 | 0 | 0 | 0 |
| importo_service_power | 117 | 0 | 0 | 0 |
| n_pnl_calculable | 117 | 0 | 0 | 0 |
| n_problem_rows | 117 | 0 | 0 | 0 |
| n_energy_not_calculable | 117 | 0 | 0 | 0 |
| n_pnl_not_applicable | 117 | 0 | 0 | 0 |
| n_curve_unavailable | 117 | 0 | 0 | 0 |
| pnl_energy_calculable_subtotal | 117 | 1 | 2.9103830456733704e-11 | 1.5147378757435981e-16 |

## Interpretazione

Ogni implementazione e' deterministica nel proprio ambiente. La conversione delle stringhe decimali in double puo' differire nell'ultimo bit tra R e Python. R usa inoltre un accumulatore esteso per sum(), mentre Python usa math.fsum(): conversione e somma possono produrre differenze nelle ultime cifre binarie del dettaglio e degli aggregati. L'uguaglianza del report e' controllata esattamente alla precisione pubblicata, senza forzare o copiare i risultati R nella pipeline Python.

## MD5 dei file confrontati

| file | MD5 R | MD5 Python |
| --- | --- | --- |
| deals_enriched_pnl.csv | ab9b4f0c05c39ac20f0707966b94bf19 | 61562f9a017f6ca2bee3a8551c097b0f |
| monthly_summary.csv | 38a38e246bb33276fa3af694932bbf3f | dacb39d4c5ffdaf1ab23b7fc189b8858 |
| report_it.md | c990c5f8528214ccfbb6ab546e41d6b1 | b163dd2d818fa72a96a3ef2f3965face |
