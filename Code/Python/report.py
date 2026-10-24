"""Report italiano e diagnostica, generati esclusivamente dai risultati Python."""
from collections import Counter, defaultdict
from pathlib import Path

from functions import contractual_statement, parse_date, parse_hour, strict_sum


def fmt(value, digits=2):
    if value is None:
        return "NA / non disponibile"
    if abs(value) < 0.5 * 10 ** (-digits):
        value = 0
    return f"{value:,.{digits}f}".translate(str.maketrans(",.", ".,"))


def md_table(columns, rows):
    def line(row):
        return "| " + " | ".join(str(v).replace("|", "/") for v in row) + " |"
    return [line(columns), line(["---"] * len(columns)), *(line(row) for row in rows)]


def write_report(deals, monthly, path):
    energy = [x for x in deals if x["commodity"] == "ENERGY"]
    n_service = sum(x["commodity"] == "SERVICE_POWER" for x in deals)
    statement = contractual_statement(deals)
    market_groups = defaultdict(list)
    for row in energy:
        market_groups[row["market"]].append(row["pnl"])
    agg = [(market, fmt(strict_sum(values))) for market, values in sorted(market_groups.items())]
    ce = [("Ricavi da vendita di energia", fmt(statement["revenue_energy"])),
          ("Ricavi da servizi", fmt(statement["revenue_service"])),
          ("Totale ricavi", fmt(statement["revenue_energy"] + statement["revenue_service"]) if all(statement[k] is not None for k in ("revenue_energy", "revenue_service")) else fmt(None)),
          ("Costi di acquisto di energia", fmt(statement["cost_energy"])),
          ("Margine di contribuzione (dataset)", fmt(statement["known_margin"]))]
    years = ", ".join(str(y) for y in sorted({x["delivery_date"].year for x in deals if x["delivery_date"] is not None}))
    lines = ["# Sorgenia Trading - Sintesi del business case", "",
        "Elaborazione in Python dei profili di consegna e delle curve power, con dettaglio orario, riepilogo mensile e bozza di Conto Economico riferita ai deal forniti.", "",
        "## 1-2. Lettura dei deal e delle curve", "",
        f"DEAL.csv contiene {fmt(len(deals), 0)} righe del {years}: {fmt(len(energy), 0)} ENERGY e {fmt(n_service, 0)} SERVICE_POWER, sui mercati italiano, tedesco e francese. CurveOrariePower.csv contiene i prezzi orari dei quattro mercati Italia, Germania, Francia e Spagna.", "",
        "I file sono letti con separatore punto e virgola, virgola decimale e date gg/mm/aaaa. Per il business case si assumono importi in EUR, volumi ENERGY in MWh e prezzi in EUR/MWh.", "",
        "## 3. Associazione del prezzo di mercato", "",
        "Le curve sono trasformate dal formato largo al formato lungo e associate ai deal per data, numero d'ora e mercato. ITALY corrisponde alla curva ITA, GERMANYDE a GER_DE e FRANCE a FRA. Il join mantiene ogni riga deal e verifica l'unicita della chiave curva. Le ore dei giorni da 23 e 25 ore sono preservate.", "",
        f"Risultato: {fmt(sum(x['match_status'] == 'matched' for x in deals), 0)} righe associate a una curva utilizzabile su {fmt(len(deals), 0)}; {fmt(sum(x['row_problem'] for x in deals), 0)} righe con problemi nei dati.", "",
        "## 4. Calcolo del P&L", "",
        "Si adotta la convenzione IMPORTO firmato, coerente con i dati: direction = +1 per Sell e -1 per Buy. Il prezzo contrattuale e il P&L ENERGY sono calcolati come segue:", "",
        "```text", "contract_price = IMPORTO / (direction * VOLUME)",
        "pnl = IMPORTO - direction * VOLUME * market_price", "```", "",
        "Per Buy il risultato e' (prezzo mercato - prezzo contratto) x volume; per Sell e' (prezzo contratto - prezzo mercato) x volume. Un P&L positivo indica condizioni contrattuali favorevoli rispetto alla curva. I prezzi negativi mantengono il proprio segno.", "",
        "Esempio: un acquisto a 80 con mercato a 100 e volume 2 genera +40; una vendita a -10 con mercato a -20 e volume 2 genera +20.", "",
        "SERVICE_POWER e' trattato come corrispettivo per servizi: le righe sono mantenute e associate alla curva, con P&L NA perche' la prestazione non e' direttamente confrontabile con il prezzo dell'energia.", "",
        *md_table(["Mercato", "PnL_ENERGY_EUR"], agg), "",
        f"**P&L ENERGY complessivo: {fmt(strict_sum(x['pnl'] for x in energy))} EUR.**", "",
        "## 5-6. Aggregazione mensile ed esportazione", "",
        f"Le righe sono aggregate esclusivamente per anno, mese, counterparty, purpose e market: il risultato contiene {fmt(len(monthly), 0)} gruppi. Gli importi e il P&L orari vengono sommati; volumi ENERGY e importi servizi restano distinti.", "",
        "I risultati sono esportati in [deals_enriched_pnl.csv](deals_enriched_pnl.csv), con prezzi e P&L per riga, e [monthly_summary.csv](monthly_summary.csv), con gli aggregati mensili. Entrambi usano il formato CSV per Excel italiano: separatore punto e virgola, virgola decimale e UTF-8 con BOM.", "",
        "## 7. Bozza di Conto Economico", "",
        "Prospetto gestionale relativo al dataset. La classificazione usa commodity e purpose: ENERGY Sell nei ricavi energia, SERVICE_POWER Sell nei ricavi servizi ed ENERGY Buy nei costi, con segno invertito rispetto a IMPORTO.", "",
        *md_table(["Voce", "EUR"], ce), "",
        "Margine di contribuzione = ricavi energia + ricavi servizi - costi di acquisto energia. Nel perimetro analizzato i costi di acquisto superano i ricavi complessivi.", "",
        "Il margine coincide qui con il saldo degli importi contrattuali. Il P&L ENERGY misura invece lo scostamento rispetto alle curve: i due risultati rispondono a domande diverse e non si sommano. Il P&L e' un confronto economico con il benchmark fornito, non una misura di risultato realizzato.", "",
        "I controlli su chiavi, segni, ore di consegna, conservazione delle righe e riconciliazione mensile sono documentati in [diagnostics.md](diagnostics.md) e [validation.txt](validation.txt). Metodologia tecnica e dizionario delle colonne: [NOTE_TECNICHE_PYTHON.md](../../Code/NOTE_TECNICHE_PYTHON.md)."]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_diagnostics(raw_deals, raw_curves, deals, curves, path):
    years_d = sorted({x["delivery_date"].year for x in deals if x["delivery_date"]})
    years_c = sorted({x["delivery_date"].year for x in curves})
    references = [("Righe deals", 216804, len(deals)), ("Righe curve larghe", 17520, len(raw_curves)),
                  ("Anno deals iniziale", 2026, years_d[0] if years_d else None),
                  ("Anno deals finale", 2026, years_d[-1] if years_d else None),
                  ("Anno curve iniziale", 2026, years_c[0]), ("Anno curve finale", 2027, years_c[-1]),
                  ("Righe SERVICE_POWER", 6, sum(x["commodity"] == "SERVICE_POWER" for x in deals))]
    lines = ["# Diagnostica dei dati - Python", "", "Generata da Python; i riferimenti servono alla validazione e non guidano il calcolo.", "",
             *md_table(["controllo", "riferimento", "osservato", "esito"],
                       [(k, ref, val, "confermato" if ref == val else "diverso: investigare") for k, ref, val in references]), "",
             "## Campi originali e parsing", ""]
    for label, raw in (("deal", raw_deals), ("curva", raw_curves)):
        lines += md_table([f"campo_{label}", "mancanti_o_vuoti"],
                          [(k, sum(x[k].strip() == "" for x in raw)) for k in raw[0]]) + [""]
    lines += md_table(["campo_analitico", "tipo", "parsing_NA"],
                      [(k, typ, sum(x[k] is None for x in deals)) for k, typ in
                       (("delivery_date", "date"), ("delivery_hour", "int"), ("importo_value", "float"), ("volume_value", "float"))]) + [""]
    lines += ["## Categorie e segni", ""]
    for field in ("business_unit", "proposer_description", "counterparty", "purpose", "market", "commodity"):
        lines += md_table([field, "righe"], sorted(Counter(x[field] for x in deals).items())) + [""]
    signs = Counter((x["commodity"], x["purpose"], None if x["importo_value"] is None else
                     (x["importo_value"] > 0) - (x["importo_value"] < 0)) for x in deals)
    lines += md_table(["commodity", "purpose", "segno_importo", "righe"],
                      [(*key, n) for key, n in sorted(signs.items(), key=lambda x: str(x[0]))]) + [""]
    for purpose in sorted({x["purpose"] for x in deals}):
        prices = [x["contract_price"] for x in deals if x["purpose"] == purpose and x["contract_price"] is not None]
        if prices:
            lines += [f"Prezzi ENERGY {purpose}: minimo {fmt(min(prices), 6)}, massimo {fmt(max(prices), 6)}, negativi {sum(p < 0 for p in prices)}.", ""]
    volumes = [x["volume_value"] for x in deals if x["volume_value"] is not None]
    duplicate_count = len(raw_deals) - len({tuple(x.values()) for x in raw_deals})
    lines += [f"VOLUME zero: {sum(x == 0 for x in volumes)}; negativo: {sum(x < 0 for x in volumes)}; righe interamente duplicate mantenute: {duplicate_count}.", "",
              f"Prezzi curva mancanti/non validi: {sum(x['market_price'] is None for x in curves)}; negativi: {sum(x['market_price'] is not None and x['market_price'] < 0 for x in curves)}.", "",
              "## Calendario di consegna", ""]
    days = defaultdict(list)
    for row in raw_curves:
        days[row["DDATE"]].append(parse_hour(row["HOUR"]))
    lines += md_table(["ore_per_giorno", "giorni"], sorted(Counter(len(h) for h in days.values()).items())) + [""]
    lines += md_table(["data", "ore", "minimo", "massimo", "sequenza_1_n"],
                      [(dt, len(days[dt]), min(days[dt]), max(days[dt]), sorted(days[dt]) == list(range(1, len(days[dt]) + 1)))
                       for dt in sorted(days, key=parse_date) if len(days[dt]) != 24]) + [""]
    deal_days = defaultdict(set)
    for row in deals:
        if row["delivery_date"]:
            deal_days[row["DATA"]].add(row["delivery_hour"])
    lines += [f"Giorni deal con etichette diverse dalla curva: {sum(h != set(days.get(dt, [])) for dt, h in deal_days.items())}.", "",
              f"Righe deal con ORA=25: {sum(x['delivery_hour'] == 25 for x in deals)}; curve larghe HOUR=25: {sum(parse_hour(x['HOUR']) == 25 for x in raw_curves)}.", "",
              "Le etichette 1..23 e 1..25 sono conservate come chiavi di consegna, senza conversione in timestamp.", "",
              "## Join e calcolabilita", "", f"Righe curva lunga: {len(curves)}; chiavi duplicate: 0 (controllo bloccante).", ""]
    for field in ("match_status", "pnl_status", "issue_codes"):
        lines += md_table([field, "righe"], sorted(Counter(x[field] for x in deals).items())) + [""]
    lines += ["## Righe SERVICE_POWER", "",
              *md_table(list(raw_deals[0]), [list(x.values()) for x in raw_deals if x["commodity"] == "SERVICE_POWER"])]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
