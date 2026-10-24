# Diagnostica dei dati - Python

Generata da Python; i riferimenti servono alla validazione e non guidano il calcolo.

| controllo | riferimento | osservato | esito |
| --- | --- | --- | --- |
| Righe deals | 216804 | 216804 | confermato |
| Righe curve larghe | 17520 | 17520 | confermato |
| Anno deals iniziale | 2026 | 2026 | confermato |
| Anno deals finale | 2026 | 2026 | confermato |
| Anno curve iniziale | 2026 | 2026 | confermato |
| Anno curve finale | 2027 | 2027 | confermato |
| Righe SERVICE_POWER | 6 | 6 | confermato |

## Campi originali e parsing

| campo_deal | mancanti_o_vuoti |
| --- | --- |
| business_unit | 0 |
| DATA | 0 |
| ORA | 0 |
| proposer_description | 0 |
| counterparty | 0 |
| purpose | 0 |
| market | 0 |
| commodity | 0 |
| IMPORTO | 0 |
| VOLUME | 0 |

| campo_curva | mancanti_o_vuoti |
| --- | --- |
| DDATE | 0 |
| HOUR | 0 |
| MkIndex_EE_FRA_ICE | 0 |
| MkIndex_EE_ITA_ICE | 0 |
| MkIndex_EE_GER_DE_ICE | 0 |
| MkIndex_EE_SPA_ICE | 0 |

| campo_analitico | tipo | parsing_NA |
| --- | --- | --- |
| delivery_date | date | 0 |
| delivery_hour | int | 0 |
| importo_value | float | 0 |
| volume_value | float | 0 |

## Categorie e segni

| business_unit | righe |
| --- | --- |
| FRWMK | 19008 |
| HEDGE | 197796 |

| proposer_description | righe |
| --- | --- |
| Sorgenia_Trading | 216804 |

| counterparty | righe |
| --- | --- |
| CONTROPARTE_1 | 186846 |
| CONTROPARTE_2 | 10944 |
| CONTROPARTE_3 | 3 |
| CONTROPARTE_4 | 19008 |
| CONTROPARTE_5 | 3 |

| purpose | righe |
| --- | --- |
| Buy | 124131 |
| Sell | 92673 |

| market | righe |
| --- | --- |
| FRANCE | 17520 |
| GERMANYDE | 62808 |
| ITALY | 136476 |

| commodity | righe |
| --- | --- |
| ENERGY | 216798 |
| SERVICE_POWER | 6 |

| commodity | purpose | segno_importo | righe |
| --- | --- | --- | --- |
| ENERGY | Buy | -1 | 117960 |
| ENERGY | Buy | 1 | 6171 |
| ENERGY | Sell | -1 | 6064 |
| ENERGY | Sell | 1 | 86603 |
| SERVICE_POWER | Sell | 1 | 6 |

Prezzi ENERGY Buy: minimo -226,421500, massimo 583,438500, negativi 6171.

Prezzi ENERGY Sell: minimo -217,798500, massimo 592,061500, negativi 6064.

VOLUME zero: 0; negativo: 0; righe interamente duplicate mantenute: 0.

Prezzi curva mancanti/non validi: 0; negativi: 1804.

## Calendario di consegna

| ore_per_giorno | giorni |
| --- | --- |
| 23 | 2 |
| 24 | 726 |
| 25 | 2 |

| data | ore | minimo | massimo | sequenza_1_n |
| --- | --- | --- | --- | --- |
| 29/03/2026 | 23 | 1 | 23 | True |
| 25/10/2026 | 25 | 1 | 25 | True |
| 28/03/2027 | 23 | 1 | 23 | True |
| 31/10/2027 | 25 | 1 | 25 | True |

Giorni deal con etichette diverse dalla curva: 0.

Righe deal con ORA=25: 25; curve larghe HOUR=25: 2.

Le etichette 1..23 e 1..25 sono conservate come chiavi di consegna, senza conversione in timestamp.

## Join e calcolabilita

Righe curva lunga: 70080; chiavi duplicate: 0 (controllo bloccante).

| match_status | righe |
| --- | --- |
| matched | 216804 |

| pnl_status | righe |
| --- | --- |
| calculated | 216798 |
| not_applicable_commodity | 6 |

| issue_codes | righe |
| --- | --- |
| OK | 216804 |

## Righe SERVICE_POWER

| business_unit | DATA | ORA | proposer_description | counterparty | purpose | market | commodity | IMPORTO | VOLUME |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HEDGE | 01/01/2026 | 1 | Sorgenia_Trading | CONTROPARTE_3 | Sell | ITALY | SERVICE_POWER | 248403 | 2 |
| HEDGE | 01/02/2026 | 1 | Sorgenia_Trading | CONTROPARTE_3 | Sell | ITALY | SERVICE_POWER | 248403 | 2 |
| HEDGE | 01/03/2026 | 1 | Sorgenia_Trading | CONTROPARTE_3 | Sell | ITALY | SERVICE_POWER | 248403 | 2 |
| HEDGE | 01/04/2026 | 1 | Sorgenia_Trading | CONTROPARTE_5 | Sell | ITALY | SERVICE_POWER | 52781,5 | 1 |
| HEDGE | 01/05/2026 | 1 | Sorgenia_Trading | CONTROPARTE_5 | Sell | ITALY | SERVICE_POWER | 52781,5 | 1 |
| HEDGE | 01/06/2026 | 1 | Sorgenia_Trading | CONTROPARTE_5 | Sell | ITALY | SERVICE_POWER | 52781,5 | 1 |
