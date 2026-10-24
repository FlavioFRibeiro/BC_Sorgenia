# Diagnostica dei dati

Generata da R; le numerosita attese sono riferimenti, non parametri del calcolo.

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

Le colonne originali sono lette come testo per preservarle. I tipi analitici sono Date, integer e double.

| campo | tipo_originale | mancanti_o_vuoti |
| --- | --- | --- |
| business_unit | character | 0 |
| DATA | character | 0 |
| ORA | character | 0 |
| proposer_description | character | 0 |
| counterparty | character | 0 |
| purpose | character | 0 |
| market | character | 0 |
| commodity | character | 0 |
| IMPORTO | character | 0 |
| VOLUME | character | 0 |

| campo_analitico | tipo | parsing_NA |
| --- | --- | --- |
| delivery_date | Date | 0 |
| delivery_hour | integer | 0 |
| importo_value | double | 0 |
| volume_value | double | 0 |

| campo_curva | mancanti_o_vuoti |
| --- | --- |
| DDATE | 0 |
| HOUR | 0 |
| MkIndex_EE_FRA_ICE | 0 |
| MkIndex_EE_ITA_ICE | 0 |
| MkIndex_EE_GER_DE_ICE | 0 |
| MkIndex_EE_SPA_ICE | 0 |

Prezzi curva mancanti/non validi nel formato lungo: 0

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

| commodity | purpose | segno_importo | Freq |
| --- | --- | --- | --- |
| ENERGY | Buy | -1 | 117960 |
| SERVICE_POWER | Buy | -1 | 0 |
| ENERGY | Sell | -1 | 6064 |
| SERVICE_POWER | Sell | -1 | 0 |
| ENERGY | Buy | 1 | 6171 |
| SERVICE_POWER | Buy | 1 | 0 |
| ENERGY | Sell | 1 | 86603 |
| SERVICE_POWER | Sell | 1 | 6 |

VOLUME zero: 0 ; negativo: 0 ; minimo/massimo: 1 / 50

Righe interamente duplicate (mantenute): 0

## Calendario di consegna

| ore_per_giorno | righe |
| --- | --- |
| 23 | 2 |
| 24 | 726 |
| 25 | 2 |

| data | ore | minimo | massimo | sequenza_1_n |
| --- | --- | --- | --- | --- |
| 29/03/2026 | 23 | 1 | 23 | TRUE |
| 25/10/2026 | 25 | 1 | 25 | TRUE |
| 28/03/2027 | 23 | 1 | 23 | TRUE |
| 31/10/2027 | 25 | 1 | 25 | TRUE |

Tutti i giorni della curva seguono la sequenza 1..n: TRUE

Le giornate brevi hanno etichette 1..23 e quelle lunghe 1..25: non sono ore civili disambiguate.
Non si deduce quale etichetta rappresenti l'ora civile ripetuta; occorre la specifica del fornitore.

Righe deal con ORA=25: 25 ; righe curve larghe HOUR=25: 2

Ore distinte osservate nei deals (unione delle righe per giorno, non controllo della completezza di ogni contratto):

| ore_distinte_per_giorno_deal | righe |
| --- | --- |
| 23 | 1 |
| 24 | 363 |
| 25 | 1 |

Giorni deal con etichette diverse dalla curva: 0

| DATA | ORA | market | match_status |
| --- | --- | --- | --- |
| 25/10/2026 | 25 | FRANCE | matched |
| 25/10/2026 | 25 | GERMANYDE | matched |
| 25/10/2026 | 25 | ITALY | matched |

## Join e calcolabilita

Righe curve lunghe: 70080 ; chiavi duplicate: 0

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

## Prezzi ENERGY ricostruiti

| purpose | righe | prezzo_minimo | prezzo_massimo | prezzi_negativi |
| --- | --- | --- | --- | --- |
| Buy | 124131 | -226,421500 | 583,438500 | 6171 |
| Sell | 92667 | -217,798500 | 592,061500 | 6064 |

Prezzi di curva negativi (tutti i mercati e anni): 1804

## Righe SERVICE_POWER (non valutate contro la curva)

| business_unit | DATA | ORA | proposer_description | counterparty | purpose | market | commodity | IMPORTO | VOLUME |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HEDGE | 01/01/2026 | 1 | Sorgenia_Trading | CONTROPARTE_3 | Sell | ITALY | SERVICE_POWER | 248403 | 2 |
| HEDGE | 01/02/2026 | 1 | Sorgenia_Trading | CONTROPARTE_3 | Sell | ITALY | SERVICE_POWER | 248403 | 2 |
| HEDGE | 01/03/2026 | 1 | Sorgenia_Trading | CONTROPARTE_3 | Sell | ITALY | SERVICE_POWER | 248403 | 2 |
| HEDGE | 01/04/2026 | 1 | Sorgenia_Trading | CONTROPARTE_5 | Sell | ITALY | SERVICE_POWER | 52781,5 | 1 |
| HEDGE | 01/05/2026 | 1 | Sorgenia_Trading | CONTROPARTE_5 | Sell | ITALY | SERVICE_POWER | 52781,5 | 1 |
| HEDGE | 01/06/2026 | 1 | Sorgenia_Trading | CONTROPARTE_5 | Sell | ITALY | SERVICE_POWER | 52781,5 | 1 |
