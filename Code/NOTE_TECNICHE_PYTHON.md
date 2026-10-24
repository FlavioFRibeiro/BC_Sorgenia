# Note tecniche Python - Sorgenia Business Case

Queste note descrivono l'implementazione **Python**. La sintesi e il Conto Economico sono in [Output/python/report_it.md](../Output/python/report_it.md). L'implementazione R è documentata separatamente nelle [note tecniche R](NOTE_TECNICHE_R.md).

## Ambiente ed esecuzione

Python >= 3.9, verificato con Python 3.9.13 su Windows. Si usa soltanto la libreria standard: `csv`, `datetime`, `math`, `decimal`, `pathlib`, `hashlib` e strumenti di supporto. Nessun pacchetto da installare.

Dalla radice del progetto:

```sh
python Code/Python/run.py
```

Input predefiniti: `DEAL.csv` e `CurveOrariePower.csv` nella radice. Output predefinito: `Output/python`. Lo script individua la radice rispetto al proprio percorso; accetta anche directory input e output come argomenti posizionali. I percorsi specificati dall'utente sono relativi alla directory corrente.

```sh
python Code/Python/run.py "." "Output/python"
python Code/Python/run.py --check-reproducibility
python Code/Python/compare.py
```

La prima corsa produce i risultati e li confronta con `Output/R`. `--check-reproducibility` richiede una corsa precedente: riesegue l'intera pipeline sugli stessi input e confronta gli hash di dettaglio, mensile, report e diagnostica prima/dopo. L'esito è in `Output/python/determinism.md`.

Per elaborare altri input senza riferimenti R usare `--skip-comparison`. Per cambiare la directory dei riferimenti usare `--reference-dir`. `compare.py` consente anche il confronto separato, senza ricalcolare i risultati.

## Organizzazione del codice

| File | Responsabilità |
| --- | --- |
| `Python/run.py` | Punto di ingresso, pipeline, validazione e registrazione degli hash |
| `Python/functions.py` | Lettura, parsing, curva lunga, join, P&L, mensile, esportazione e rilettura |
| `Python/report.py` | Sintesi in italiano e diagnostica generate dai risultati Python |
| `Python/tests.py` | Casi critici e verifica che il confronto intercetti dati alterati |
| `Python/compare.py` | Confronto completo con gli output R |

## Importazione e chiavi

`csv.DictReader` legge separatore `;` e UTF-8 con eventuale BOM. Tutti i campi originali sono stringhe. Si verifica lo schema, l'unicità delle intestazioni e il numero di campi di ogni riga; non si normalizzano silenziosamente categorie o spazi.

Il parsing crea `datetime.date`, interi per le ore e `float` per importi, volumi e prezzi. Sono ammesse date esattamente `gg/mm/aaaa`, ore intere 1–25 e decimali con virgola senza separatori delle migliaia. Un parsing non valido produce `None`, esportato come `NA`, con il relativo indicatore di problema.

`deal_row_id` è la posizione nel file sorgente, a partire da 1: non è un ID contratto. I deal apparentemente duplicati sono mantenuti.

Le curve sono trasformate in righe per mercato con la stessa mappatura R:

| Mercato | Colonna curva |
| --- | --- |
| ITALY | MkIndex_EE_ITA_ICE |
| GERMANYDE | MkIndex_EE_GER_DE_ICE |
| FRANCE | MkIndex_EE_FRA_ICE |
| SPAIN | MkIndex_EE_SPA_ICE |

Un dizionario indicizzato dalla tupla `(data, ora, mercato)` implementa il left join molti-a-uno. Si blocca l'esecuzione se una chiave curva è duplicata o non valida. Ogni deal mantiene una sola riga, con zero o una corrispondenza; un prezzo mancante resta `NA`. Le etichette DATA/ORA e DDATE/HOUR sono conservate, incluse le ore 25. Non si convertono le ore in timestamp.

## Segni, P&L e servizi

Si adotta la stessa convenzione economica: `direction=+1` per Sell, `-1` per Buy; importi in EUR, volumi ENERGY in MWh e prezzi in EUR/MWh come ipotesi del business case.

```text
contract_price = IMPORTO / (direction * VOLUME)
market_value_signed = direction * VOLUME * market_price
pnl = IMPORTO - market_value_signed
```

| Caso | Volume | Prezzo contratto | Prezzo mercato | IMPORTO | P&L |
| --- | --- | --- | --- | --- | --- |
| Buy | 2 | 80 | 100 | -160 | 40 |
| Sell | 2 | 120 | 100 | 240 | 40 |
| Buy a prezzo negativo | 2 | -20 | -10 | 40 | 20 |
| Sell a prezzo negativo | 2 | -10 | -20 | -20 | 20 |

