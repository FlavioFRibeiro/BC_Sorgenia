# Sorgenia Trading - Sintesi del business case

Elaborazione in R dei profili di consegna e delle curve power, con dettaglio orario, riepilogo mensile e bozza di Conto Economico riferita ai deal forniti.

## 1-2. Lettura dei deal e delle curve

DEAL.csv contiene 216.804 righe del 2026: 216.798 ENERGY e 6 SERVICE_POWER, sui mercati italiano, tedesco e francese. CurveOrariePower.csv contiene i prezzi orari dei quattro mercati Italia, Germania, Francia e Spagna.

I file sono letti con separatore punto e virgola, virgola decimale e date gg/mm/aaaa. Per il business case si assumono importi in EUR, volumi ENERGY in MWh e prezzi in EUR/MWh.

## 3. Associazione del prezzo di mercato

Le curve sono trasformate dal formato largo al formato lungo e associate ai deal per data, numero d'ora e mercato. ITALY corrisponde alla curva ITA, GERMANYDE a GER_DE e FRANCE a FRA. Il join mantiene ogni riga deal e verifica l'unicita della chiave curva. Le ore dei giorni da 23 e 25 ore sono preservate.

Risultato: 216.804 righe associate a una curva utilizzabile su 216.804; 0 righe con problemi nei dati.

## 4. Calcolo del P&L

Si adotta la convenzione IMPORTO firmato, coerente con i dati: direction = +1 per Sell e -1 per Buy. Il prezzo contrattuale e il P&L ENERGY sono calcolati come segue:

```text
contract_price = IMPORTO / (direction * VOLUME)
pnl = IMPORTO - direction * VOLUME * market_price
```

Per Buy il risultato e' (prezzo mercato - prezzo contratto) x volume; per Sell e' (prezzo contratto - prezzo mercato) x volume. Un P&L positivo indica condizioni contrattuali favorevoli rispetto alla curva. I prezzi negativi mantengono il proprio segno.

Esempio: un acquisto a 80 con mercato a 100 e volume 2 genera +40; una vendita a -10 con mercato a -20 e volume 2 genera +20.

SERVICE_POWER e' trattato come corrispettivo per servizi: le righe sono mantenute e associate alla curva, con P&L NA perche' la prestazione non e' direttamente confrontabile con il prezzo dell'energia.

| Mercato | PnL_ENERGY_EUR |
| --- | --- |
| FRANCE | 28.908,00 |
| GERMANYDE | 880.469,31 |
| ITALY | -1.450.018,00 |

**P&L ENERGY complessivo: -540.640,69 EUR.**

## 5-6. Aggregazione mensile ed esportazione

Le righe sono aggregate esclusivamente per anno, mese, counterparty, purpose e market: il risultato contiene 117 gruppi. Gli importi e il P&L orari vengono sommati; volumi ENERGY e importi servizi restano distinti.

I risultati sono esportati in [deals_enriched_pnl.csv](deals_enriched_pnl.csv), con prezzi e P&L per riga, e [monthly_summary.csv](monthly_summary.csv), con gli aggregati mensili. Entrambi usano il formato CSV per Excel italiano: separatore punto e virgola, virgola decimale e UTF-8 con BOM.

## 7. Bozza di Conto Economico

Prospetto gestionale relativo al dataset. La classificazione usa commodity e purpose: ENERGY Sell nei ricavi energia, SERVICE_POWER Sell nei ricavi servizi ed ENERGY Buy nei costi, con segno invertito rispetto a IMPORTO.

| Voce | EUR |
| --- | --- |
| Ricavi da vendita di energia | 106.297.856,58 |
| Ricavi da servizi | 903.553,50 |
| Totale ricavi | 107.201.410,08 |
| Costi di acquisto di energia | 121.416.249,94 |
| Margine di contribuzione (dataset) | -14.214.839,86 |

Margine di contribuzione = ricavi energia + ricavi servizi - costi di acquisto energia. Nel perimetro analizzato i costi di acquisto superano i ricavi complessivi.

Il margine coincide qui con il saldo degli importi contrattuali. Il P&L ENERGY misura invece lo scostamento rispetto alle curve: i due risultati rispondono a domande diverse e non si sommano. Il P&L e' un confronto economico con il benchmark fornito, non una misura di risultato realizzato.

I controlli su chiavi, segni, ore di consegna, conservazione delle righe e riconciliazione mensile sono documentati in [diagnostics.md](diagnostics.md) e [validation.txt](validation.txt). Metodologia tecnica e dizionario delle colonne: [NOTE_TECNICHE_R.md](../../Code/NOTE_TECNICHE_R.md).
