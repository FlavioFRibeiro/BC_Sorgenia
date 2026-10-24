"""Adattatore del dataset validato. Formule e aggregatore provengono dalla pipeline."""
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
CORE_PATH = WEB_DIR.parent / "functions.py"
spec = importlib.util.spec_from_file_location("sorgenia_finance_core", CORE_PATH)
finance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finance)

DETAIL_COLUMNS = finance.DEAL_COLUMNS + [
    "deal_row_id", "delivery_date", "delivery_hour", "importo_value", "volume_value", "direction",
    "curve_index_expected", "curve_match_count", "curve_row_id", "DDATE", "HOUR", "curve_index",
    "market_price_raw", "market_price", "match_status", "pnl_applicable", "row_problem", "issue_codes",
    "contract_price", "pnl_calculable", "pnl", "market_value_signed", "pnl_status"]
MONTH_COLUMNS = ["anno", "mese", "counterparty", "purpose", "market", "n_rows", "importo_total",
                 "n_energy", "volume_energy", "market_value_signed_energy", "pnl_energy", "n_service_power",
                 "importo_service_power", "n_pnl_calculable", "n_problem_rows", "n_energy_not_calculable",
                 "n_pnl_not_applicable", "n_curve_unavailable", "pnl_energy_calculable_subtotal"]
BOOL_COLUMNS = {"pnl_applicable", "pnl_calculable", "row_problem"}
INT_COLUMNS = {"deal_row_id", "delivery_hour", "curve_match_count", "curve_row_id", "direction"}
DIMENSIONS = ("anno", "mese", "market", "counterparty", "purpose", "business_unit", "commodity")
COUNTRIES = {"ITALY": "Italia", "GERMANYDE": "Germania", "FRANCE": "Francia", "SPAIN": "Spagna"}
MONTH_NAMES = ("Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto",
               "Settembre", "Ottobre", "Novembre", "Dicembre")
SNAPSHOT_FILES = ("deals.csv.gz", "monthly_reference.csv", "reference.json")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def number(raw):
    if raw == "NA":
        return None
    try:
        value = float(raw.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"Numero analitico non valido: {raw}") from exc
    finance.require(math.isfinite(value), "Numero analitico non finito")
    return value


def read_detail(handle):
    reader = csv.DictReader(handle, delimiter=";", strict=True)
    finance.require(reader.fieldnames == DETAIL_COLUMNS, "Schema dettaglio non compatibile")
    rows = []
    interned = {}
    shared = {"business_unit", "DATA", "ORA", "proposer_description", "counterparty", "purpose", "market",
              "commodity", "DDATE", "HOUR", "curve_index", "curve_index_expected", "match_status", "pnl_status", "issue_codes"}
    for source in reader:
        finance.require(None not in source and all(v is not None for v in source.values()), "Riga dettaglio incompleta")
        row = dict(source)
        for field in finance.DETAIL_NUMERIC:
            value = number(source[field])
            if field in INT_COLUMNS and value is not None:
                finance.require(value.is_integer(), f"Intero non valido: {field}")
                value = int(value)
            row[field] = value
        for field in BOOL_COLUMNS:
            finance.require(source[field] in ("TRUE", "FALSE"), f"Booleano non valido: {field}")
            row[field] = source[field] == "TRUE"
        row["delivery_date"] = finance.parse_date(source["delivery_date"]) if source["delivery_date"] != "NA" else None
        finance.require(source["delivery_date"] == "NA" or row["delivery_date"] is not None, "Data analitica non valida")
        for field in ("curve_index_expected", "DDATE", "HOUR", "curve_index", "market_price_raw"):
            if row[field] == "NA":
                row[field] = None
        for field in shared:
            if row[field] is not None:
                row[field] = interned.setdefault(row[field], row[field])
        finance.require(row["delivery_date"] == finance.parse_date(row["DATA"]), "Data originale e analitica incoerenti")
        finance.require(row["delivery_hour"] == finance.parse_hour(row["ORA"]), "Ora originale e analitica incoerenti")
        if not row["pnl_applicable"]:
            finance.require(row["pnl"] is None and row["market_value_signed"] is None, "P&L presente per commodity non applicabile")
        finance.require(row["pnl_calculable"] == (row["pnl"] is not None), "Stato P&L incoerente")
        rows.append(row)
    finance.require(bool(rows), "Dettaglio vuoto")
    finance.require(len({r["deal_row_id"] for r in rows}) == len(rows), "ID riga tecnico duplicato")
    return rows