Non si usa il valore assoluto di IMPORTO e non lo si moltiplica nuovamente per il volume. Volume non positivo, importo non valido, purpose ignoto o curva non utilizzabile rendono il P&L non calcolabile. `row_problem`, `issue_codes` e `pnl_status` esplicitano il trattamento.

`SERVICE_POWER` rimane nel dettaglio e riceve la curva, ma `pnl_applicable=False` e prezzo contrattuale ENERGY, valore di mercato e P&L restano `None/NA`. I servizi Sell sono classificati nei ricavi servizi. Il loro volume non viene sommato a ENERGY.

## Mensile e colonne

La chiave mensile è esattamente `anno, mese, counterparty, purpose, market`, ottenuta dalla data di consegna. Le tabelle hanno lo stesso schema e ordine di colonne della versione R.

| Colonne | Significato |
| --- | --- |
| Le dieci colonne originali | Valori sorgente mantenuti integralmente come testo |
| `deal_row_id`, `curve_row_id` | Provenienza tecnica delle righe deal e curva |
| `delivery_date`, `delivery_hour`, `importo_value`, `volume_value` | Campi analitici interpretati |
| `direction`, `curve_index_expected`, `curve_index` | Direzione e mappatura del mercato |
| `DDATE`, `HOUR`, `market_price_raw`, `market_price` | Chiave e prezzo della curva associata |
| `curve_match_count`, `match_status` | Esito della corrispondenza |
| `pnl_applicable`, `pnl_calculable`, `pnl_status` | Applicabilità e calcolabilità del P&L |
| `contract_price`, `market_value_signed`, `pnl` | Prezzo ricostruito, valore firmato e risultato ENERGY |
| `row_problem`, `issue_codes` | Problemi nei dati e relative ragioni |
| `n_rows`, `importo_total` | Conteggio e importo mensile di tutte le commodity |
| `n_energy`, `volume_energy`, `market_value_signed_energy`, `pnl_energy` | Aggregati della sola ENERGY |
| `n_service_power`, `importo_service_power` | Conteggio e importo servizi separati |
| `n_pnl_calculable`, `n_problem_rows`, `n_energy_not_calculable`, `n_pnl_not_applicable`, `n_curve_unavailable` | Contatori di copertura e problemi |
| `pnl_energy_calculable_subtotal` | Somma delle sole righe calcolabili, anche per gruppi incompleti |

`strict_sum()` usa `math.fsum()` e propaga le assenze: se manca un contributo, la somma completa è `NA`. Un gruppo senza ENERGY ha volume e P&L ENERGY `NA`. Senza righe servizi il relativo importo è zero, documentato da `n_service_power=0`. Un subtotale senza righe calcolabili resta `NA`. I volumi ENERGY non positivi invalidano il relativo totale mensile.

Il Conto Economico applica commodity e purpose alle stesse righe della versione R. Il margine del dataset riconcilia il saldo contrattuale; il P&L rispetto alle curve rimane una misura distinta.

## Precisione, confronto e riproducibilità

I calcoli utilizzano double Python, senza arrotondamento economico. `math.fsum()` limita l'errore di accumulo. La riconciliazione mensile segue un secondo percorso: contributi per riga accumulati con `Decimal` a 80 cifre, inclusa la propagazione dei mancanti.

I CSV usano `;`, virgola decimale, UTF-8 con BOM, CRLF, date `gg/mm/aaaa`, booleani TRUE/FALSE e `NA` esplicito. I float sono scritti con 17 cifre significative. La rilettura Python confronta tutte le celle, i totali e l'uguaglianza esatta dei float ricostruiti. Dettaglio e mensile sono ordinati sulle stesse chiavi R, senza dipendere dalla locale.

`comparison_R_python.md` verifica integralmente i due CSV e il report. Per il report si neutralizzano esclusivamente il nome del linguaggio e il link delle note; il testo restante, compresi tutti i numeri pubblicati, deve coincidere esattamente, senza tolleranza.

Per i CSV si distinguono uguaglianza esatta, uguaglianza byte per byte e confronto numerico con tolleranze relativa e assoluta `1e-12`. Le eventuali differenze nell'ultimo bit dovute alla conversione decimale-double e all'accumulo R/Python sono contate per colonna, con massimo scarto assoluto e relativo: non vengono nascoste arrotondando o copiando i risultati R. I campi originali, le chiavi, gli stati e gli NA devono sempre coincidere esattamente.

I test coprono segni Buy/Sell, prezzi contrattuali e di curva negativi, volume zero, servizi, ora 25, chiavi duplicate, prezzi mancanti, parsing non valido, conservazione dei deal uguali, mensili incompleti, classificazione CE e capacità del confronto di rilevare alterazioni. La validazione registra hash degli input, CSV e codice, oltre all'ambiente Python.
