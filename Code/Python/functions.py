"""Pipeline indipendente in Python standard: importazione, join, P&L e mensile."""
import csv
import hashlib
import math
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, localcontext
from functools import lru_cache
from pathlib import Path

MARKET_MAP = {"ITALY": "MkIndex_EE_ITA_ICE", "GERMANYDE": "MkIndex_EE_GER_DE_ICE",
              "FRANCE": "MkIndex_EE_FRA_ICE", "SPAIN": "MkIndex_EE_SPA_ICE"}
DEAL_COLUMNS = ["business_unit", "DATA", "ORA", "proposer_description", "counterparty",
                "purpose", "market", "commodity", "IMPORTO", "VOLUME"]
CURVE_COLUMNS = ["DDATE", "HOUR", *MARKET_MAP.values()]
MONTH_KEY = ["anno", "mese", "counterparty", "purpose", "market"]
DETAIL_NUMERIC = {"deal_row_id", "delivery_hour", "importo_value", "volume_value", "direction",
                  "curve_match_count", "curve_row_id", "market_price", "contract_price",
                  "pnl", "market_value_signed"}
NUMBER = re.compile(r"[+-]?[0-9]+(?:,[0-9]+)?\Z")
DATE = re.compile(r"[0-9]{2}/[0-9]{2}/[0-9]{4}\Z")
HOUR = re.compile(r"[0-9]+\Z")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def near(a, b):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)


def blank(value):
    return value is None or value.strip() == ""


def read_source(path, required):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", strict=True)
        require(reader.fieldnames is not None and len(reader.fieldnames) == len(set(reader.fieldnames)),
                "Intestazioni mancanti o duplicate")
        require(set(reader.fieldnames) == set(required), f"Schema inatteso: {path}")
        rows = []
        for line, row in enumerate(reader, 2):
            require(None not in row and all(v is not None for v in row.values()),
                    f"Numero campi non valido: {path}, riga {line}")
            rows.append(row)
    require(bool(rows), f"File vuoto: {path}")
    return rows


@lru_cache(maxsize=100000)
def parse_decimal(value):
    if value is None or not NUMBER.fullmatch(value):
        return None
    number = float(value.replace(",", "."))
    return number if math.isfinite(number) else None


@lru_cache(maxsize=4096)
def parse_date(value):
    if value is None or not DATE.fullmatch(value):
        return None
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y").date()
        return parsed if parsed.strftime("%d/%m/%Y") == value else None
    except ValueError:
        return None


@lru_cache(maxsize=4096)
def parse_hour(value):
    if value is None or not HOUR.fullmatch(value):
        return None
    parsed = int(value)
    return parsed if 1 <= parsed <= 25 else None


def prepare_deals(raw):
    result = []
    for row_id, row in enumerate(raw, 1):
        out = dict(row)
        out.update(deal_row_id=row_id, delivery_date=parse_date(row["DATA"]),
                   delivery_hour=parse_hour(row["ORA"]), importo_value=parse_decimal(row["IMPORTO"]),
                   volume_value=parse_decimal(row["VOLUME"]),
                   direction={"Buy": -1, "Sell": 1}.get(row["purpose"]),
                   curve_index_expected=MARKET_MAP.get(row["market"]))
        result.append(out)
    return result


def delivery_key(row):
    return row["delivery_date"], row["delivery_hour"], row["market"]


def curves_to_long(raw):
    dates = [parse_date(x["DDATE"]) for x in raw]
    hours = [parse_hour(x["HOUR"]) for x in raw]
    require(all(x is not None for x in dates + hours), "Chiave curva non valida")
    result, seen = [], set()
    for market, index in MARKET_MAP.items():
        for i, row in enumerate(raw):
            key = dates[i], hours[i], market
            require(key not in seen, f"Chiave curva duplicata, nessuna scelta arbitraria: {key}")
            seen.add(key)
            result.append(dict(curve_row_id=i + 1, DDATE=row["DDATE"], HOUR=row["HOUR"],
                               delivery_date=dates[i], delivery_hour=hours[i], market=market,
                               curve_index=index, market_price_raw=row[index], market_price=parse_decimal(row[index])))
    return result


def enrich_deals(deals, curves):
    lookup = {delivery_key(x): x for x in curves}
    require(len(lookup) == len(curves), "Join rifiutato: chiave curva duplicata")
    result = []
    for row in deals:
        invalid = any(row[k] is None for k in ("delivery_date", "delivery_hour", "curve_index_expected"))
        curve = None if invalid else lookup.get(delivery_key(row))
        out = dict(row)
        out["curve_match_count"] = int(curve is not None)
        for field in ("curve_row_id", "DDATE", "HOUR", "curve_index", "market_price_raw", "market_price"):
            out[field] = curve[field] if curve is not None else None
        out["match_status"] = ("invalid_delivery_key_or_market" if invalid else
                               "no_curve_match" if curve is None else
                               "matched_missing_or_invalid_price" if curve["market_price"] is None else "matched")
        require(all(out[k] == row[k] for k in DEAL_COLUMNS + ["importo_value", "volume_value"]),
                "Il join ha alterato i dati originali")
        result.append(out)
    require(len(result) == len(deals), "Il join ha cambiato il numero di righe")
    return result


