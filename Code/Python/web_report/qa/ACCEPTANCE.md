# Verifica di consegna

## Completato

- Ambiente isolato Python 3.12.13, dipendenze dirette e transitive fissate.
- Snapshot deterministico: 216.804 righe, 117 gruppi mensili, confronto degli importi con report R/Python e riconciliazione indipendente.
- P&L ENERGY **−540.640,69 EUR**; margine di contribuzione del dataset **−14.214.839,86 EUR**.
- Undici test automatici superati, inclusi tutti i filtri, solo servizi, selezione vuota, ora 25, prezzi negativi, P&L incompleto, download completo, corruzione snapshot e preparazione ripetibile.
- Test UI: navigazione, persistenza e reset dei filtri, paginazione, ora 25, invalidazione del download e reset dei filtri locali non più validi.
- Browser Chromium isolato: Panoramica, Conto Economico e dettaglio su desktop; Panoramica e grafici su mobile 390 px. Nessun errore JavaScript e nessun overflow orizzontale rilevato. Schermate controllate nella cartella QA.
- Server locale su loopback, endpoint health HTTP 200.
- Repository GitHub verificato come privato tramite API autenticata; codebase pubblicato senza token/password nei file.
- Le pipeline e i CSV obbligatori precedenti sono preservati.

## Configurazione esterna ancora da verificare

La pubblicazione dell'app su Streamlit Community Cloud e l'allowlist del viewer **flarib@msn.com** richiedono la sessione autenticata del proprietario sulla piattaforma. Il repository privato è pronto, ma non viene presentato come URL dell'app già distribuita.

L'automazione della sessione browser personale non è disponibile nell'ambiente di esecuzione (errore di inizializzazione sandbox). La QA visiva locale è stata comunque completata con un browser nuovo e isolato, senza utilizzare profili personali.

Dopo il deploy occorre verificare sia l'accesso del viewer autorizzato sia il blocco del visitatore anonimo. Queste due prove Cloud non sono ancora marcate come superate. I dati necessari e i passaggi sono nel README.

## Evidenze

- `validation.json` e `tests.txt`: esito dei test automatici.
- `browser_validation.json`: verifiche desktop/mobile e durata di apertura.
- File PNG: schermate delle tre viste e della versione mobile.
- `repository_publication.json`: ricevuta locale del push, esclusa dal repository per evitare riferimenti ricorsivi al commit.
