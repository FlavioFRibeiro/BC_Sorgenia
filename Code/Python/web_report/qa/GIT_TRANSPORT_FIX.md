# Correzione del trasporto dello snapshot su GitHub

Errore osservato nel deploy Streamlit: `Snapshot alterato o incompleto: monthly_reference.csv`.

Il confronto diretto con il blob pubblicato ha confermato che Git aveva convertito esclusivamente le terminazioni di riga da CRLF a LF:

| Contenuto | Byte | SHA-256 |
| --- | --- | --- |
| CSV validato locale | 20241 | 86d7b5fb57d6c97243e16eeaa833202476a75fffd714706c5a5c490f1db97702 |
| CSV precedentemente su GitHub | 20123 | 596027387084bd29098037b6f21db77f664091a4075d88aa94766310037ce0c8 |

Il file remoto coincide esattamente con il locale dopo la sostituzione `CRLF → LF`. Il manifesto verificava correttamente i byte originali e ha quindi rifiutato il file convertito. Nessun importo o risultato finanziario era cambiato.

La pubblicazione ora scrive una `.gitattributes` che disabilita la conversione testuale per i file dello snapshot e per il modulo finanziario verificato tramite hash. Il payload viene aggiunto nuovamente all'index con `--renormalize`; gli SHA-256 dei blob Git vengono confrontati prima del commit/push e dopo il commit.

Un test di regressione riproduce il problema con `core.autocrlf=true`, verifica che il controllo rifiuti il payload convertito e conferma la preservazione dei byte dopo la correzione in un nuovo checkout con `core.autocrlf=false`, come su Linux. I controlli di integrità rimangono attivi.
