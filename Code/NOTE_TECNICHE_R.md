# Note tecniche R - Sorgenia Business Case

Documentazione di supporto al codice R. La sintesi dei risultati e la bozza di Conto Economico sono in [report_it.md](../Output/R/report_it.md).

## Convenzione economica ed esempi

Si adotta IMPORTO come valore contrattuale firmato: `direction=+1` per Sell e `-1` per Buy. Il prezzo ENERGY è `IMPORTO / (direction * VOLUME)` e il P&L è `IMPORTO - direction * VOLUME * market_price`. La convenzione è coerente con la prevalenza di importi negativi Buy e positivi Sell; i segni inversi corrispondono a prezzi contrattuali negativi, mantenuti nei calcoli. Si assumono EUR, MWh ed EUR/MWh.

| Caso | Volume | Prezzo contratto | Prezzo mercato | IMPORTO | Valore mercato firmato | P&L |
| --- | --- | --- | --- | --- | --- | --- |
| Buy | 2 | 80 | 100 | -160 | -200 | 40 |
| Sell | 2 | 120 | 100 | 240 | 200 | 40 |
| Buy a prezzo negativo | 2 | -20 | -10 | 40 | 20 | 20 |
| Sell a prezzo negativo | 2 | -10 | -20 | -20 | -40 | 20 |

IMPORTO è già prezzo per volume: non si moltiplica nuovamente per VOLUME e non si usa il suo valore assoluto. L'identità algebrica controlla la coerenza del calcolo; la convenzione economica resta un'ipotesi di lettura del dataset.

Il Conto Economico classifica ENERGY Sell come ricavi, ENERGY Buy come costi con segno invertito e SERVICE_POWER Sell come ricavi servizi. Con prezzi negativi sono possibili ricavi negativi e costi negativi. Il margine del dataset riconcilia il saldo contrattuale e resta distinto dal P&L rispetto alle curve.

## Parsing e dati non validi

Le dieci colonne originali dei deals sono mantenute come testo, nello stesso ordine iniziale e con gli stessi valori; si aggiungono colonne analitiche. Per esempio, `IMPORTO` resta la stringa originale con virgola e `importo_value` è il corrispondente double R. Questo permette di distinguere dati sorgente e interpretazione senza perdere il testo originale. La preservazione riguarda i valori dei campi, non la rappresentazione byte per byte del CSV esportato.

Il parsing accetta decimali con virgola senza separatori delle migliaia e date rigorosamente `gg/mm/aaaa`. Le ore sono interi da 1 a 25. Gli input devono avere esattamente lo schema atteso; i nomi delle categorie sono intenzionalmente case sensitive e non vengono normalizzati silenziosamente.

Una chiave curva non valida o duplicata blocca la corsa: non esiste un'associazione affidabile. Un prezzo curva vuoto/non numerico resta `NA`. I deal con parsing non valido, categorie ignote, dimensioni mancanti, volume non positivo o curva non disponibile sono conservati e marcati con `row_problem` e `issue_codes`. I numeri di riferimento forniti nella consegna sono confrontati nella diagnostica, senza usarli per filtrare righe o dirigere il calcolo. Differenze vanno investigate, non corrette forzando quei numeri.

`SERVICE_POWER` è mantenuto e associato alla curva; `pnl_applicable=FALSE`, prezzo contrattuale ENERGY, valore di mercato ENERGY e P&L restano `NA`. La natura dei servizi e l'unità del loro volume non sono note. Un servizio escluso dal P&L per natura non è automaticamente una riga problematica.

## Dizionario delle colonne aggiunte nel dettaglio

