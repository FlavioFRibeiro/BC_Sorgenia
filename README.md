# Sorgenia Trading - Business case in R e Python

Due implementazioni indipendenti degli stessi sette punti: lettura dei deal e delle curve, join orario, P&L ENERGY, aggregazione mensile, due CSV e bozza di Conto Economico. Entrambe usano soltanto le rispettive librerie di base e mantengono intatti `DEAL.csv` e `CurveOrariePower.csv`.

## Esecuzione

Requisiti: R >= 4.1 e Python >= 3.9; verificati con R 4.3.1 e Python 3.9.13 su Windows. Nessun pacchetto aggiuntivo da installare.

Dalla radice, eseguire prima R e poi Python:

```sh
Rscript --vanilla Code/R/run.R
python Code/Python/run.py
```

Lo script R scrive in `Output/R`; Python scrive in `Output/python` e confronta automaticamente i propri risultati con quelli R. Le radici predefinite sono risolte rispetto agli script: non ci sono percorsi specifici della macchina. Se gli eseguibili non sono nel PATH, usare il percorso della propria installazione.

Entrambi accettano directory input e output opzionali, relative alla directory corrente:

```sh
Rscript --vanilla Code/R/run.R "." "Output/R"
python Code/Python/run.py "." "Output/python"
```

Gli output omonimi vengono rigenerati. Ogni corsa include i test e produce un verbale `validation.txt`; considerare valida solo una corsa terminata con successo.

## Consegna

| Contenuto | R | Python |
| --- | --- | --- |
| Codice e punto di ingresso | [Code/R/run.R](Code/R/run.R) | [Code/Python/run.py](Code/Python/run.py) |
| Dettaglio orario e P&L | [deals_enriched_pnl.csv](Output/R/deals_enriched_pnl.csv) | [deals_enriched_pnl.csv](Output/python/deals_enriched_pnl.csv) |
| Riepilogo mensile | [monthly_summary.csv](Output/R/monthly_summary.csv) | [monthly_summary.csv](Output/python/monthly_summary.csv) |
| Sintesi e Conto Economico | [report_it.md](Output/R/report_it.md) | [report_it.md](Output/python/report_it.md) |
| Note tecniche | [NOTE_TECNICHE_R.md](Code/NOTE_TECNICHE_R.md) | [NOTE_TECNICHE_PYTHON.md](Code/NOTE_TECNICHE_PYTHON.md) |
| Diagnostica | [diagnostics.md](Output/R/diagnostics.md) | [diagnostics.md](Output/python/diagnostics.md) |
| Validazione | [validation.txt](Output/R/validation.txt) | [validation.txt](Output/python/validation.txt) |

Il [confronto R/Python](Output/python/comparison_R_python.md) riporta gli esiti per ogni colonna e l'uguaglianza esatta dei risultati pubblicati nei report. Il [controllo di riproducibilità Python](Output/python/determinism.md) documenta l'identità byte per byte fra due corse.

## Confronto e determinismo

Il confronto può essere ripetuto senza ricalcolare i risultati:

```sh
python Code/Python/compare.py
```

Per verificare una seconda esecuzione completa Python sugli stessi input:

```sh
python Code/Python/run.py --check-reproducibility
```

Il report deve coincidere esattamente dopo aver neutralizzato soltanto il nome del linguaggio e il link delle note tecniche. Tutti gli importi e gli altri risultati pubblicati sono confrontati senza tolleranza.

I CSV sono confrontati integralmente: originali, chiavi, ordine, stati e NA devono coincidere; le differenze nelle ultime cifre dei double sono contate e misurate, con tolleranze relativa e assoluta `1e-12`. Una pipeline deterministica produce gli stessi risultati a ogni corsa nel proprio ambiente; implementazioni in linguaggi diversi possono differire nell'ultimo bit per conversione decimale e somma. Il verbale distingue queste differenze dall'uguaglianza esatta del report.

La pipeline Python elabora autonomamente gli input: i file R sono letti soltanto nella fase finale di confronto. Per un'esecuzione Python senza riferimenti R usare `--skip-comparison`; `--reference-dir` consente di specificare un diverso riferimento R.

## Decisioni comuni

- **Join:** chiave data, numero d'ora e mercato, con curve univoche e tutte le righe deal preservate. Si mantengono le ore dei giorni da 23 e 25 ore.
- **Segni:** `direction=+1` Sell e `-1` Buy; `contract_price=IMPORTO/(direction*VOLUME)`; `pnl=IMPORTO-direction*VOLUME*market_price`. I prezzi negativi mantengono il proprio segno.
- **Servizi:** SERVICE_POWER contribuisce ai ricavi servizi, con P&L power `NA` e volumi separati da ENERGY.
- **Mensile:** chiave esatta anno, mese, counterparty, purpose e market. Le somme complete propagano i contributi mancanti; i contatori esplicitano la copertura.
- **Conto Economico:** ricavi energia e servizi meno costi di acquisto energia danno il margine del dataset, distinto dal P&L rispetto alle curve.

Si assumono EUR, MWh per ENERGY ed EUR/MWh. Entrambe le versioni esportano CSV con `;`, virgola decimale, UTF-8 con BOM e date `gg/mm/aaaa`. I calcoli mantengono la precisione numerica; i report presentano gli importi con due decimali.
