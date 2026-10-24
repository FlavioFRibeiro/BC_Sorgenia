# Sorgenia Trading - Report web

Applicazione Streamlit in italiano per consultare i risultati validati del business case. Tre viste condividono gli stessi filtri: **Panoramica**, **Conto Economico**, **Dettaglio e controlli**.

## Avvio locale

Requisito: Python 3.12. L'ambiente è isolato nella cartella `.venv`; le versioni dirette sono in `requirements.txt` e quelle transitive in `requirements.lock`. Le pipeline originali R/Python non vengono modificate.

Dalla radice del progetto, su Windows:

```powershell
py -3.12 -m venv Code/Python/web_report/.venv
Code/Python/web_report/.venv/Scripts/python.exe -m pip install -r Code/Python/web_report/requirements.txt
Code/Python/web_report/.venv/Scripts/python.exe Code/Python/web_report/prepare_data.py
Set-Location Code/Python/web_report
.venv/Scripts/python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Se Python è gestito con `uv`, l'equivalente è `uv venv --python 3.12 Code/Python/web_report/.venv` e `uv pip install --python Code/Python/web_report/.venv/Scripts/python.exe -r Code/Python/web_report/requirements.txt`.

La versione locale usa soltanto il loopback del computer; l'accesso degli stakeholder online è gestito dalla piattaforma privata Streamlit Cloud, descritta sotto.

Dopo la prima configurazione basta eseguire `python Code/Python/web_report/run_local.py` dalla radice del progetto.

## Dati e precisione

Gli importi dell'interfaccia sono abbreviati con una cifra decimale: `k€` per migliaia e `M€` da un milione (in valore assoluto). Per esempio, `-540.640,69 €` diventa `-540,6 k€` e `-14.214.839,86 €` diventa `-14,2 M€`. Il segno viene preservato. Ogni asse monetario usa una scala comune, indicata nelle etichette; tooltip e tabelle mostrano l'unità accanto all'importo. I prezzi unitari restano in `€/MWh`, i volumi in MWh e i contatori in righe. Calcoli, snapshot e CSV scaricabili conservano valori e precisione originali.

`prepare_data.py` legge gli output di `Output/python`, controlla gli hash nel verbale di validazione, riconcilia ogni gruppo mensile tramite il modulo finanziario esistente e confronta **tutti gli importi pubblicati** con i report R e Python. I CSV sorgenti restano intatti.

Lo snapshot in `data/` contiene dettaglio CSV gzip, riferimento mensile, indicatori di controllo e manifesto con SHA-256, schema e contatori. La compressione ha timestamp e filename gzip fissi: due preparazioni con gli stessi input generano file identici. Il manifesto viene sostituito per ultimo; un aggiornamento incompleto viene rifiutato.

La pubblicazione scrive `.gitattributes` alla radice del repository con `-text` per il payload dello snapshot e il modulo finanziario: Git conserva gli stessi byte su Windows e Linux. Prima del push vengono confrontati gli hash dei blob nell'index Git e dopo il commit quelli di HEAD. Il test `test_git_transport.py` riproduce la conversione CRLF/LF e verifica che un checkout con configurazione Linux conservi il payload originale.

All'avvio si verificano schema, hash, versione del modulo finanziario e indicatori. I dati sono mantenuti in cache per identità e firma dei file; cambiare snapshot invalida il cache. Gli utenti non modificano i dati e non caricano file.

Le funzioni `contractual_statement()`, `monthly_summary()` e le somme rigorose provengono da `Code/Python/functions.py`. L'interfaccia non ricalcola formule finanziarie in JavaScript. Le operazioni sui numeri mantengono precisione double; euro e prezzi sono arrotondati solo nella presentazione. I valori completi mancanti restano non disponibili, anziché diventare zero.

## Utilizzo

- I filtri globali sono anno, mese, paese, counterparty, Buy/Sell, business unit e commodity. Si applicano prima dell'aggregazione e restano attivi passando fra le viste.
- HEDGE/FRWMK è denominato **Business unit**: non si deduce un nuovo tipo contrattuale dai codici.
- Il pulsante **Ripristina filtri** seleziona nuovamente tutto. Una selezione vuota produce “Nessun dato”.
- Il P&L ENERGY è separato dal margine di contribuzione. Selezionando solo SERVICE_POWER, P&L e volume ENERGY sono non applicabili, mentre i ricavi servizi rimangono visibili.
- Nel dettaglio, data e ora sono filtri locali alla tabella e al relativo download. Il selettore conserva anche l'ora 25. La paginazione mostra 100 righe; l'ordinamento si applica all'intero dettaglio selezionato prima di paginare.
- **Prepara CSV di tutte le righe selezionate** genera il file completo, non solo la pagina visualizzata. Modificare la selezione invalida il download precedente.
- I CSV scaricati usano UTF-8 con BOM, `;`, virgola decimale, CRLF, NA espliciti e date `gg/mm/aaaa`. Le dieci colonne originali sono preservate.

## Test

Dalla radice:

```powershell
Code/Python/web_report/.venv/Scripts/python.exe -m unittest discover -s Code/Python/web_report -p "test_*.py" -v
```

I test verificano baseline ai centesimi, 216.804 righe e 117 gruppi come riferimenti, singoli filtri e combinazioni, solo servizi, assenze, ora 25, prezzi negativi, P&L incompleto, download oltre la prima pagina, rifiuto di snapshot alterati, preparazione riproducibile e navigazione Streamlit tramite AppTest.

Il materiale in `qa/` distingue le verifiche automatiche dalle verifiche esterne effettivamente completate. I test AppTest verificano l'esecuzione della UI e i suoi widget; non sostituiscono un controllo visivo del browser.

Per registrare l'esito strutturato: `Code/Python/web_report/.venv/Scripts/python.exe Code/Python/web_report/verify.py`. La QA desktop/mobile è ripetibile con `browser_check.py`, dopo aver installato `requirements-dev.txt` e il browser Chromium di Playwright. Le schermate e il verbale browser sono salvati in `qa/` e la cache del browser resta esclusa dal repository.

## Pubblicazione privata su Streamlit Community Cloud

Repository autorizzato: **[FlavioFRibeiro/BC_Sorgenia](https://github.com/FlavioFRibeiro/BC_Sorgenia)**. Viewer iniziale: **flarib@msn.com**.

`publish.py` verifica il repository con l'API GitHub autenticata e pubblica il codebase senza force-push. Per impostazione predefinita richiede un repository privato; il proprietario ha successivamente autorizzato il mantenimento pubblico di BC_Sorgenia, consentito esplicitamente con `--allow-public`. Usa il gestore credenziali Git esistente; nessun token o password viene scritto nel progetto. Include sorgenti, input del case, report e snapshot compresso; esclude ambienti, cache, segreti e i due dettagli CSV di grandi dimensioni rigenerabili.

```powershell
python Code/Python/web_report/publish.py          # verifica visibilità privata
python Code/Python/web_report/publish.py --push   # pubblica il codebase
python Code/Python/web_report/publish.py --push --allow-public  # scelta pubblica autorizzata dal proprietario
```

Per il deploy dalla propria sessione Streamlit Cloud:

1. Aprire **[share.streamlit.io](https://share.streamlit.io/)** e scegliere **Create app**.
2. Repository `FlavioFRibeiro/BC_Sorgenia`, branch `main`, entrypoint `Code/Python/web_report/app.py`.
3. Nelle impostazioni avanzate selezionare **Python 3.12**. Le dipendenze vengono lette dal `requirements.txt` accanto all'entrypoint.
4. Distribuire l'app dal repository privato. In **App settings → Sharing → Who can view this app** verificare **Only specific people can view this app**.
5. Aggiungere **flarib@msn.com** come viewer, conservando l'accesso riservato. L'accesso è gestito da Streamlit via e-mail/identità del provider: non esiste una password incorporata nel codice.
6. Verificare una sessione autenticata autorizzata e una finestra anonima: la seconda deve richiedere il login e non mostrare il dataset.

Il repository privato non dimostra, da solo, che l'app Cloud sia già pubblicata o che l'allowlist sia configurata. L'esito effettivo del deploy e della prova di accesso deve essere verificato nella piattaforma. [Istruzioni ufficiali Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

## Aggiornamento del report

Eseguire la pipeline originale sui nuovi dati, poi `prepare_data.py`, i test e la pubblicazione del nuovo commit. Non modificare manualmente `data/manifest.json` o i CSV compressi. Un cambiamento al modulo finanziario richiede uno snapshot nuovo. Le versioni precedenti del repository permettono di recuperare il relativo snapshot.