| Colonna | Significato |
| --- | --- |
| `deal_row_id` | Numero di riga dati nel sorgente, a partire da 1; non è un contratto |
| `delivery_date`, `delivery_hour` | Data e ora interpretate, mantenendo anche DATA/ORA originali |
| `importo_value`, `volume_value` | Valori numerici interpretati, senza arrotondamento |
| `direction` | -1 Buy, +1 Sell, NA per purpose ignoto |
| `curve_index_expected` | Colonna curva attesa dalla mappatura del mercato |
| `curve_match_count` | 0 o 1; l'unicità delle curve è verificata prima del match |
| `curve_row_id`, `DDATE`, `HOUR`, `curve_index` | Provenienza della riga curva associata; ID tecnico della riga nel file largo |
| `market_price_raw`, `market_price` | Prezzo sorgente della curva e sua interpretazione numerica |
| `match_status` | matched, no_curve_match, invalid_delivery_key_or_market o matched_missing_or_invalid_price |
| `pnl_applicable` | TRUE per ENERGY, FALSE per le altre commodity |
| `contract_price` | Prezzo ENERGY ricostruito se purpose, importo e volume sono validi, anche se manca la curva |
| `pnl_calculable` | ENERGY senza problemi nei dati richiesti e nelle dimensioni |
| `market_value_signed`, `pnl` | Valore di mercato firmato e scostamento ENERGY dalla curva |
| `pnl_status` | calculated, not_calculable_data_issue o not_applicable_commodity |
| `row_problem`, `issue_codes` | Indicatore problema e ragioni, separate da `\|`; OK se nessuna |

Mappatura unica in `Code/R/functions.R`: ITALY → MkIndex_EE_ITA_ICE; GERMANYDE → MkIndex_EE_GER_DE_ICE; FRANCE → MkIndex_EE_FRA_ICE; SPAIN → MkIndex_EE_SPA_ICE.

## Dizionario del riepilogo mensile

| Colonna | Significato |
| --- | --- |
| `anno, mese, counterparty, purpose, market` | Unica chiave di aggregazione |
| `n_rows`, `importo_total` | Righe e importo di tutte le commodity del gruppo |
| `n_energy`, `volume_energy` | Numero righe e volume della sola ENERGY |
| `market_value_signed_energy`, `pnl_energy` | Somme complete ENERGY: NA se manca un contributo |
| `n_service_power`, `importo_service_power` | Numero righe e importo dei servizi, separati |
| `n_pnl_calculable`, `n_problem_rows` | Copertura P&L e righe con problemi |
| `n_energy_not_calculable`, `n_pnl_not_applicable` | ENERGY non calcolabile e altre commodity |
| `n_curve_unavailable` | Righe senza curva utilizzabile, di qualsiasi commodity |
| `pnl_energy_calculable_subtotal` | Somma delle sole righe calcolabili; può essere parziale |

Le somme complete restituiscono NA se anche un contributo è mancante/non valido. Per volume ENERGY un valore non positivo invalida il totale del gruppo. Se non ci sono righe ENERGY, volume, valore di mercato e P&L ENERGY sono NA. Se non ci sono servizi, il loro importo è zero come assenza strutturale documentata da `n_service_power=0`; non è una stima di costi aziendali mancanti. Il subtotale calcolabile è NA quando non c'è alcun P&L calcolabile. Le righe con data non valida, se presenti, restano in un gruppo con anno/mese NA.

## Formato dei CSV e verifiche

- Separatore `;`, virgola decimale, UTF-8 con BOM e righe CRLF per Excel italiano.
- Stringhe tra virgolette con escape standard; campi mancanti analitici `NA`, booleani TRUE/FALSE, date `gg/mm/aaaa`.
- Numeri calcolati scritti con 17 cifre significative per preservare i double alla rilettura; eventuali code decimali sono rappresentazione numerica, non nuovi arrotondamenti economici. Excel può visualizzare meno cifre: non usarlo per risalvare l'output destinato all'audit.
- Dettaglio ordinato per data, ora, mercato, controparte, purpose e ID tecnico. Mensile ordinato per la sua chiave. Collazione R `C` per risultati deterministici.
- La riconciliazione controlla i totali e ogni singolo gruppo con un secondo percorso di aggregazione (`rowsum`), inclusi NA e contatori. Le verifiche confrontano tutte le celle dei CSV riletti, inclusi originali e date. I confronti numerici usano tolleranza relativa `1e-12` per gli effetti di floating point; non si arrotondano i dati per far coincidere i totali.
- Per rileggere i risultati in R: `read.csv2("Output/R/monthly_summary.csv", fileEncoding="UTF-8-BOM", na.strings="NA")`. Per preservare i campi originali del dettaglio come testo, usare `colClasses="character"` e `na.strings=NULL`, poi interpretare esplicitamente le colonne analitiche.