def read_monthly(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", strict=True)
        finance.require(reader.fieldnames == MONTH_COLUMNS, "Schema mensile non compatibile")
        return [{k: (v if k in ("counterparty", "purpose", "market") else number(v)) for k, v in row.items()} for row in reader]


def reconcile_reference(rows, monthly):
    actual = finance.monthly_summary(rows)
    finance.require(len(actual) == len(monthly), "Numero gruppi diverso dal mensile validato")
    for observed, expected in zip(actual, monthly):
        for field in MONTH_COLUMNS:
            ok = observed[field] == expected[field] if field in ("counterparty", "purpose", "market") else finance.near(observed[field], expected[field])
            finance.require(ok, f"Riconciliazione snapshot/mensile fallita: {field}")
    finance.reconcile_monthly(rows, actual)
    return actual


def dimensions(row):
    dt = row["delivery_date"]
    return (dt.year if dt else None, dt.month if dt else None, row["market"], row["counterparty"],
            row["purpose"], row["business_unit"], row["commodity"])


def catalog_for(rows):
    values = [set() for _ in DIMENSIONS]
    for row in rows:
        for catalog, value in zip(values, dimensions(row)):
            catalog.add(value)
    return tuple(tuple(sorted(catalog, key=lambda x: (x is None, x))) for catalog in values)


def filter_indices(rows, selections):
    finance.require(len(selections) == len(DIMENSIONS), "Schema filtri non valido")
    selected = tuple(set(values) for values in selections)
    if any(not x for x in selected):
        return []
    return [i for i, row in enumerate(rows) if all(value in choices for value, choices in zip(dimensions(row), selected))]


def statistics(rows):
    energy = [row for row in rows if row["commodity"] == "ENERGY"]
    result = finance.contractual_statement(rows)
    result.update(n_rows=len(rows), n_energy=len(energy), n_service=sum(x["commodity"] == "SERVICE_POWER" for x in rows),
                  n_calculable=sum(x["pnl_calculable"] for x in rows), n_problem=sum(x["row_problem"] for x in rows),
                  n_not_applicable=sum(not x["pnl_applicable"] for x in rows),
                  n_energy_incomplete=sum(not x["pnl_calculable"] for x in energy),
                  pnl=finance.strict_sum(x["pnl"] for x in energy),
                  volume_energy=finance.strict_sum(x["volume_value"] if x["volume_value"] is not None and x["volume_value"] > 0 else None for x in energy))
    return result


def grouped_pnl(rows, field):
    groups = defaultdict(list)
    for row in rows:
        if row["commodity"] == "ENERGY":
            groups[row[field]].append(row["pnl"])
    return [(key, finance.strict_sum(values)) for key, values in sorted(groups.items())]


def summary(rows):
    return {"statistics": statistics(rows), "monthly": finance.monthly_summary(rows),
            "markets": grouped_pnl(rows, "market"), "counterparties": grouped_pnl(rows, "counterparty")}


def fmt(value, digits=2):
    if value is None:
        return "Non applicabile"
    if abs(value) < 0.5 * 10 ** -digits:
        value = 0
    return f"{value:,.{digits}f}".translate(str.maketrans(",.", ".,"))


def report_money(rows):
    stats = statistics(rows)
    return {"Ricavi da vendita di energia": fmt(stats["revenue_energy"]),
            "Ricavi da servizi": fmt(stats["revenue_service"]),
            "Totale ricavi": fmt(stats["revenue_energy"] + stats["revenue_service"]),
            "Costi di acquisto di energia": fmt(stats["cost_energy"]),
            "Margine di contribuzione (dataset)": fmt(stats["known_margin"]),
            "P&L ENERGY complessivo": fmt(stats["pnl"]),
            **{market: fmt(value) for market, value in grouped_pnl(rows, "market")}}


def csv_bytes(rows, columns):
    """Stesse convenzioni CSV della pipeline; mai limitato alla pagina mostrata."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n", quoting=csv.QUOTE_ALL)
    writer.writerow(columns)
    writer.writerows([finance.display_value(row.get(name)) for name in columns] for row in rows)
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


@dataclass(frozen=True)
class Snapshot:
    manifest: dict
    rows: tuple
    catalog: tuple


def snapshot_signature(directory):
    directory = Path(directory)
    return (sha256(directory / "manifest.json"), tuple((name, (directory / name).stat().st_size,
            (directory / name).stat().st_mtime_ns) for name in SNAPSHOT_FILES))


def load_snapshot(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    finance.require(manifest.get("schema_version") == 1, "Versione snapshot non compatibile")
    identity = manifest.get("dataset_id")
    payload = {k: v for k, v in manifest.items() if k != "dataset_id"}
    finance.require(hashlib.sha256(canonical_json(payload).encode()).hexdigest() == identity, "Identita manifesto non valida")
    finance.require(manifest["detail_schema"] == DETAIL_COLUMNS and manifest["monthly_schema"] == MONTH_COLUMNS,
                    "Schema manifesto non compatibile")
    finance.require(set(manifest["files"]) == set(SNAPSHOT_FILES), "Elenco file snapshot non valido")
    finance.require(manifest["core_sha256"] == sha256(CORE_PATH), "Modulo finanziario diverso: rigenerare lo snapshot")
    for name in SNAPSHOT_FILES:
        metadata = manifest["files"][name]
        finance.require(sha256(directory / name) == metadata["sha256"] and (directory / name).stat().st_size == metadata["bytes"],
                        f"Snapshot alterato o incompleto: {name}")
    with gzip.open(directory / "deals.csv.gz", "rt", encoding="utf-8-sig", newline="") as handle:
        rows = read_detail(handle)
    reference = json.loads((directory / "reference.json").read_text(encoding="utf-8"))
    finance.require(len(rows) == manifest["counts"]["rows"], "Conteggio righe snapshot non valido")
    finance.require(report_money(rows) == reference["report_money"], "Indicatori diversi dal report validato")
    return Snapshot(manifest, tuple(rows), catalog_for(rows))