def calculate_pnl(deals):
    for row in deals:
        applicable = row["commodity"] == "ENERGY"
        issues = []
        validations = [
            (row["delivery_date"] is None, "invalid_date"),
            (row["delivery_hour"] is None, "invalid_hour"),
            (row["direction"] is None, "unknown_purpose"),
            (row["curve_index_expected"] is None, "unknown_market"),
            (row["commodity"] not in ("ENERGY", "SERVICE_POWER"), "unknown_commodity"),
            (row["importo_value"] is None, "missing_or_invalid_importo"),
            (row["volume_value"] is None, "missing_or_invalid_volume"),
            (row["volume_value"] is not None and row["volume_value"] <= 0, "nonpositive_volume"),
            (any(blank(row[k]) for k in ("counterparty", "business_unit", "proposer_description")), "missing_dimension"),
            (row["match_status"] != "matched", "curve_unavailable")]
        issues.extend(label for problem, label in validations if problem)
        row["pnl_applicable"] = applicable
        row["row_problem"] = bool(issues)
        row["issue_codes"] = "|".join(issues) if issues else "OK"
        valid_contract = applicable and all(row[k] is not None for k in ("importo_value", "volume_value", "direction"))
        valid_contract = valid_contract and row["volume_value"] > 0
        row["contract_price"] = row["importo_value"] / (row["direction"] * row["volume_value"]) if valid_contract else None
        row["pnl_calculable"] = applicable and not issues
        row["pnl"] = row["market_value_signed"] = None
        if row["pnl_calculable"]:
            market_value = row["direction"] * row["volume_value"] * row["market_price"]
            pnl = row["importo_value"] - market_value
            require(math.isfinite(pnl) and math.isfinite(market_value), "Overflow nel calcolo P&L")
            row["pnl"], row["market_value_signed"] = pnl, market_value
            expected = row["direction"] * (row["contract_price"] - row["market_price"]) * row["volume_value"]
            require(near(pnl, expected), "Formule P&L non coerenti")
        row["pnl_status"] = ("not_applicable_commodity" if not applicable else
                             "calculated" if row["pnl_calculable"] else "not_calculable_data_issue")
    return deals


def strict_sum(values, empty=None):
    values = list(values)
    if not values:
        return empty
    if any(x is None or not math.isfinite(x) for x in values):
        return None
    return math.fsum(values)


def contractual_statement(deals):
    revenues = strict_sum((x["importo_value"] for x in deals if x["commodity"] == "ENERGY" and x["purpose"] == "Sell"), empty=0)
    purchases = strict_sum((x["importo_value"] for x in deals if x["commodity"] == "ENERGY" and x["purpose"] == "Buy"), empty=0)
    costs = -purchases if purchases is not None else None
    services = strict_sum((x["importo_value"] for x in deals if x["commodity"] == "SERVICE_POWER" and x["purpose"] == "Sell"), empty=0)
    unclassified = sum(not (x["commodity"] == "ENERGY" and x["purpose"] in ("Buy", "Sell") or
                           x["commodity"] == "SERVICE_POWER" and x["purpose"] == "Sell") for x in deals)
    margin = revenues + services - costs if unclassified == 0 and all(x is not None for x in (revenues, services, costs)) else None
    balance = strict_sum(x["importo_value"] for x in deals)
    if unclassified == 0:
        require(near(margin, balance), "Bozza CE non riconciliata")
    return dict(revenue_energy=revenues, cost_energy=costs, revenue_service=services,
                known_margin=margin, balance=balance, n_unclassified=unclassified)


def month_key(row):
    dt = row["delivery_date"]
    return (dt.year if dt else None, dt.month if dt else None, row["counterparty"], row["purpose"], row["market"])


def sort_key(key):
    return tuple((value is None, value) for value in key)


def sort_deals(rows):
    rows.sort(key=lambda x: sort_key((x["delivery_date"], x["delivery_hour"], x["market"],
                                     x["counterparty"], x["purpose"], x["deal_row_id"])))


