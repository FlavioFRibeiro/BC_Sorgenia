"""Test mirati, eseguiti prima di elaborare i file reali."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from compare import compare_csv, compare_reports
from functions import (DEAL_COLUMNS, MARKET_MAP, calculate_pnl, contractual_statement,
                       curves_to_long, enrich_deals, export_csv, monthly_summary,
                       parse_date, parse_decimal, parse_hour, prepare_deals,
                       reconcile_monthly, require, strict_sum, verify_csv)


def expect_error(function):
    try:
        function()
    except ValueError:
        return
    raise ValueError("Era atteso un errore bloccante")


def run_tests():
    raw = []
    for purpose, amount, volume, commodity in zip(
            ["Buy", "Sell", "Buy", "Sell", "Buy", "Sell"], ["-160", "240", "40", "-20", "0", "100"],
            ["2", "2", "2", "2", "0", "1"], ["ENERGY"] * 5 + ["SERVICE_POWER"]):
        raw.append(dict(zip(DEAL_COLUMNS, ["TEST", "25/10/2026", "25", "TEST", "TEST", purpose,
                                          "ITALY", commodity, amount, volume])))
    cv = {"DDATE": "25/10/2026", "HOUR": "25", **{k: "100" for k in MARKET_MAP.values()}}
    def pipeline(rows, curves):
        return calculate_pnl(enrich_deals(prepare_deals(rows), curves_to_long(curves)))
    d = pipeline(raw, [cv])
    require([x["pnl"] for x in d[:4]] == [40, 40, 240, -220], "Segni P&L errati")
    require([x["contract_price"] for x in d[:4]] == [80, 120, -20, -10], "Prezzi negativi cancellati")
    negative = dict(cv, **{MARKET_MAP["ITALY"]: "-10"})
    require(pipeline(raw, [negative])[2]["pnl"] == 20, "Buy con curva negativa errato")
    negative[MARKET_MAP["ITALY"]] = "-20"
    require(pipeline(raw, [negative])[3]["pnl"] == 20, "Sell con curva negativa errato")
    require(d[4]["pnl"] is None and d[4]["contract_price"] is None and d[4]["row_problem"], "Volume zero non gestito")
    require(not d[5]["pnl_applicable"] and d[5]["pnl"] is None and not d[5]["row_problem"] and d[5]["curve_match_count"] == 1,
            "SERVICE_POWER non gestito")
    require(all(x["delivery_hour"] == 25 and x["HOUR"] == "25" for x in d), "Ora 25 persa")
    require(len(d) == len(raw) and all(all(a[k] == b[k] for k in DEAL_COLUMNS) for a, b in zip(raw, d)), "Join non conservativo")
    expect_error(lambda: curves_to_long([cv, cv]))
    missing = dict(cv, **{MARKET_MAP["ITALY"]: ""})
    require(all(x["pnl"] is None and x["curve_match_count"] == 1 for x in pipeline(raw, [missing])), "Prezzo assente sostituito")
    bad = deepcopy(raw)
    for row, key, value in [(0, "ORA", "24"), (1, "IMPORTO", "invalid"), (2, "DATA", "31/02/2026"),
                            (3, "market", "UNKNOWN"), (4, "purpose", "OTHER")]:
        bad[row][key] = value
    require(all(x["row_problem"] and not x["pnl_calculable"] for x in pipeline(bad, [cv])[:5]), "Dati invalidi non segnalati")
    monthly = monthly_summary(d)
    buy = next(x for x in monthly if x["purpose"] == "Buy")
    require(buy["pnl_energy"] is None and buy["pnl_energy_calculable_subtotal"] == 280, "Gruppo incompleto nascosto")
    service = monthly_summary(d[5:])[0]
    require(service["pnl_energy"] is None and service["volume_energy"] is None, "Gruppo servizi trasformato in zero")
    require(strict_sum([]) is None and strict_sum([1, None]) is None, "Somma nasconde assenze")
    require(len(pipeline(raw + [raw[0]], [cv])) == len(raw) + 1, "Deal uguali eliminati")
    require(all(parse_decimal(x) is None for x in ("1.23", "1,2,3", "", "Inf")), "Parsing numerico permissivo")
    require(all(parse_date(x) is None for x in ("31/02/2026", "2026-01-01", "1/1/2026")), "Parsing date permissivo")
    require(all(parse_hour(x) is None for x in ("0", "26", "1,5")), "Parsing ore permissivo")
    ce = contractual_statement(d)
    require((ce["revenue_energy"], ce["cost_energy"], ce["revenue_service"], ce["known_margin"]) == (220, 120, 100, 200),
            "CE classificato per segno invece che per purpose")
    unknown = deepcopy(d)
    unknown[0]["commodity"] = "OTHER"
    require(contractual_statement(unknown)["known_margin"] is None, "CE ignora categoria ignota")
    reconcile_monthly(d, monthly)
    broken = deepcopy(monthly)
    broken[0]["n_rows"] += 1
    expect_error(lambda: reconcile_monthly(d, broken))
    with TemporaryDirectory() as tmp:
        output = Path(tmp) / "test.csv"
        reference = Path(tmp) / "reference.csv"
        export_csv(d, output)
        verify_csv(d, output)
        export_csv(d, reference)
        require(compare_csv(reference, output, detail=True)["bytes_equal"], "Confronto CSV esatto fallito")
        corrupted = deepcopy(d)
        corrupted[0]["pnl"] += 1
        export_csv(corrupted, output)
        expect_error(lambda: compare_csv(reference, output, detail=True))
        corrupted = deepcopy(d)
        corrupted[0]["counterparty"] = "ALTERATA"
        export_csv(corrupted, output)
        expect_error(lambda: compare_csv(reference, output, detail=True))
        r_report, py_report = Path(tmp) / "r.md", Path(tmp) / "python.md"
        r_report.write_text("Elaborazione in R: 40,00", encoding="utf-8")
        py_report.write_text("Elaborazione in Python: 40,00", encoding="utf-8")
        compare_reports(r_report, py_report)
        py_report.write_text("Elaborazione in Python: 40,01", encoding="utf-8")
        expect_error(lambda: compare_reports(r_report, py_report))
    print("Test mirati Python: OK", flush=True)


if __name__ == "__main__":
    run_tests()
