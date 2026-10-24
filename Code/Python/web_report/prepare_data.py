#!/usr/bin/env python
"""Crea uno snapshot deterministico dagli output Python validati."""
import argparse
import gzip
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from data_model import (CORE_PATH, DETAIL_COLUMNS, MONTH_COLUMNS, SNAPSHOT_FILES, WEB_DIR,
                        canonical_json, finance, read_detail, read_monthly, reconcile_reference,
                        report_money, sha256, statistics)


def check_report(path, expected):
    text = Path(path).read_text(encoding="utf-8-sig")
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r"\| ([^|]+) \| (-?[0-9.,]+) \|", line)
        if match:
            values[match[1].strip()] = match[2]
    match = re.search(r"P&L ENERGY complessivo: (-?[0-9.,]+) EUR", text)
    finance.require(match is not None, f"P&L non trovato nel report: {path}")
    values["P&L ENERGY complessivo"] = match[1]
    for label, value in expected.items():
        finance.require(values.get(label) == value, f"Valore diverso dal report {path.name}: {label}")


def prepare(source, target, r_report):
    source, target = Path(source), Path(target)
    inputs = {name: source / name for name in ("deals_enriched_pnl.csv", "monthly_summary.csv", "report_it.md", "validation.txt")}
    validation = inputs["validation.txt"].read_text(encoding="utf-8-sig")
    finance.require("VALIDAZIONE PYTHON COMPLETATA" in validation, "Validazione Python assente")
    for name in ("deals_enriched_pnl.csv", "monthly_summary.csv"):
        finance.require(f"{name} {finance.file_hash(inputs[name])}" in validation, f"CSV diverso dal verbale validato: {name}")
    original_hashes = {name: sha256(path) for name, path in inputs.items()}
    with inputs["deals_enriched_pnl.csv"].open(encoding="utf-8-sig", newline="") as handle:
        rows = read_detail(handle)
    monthly = reconcile_reference(rows, read_monthly(inputs["monthly_summary.csv"]))
    money = report_money(rows)
    check_report(inputs["report_it.md"], money)
    check_report(r_report, money)
    dates = [row["delivery_date"] for row in rows if row["delivery_date"]]
    reference = {"report_money": money, "statistics": statistics(rows), "monthly_groups": len(monthly)}
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="snapshot-", dir=target.parent) as tmp:
        staging = Path(tmp).resolve()
        finance.require(staging.is_relative_to(target.parent.resolve()), "Staging fuori dalla directory prevista")
        with inputs["deals_enriched_pnl.csv"].open("rb") as original, (staging / "deals.csv.gz").open("wb") as compressed:
            with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, compresslevel=9, mtime=0) as writer:
                shutil.copyfileobj(original, writer)
        shutil.copyfile(inputs["monthly_summary.csv"], staging / "monthly_reference.csv")
        (staging / "reference.json").write_text(canonical_json(reference), encoding="utf-8", newline="\n")
        manifest = {"schema_version": 1, "detail_schema": DETAIL_COLUMNS, "monthly_schema": MONTH_COLUMNS,
                    "core_sha256": sha256(CORE_PATH), "sources": original_hashes,
                    "r_report_sha256": sha256(r_report), "counts": {"rows": len(rows), "monthly_groups": len(monthly)},
                    "period": {"from": min(dates).isoformat(), "to": max(dates).isoformat()},
                    "units": {"currency": "EUR", "energy_volume": "MWh", "energy_price": "EUR/MWh", "assumed": True},
                    "files": {name: {"sha256": sha256(staging / name), "bytes": (staging / name).stat().st_size} for name in SNAPSHOT_FILES}}
        manifest["dataset_id"] = hashlib.sha256(canonical_json(manifest).encode()).hexdigest()
        (staging / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8", newline="\n")
        finance.require(original_hashes == {name: sha256(path) for name, path in inputs.items()}, "Input cambiati durante la preparazione")
        # Il manifesto viene sostituito per ultimo: un aggiornamento parziale fallisce i controlli hash.
        for name in (*SNAPSHOT_FILES, "manifest.json"):
            # Copiare nel target prima del replace eredita le ACL del progetto, anziche'
            # quelle private di TemporaryDirectory su Windows/Python 3.12.
            pending = target / (name + ".pending")
            shutil.copyfile(staging / name, pending)
            pending.replace(target / name)
    print(f"Snapshot validato: {len(rows)} righe, {len(monthly)} gruppi; ID {manifest['dataset_id'][:12]}")
    return manifest


if __name__ == "__main__":
    root = WEB_DIR.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=root / "Output" / "python")
    parser.add_argument("--output", type=Path, default=WEB_DIR / "data")
    parser.add_argument("--r-report", type=Path, default=root / "Output" / "R" / "report_it.md")
    args = parser.parse_args()
    prepare(args.source, args.output, args.r_report)