def monthly_summary(deals):
    groups = defaultdict(list)
    for row in deals:
        groups[month_key(row)].append(row)
    result = []
    for key in sorted(groups, key=sort_key):
        rows = groups[key]
        energy = [x for x in rows if x["commodity"] == "ENERGY"]
        service = [x for x in rows if x["commodity"] == "SERVICE_POWER"]
        valid = [x for x in rows if x["pnl_calculable"]]
        out = dict(zip(MONTH_KEY, key))
        out.update(n_rows=len(rows), importo_total=strict_sum(x["importo_value"] for x in rows),
                   n_energy=len(energy), volume_energy=strict_sum(x["volume_value"] if x["volume_value"] is not None and x["volume_value"] > 0 else None for x in energy),
                   market_value_signed_energy=strict_sum(x["market_value_signed"] for x in energy),
                   pnl_energy=strict_sum(x["pnl"] for x in energy), n_service_power=len(service),
                   importo_service_power=strict_sum((x["importo_value"] for x in service), empty=0),
                   n_pnl_calculable=len(valid), n_problem_rows=sum(x["row_problem"] for x in rows),
                   n_energy_not_calculable=len(energy) - len(valid), n_pnl_not_applicable=len(rows) - len(energy),
                   n_curve_unavailable=sum(x["match_status"] != "matched" for x in rows),
                   pnl_energy_calculable_subtotal=strict_sum(x["pnl"] for x in valid))
        result.append(out)
    require(sum(x["n_rows"] for x in result) == len(deals), "Righe mensili non riconciliate")
    return result


def reconcile_monthly(deals, monthly):
    """Secondo percorso: contributi per riga accumulati con Decimal, NA propagati."""
    groups = {}
    with localcontext() as ctx:
        ctx.prec = 80
        for row in deals:
            en, sv, ok = row["commodity"] == "ENERGY", row["commodity"] == "SERVICE_POWER", row["pnl_calculable"]
            volume = row["volume_value"]
            values = dict(n_rows=1, importo_total=row["importo_value"], n_energy=int(en),
                          volume_energy=(volume if volume is not None and volume > 0 else None) if en else 0,
                          market_value_signed_energy=row["market_value_signed"] if en else 0,
                          pnl_energy=row["pnl"] if en else 0, n_service_power=int(sv),
                          importo_service_power=row["importo_value"] if sv else 0, n_pnl_calculable=int(ok),
                          n_problem_rows=int(row["row_problem"]), n_energy_not_calculable=int(en and not ok),
                          n_pnl_not_applicable=int(not en), n_curve_unavailable=int(row["match_status"] != "matched"),
                          pnl_energy_calculable_subtotal=row["pnl"] if ok else 0)
            key = month_key(row)
            acc = groups.setdefault(key, {k: Decimal(0) for k in values})
            for name, value in values.items():
                acc[name] = None if value is None or acc[name] is None else acc[name] + Decimal(value)
        require(len(groups) == len(monthly), "Numero gruppi mensili errato")
        for row in monthly:
            acc = groups[tuple(row[k] for k in MONTH_KEY)]
            if acc["n_energy"] == 0:
                for name in ("volume_energy", "market_value_signed_energy", "pnl_energy"):
                    acc[name] = None
            if acc["n_pnl_calculable"] == 0:
                acc["pnl_energy_calculable_subtotal"] = None
            for name, value in acc.items():
                require(near(row[name], float(value) if value is not None else None), f"Riconciliazione mensile fallita: {name}")


def display_value(value):
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, (int, float)):
        return format(value, ".17g").replace(".", ",")
    return value


def export_csv(rows, path):
    require(bool(rows), "Tabella di output vuota")
    def quote(text):
        return '"' + text.replace('"', '""') + '"'
    columns = list(rows[0])
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        handle.write(";".join(quote(x) for x in columns) + "\r\n")
        for row in rows:
            fields = []
            for name in columns:
                value = row[name]
                text = display_value(value)
                fields.append(text if value is None or isinstance(value, bool) else quote(text))
            handle.write(";".join(fields) + "\r\n")


def verify_csv(expected, path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", strict=True)
        require(reader.fieldnames == list(expected[0]), f"Schema CSV alterato: {path}")
        count = 0
        totals = defaultdict(list)
        for count, source in enumerate(expected, 1):
            actual = next(reader, None)
            require(actual is not None, "Righe perse nel CSV")
            for name, value in source.items():
                raw = actual[name]
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    parsed = float(raw.replace(",", "."))
                    require(parsed == value, f"Round-trip numerico non esatto: {name}, riga {count}")
                    totals[name].append(parsed)
                else:
                    require(raw == display_value(value), f"Round-trip campo fallito: {name}, riga {count}")
        require(next(reader, None) is None, "Righe aggiunte nel CSV")
        for name, values in totals.items():
            require(strict_sum(values) == strict_sum(row[name] for row in expected if row[name] is not None),
                    f"Totale alterato: {name}")
    return count


def file_hash(path):
    digest = hashlib.md5()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
