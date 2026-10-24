#!/usr/bin/env python
"""Avvio: python Code/Python/run.py [input_dir] [output_dir]."""
import argparse
import platform
import sys
from pathlib import Path

from compare import compare_outputs
from functions import (CURVE_COLUMNS, DEAL_COLUMNS, calculate_pnl, curves_to_long,
                       enrich_deals, export_csv, file_hash, monthly_summary,
                       prepare_deals, read_source, reconcile_monthly, require,
                       sort_deals, verify_csv)
from report import write_diagnostics, write_report
from tests import run_tests


def main():
    code_dir = Path(__file__).resolve().parent
    root = code_dir.parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", nargs="?", type=Path, default=root)
    parser.add_argument("output_dir", nargs="?", type=Path, default=root / "Output" / "python")
    parser.add_argument("--reference-dir", type=Path, default=root / "Output" / "R")
    parser.add_argument("--skip-comparison", action="store_true", help="Esecuzione indipendente senza riferimenti R")
    parser.add_argument("--check-reproducibility", action="store_true", help="Confronta i nuovi output con la corsa precedente, tramite MD5")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reproducible_files = ["deals_enriched_pnl.csv", "monthly_summary.csv", "report_it.md", "diagnostics.md"]
    previous_hash = {}
    if args.check_reproducibility:
        require(all((args.output_dir / name).is_file() for name in reproducible_files),
                "Per --check-reproducibility eseguire prima una corsa normale sugli stessi input")
        previous_hash = {name: file_hash(args.output_dir / name) for name in reproducible_files}
    run_tests()
    inputs = [args.input_dir / name for name in ("DEAL.csv", "CurveOrariePower.csv")]
    before_hash = [file_hash(path) for path in inputs]
    raw_deals = read_source(inputs[0], DEAL_COLUMNS)
    raw_curves = read_source(inputs[1], CURVE_COLUMNS)
    print(f"Importati {len(raw_deals)} deals e {len(raw_curves)} righe curva", flush=True)
    prepared = prepare_deals(raw_deals)
    curves = curves_to_long(raw_curves)
    result = calculate_pnl(enrich_deals(prepared, curves))
    del prepared
    sort_deals(result)
    monthly = monthly_summary(result)
    reconcile_monthly(result, monthly)
    print(f"Join, P&L e riconciliazione: OK; {len(monthly)} gruppi mensili", flush=True)
    output_names = ["deals_enriched_pnl.csv", "monthly_summary.csv"]
    for table, name in zip((result, monthly), output_names):
        path = args.output_dir / name
        require(path.resolve() not in [x.resolve() for x in inputs], "Output sovrapposto agli input")
        export_csv(table, path)
        verify_csv(table, path)
    write_diagnostics(raw_deals, raw_curves, result, curves, args.output_dir / "diagnostics.md")
    write_report(result, monthly, args.output_dir / "report_it.md")
    require(before_hash == [file_hash(path) for path in inputs], "Originali modificati")
    if not args.skip_comparison:
        compare_outputs(args.reference_dir, args.output_dir)
    if args.check_reproducibility:
        current_hash = {name: file_hash(args.output_dir / name) for name in reproducible_files}
        require(previous_hash == current_hash, "Output diversi dalla corsa precedente: verificare input, codice e ambiente")
        lines = ["# Riproducibilita Python", "", "Due esecuzioni complete sugli stessi input hanno prodotto output identici byte per byte.", "",
                 "| File | MD5 corsa precedente | MD5 nuova corsa |", "| --- | --- | --- |",
                 *(f"| {name} | {previous_hash[name]} | {current_hash[name]} |" for name in reproducible_files)]
        (args.output_dir / "determinism.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Riproducibilita Python: output identici byte per byte", flush=True)
    log = ["VALIDAZIONE PYTHON COMPLETATA", "Test sintetici mirati: OK", "Chiavi curve univoche: OK",
           "Left join conservativo (righe, originali, IMPORTO, VOLUME): OK",
           "Identita formule P&L: OK", "Riconciliazione indipendente con Decimal: OK",
           "Rilettura esatta dei due CSV Python (tutte le celle e totali): OK", "Originali invariati (MD5): OK",
           "Confronto R/Python: " + ("non richiesto (--skip-comparison)" if args.skip_comparison else "report esatto, CSV entro tolleranza: OK"), "",
           "Riproducibilita tra due corse: " + ("MD5 identici: OK" if args.check_reproducibility else "non richiesta in questa corsa"), "",
           f"Righe deal: {len(result)}", f"Righe curve larghe/lunghe: {len(raw_curves)} {len(curves)}",
           f"Gruppi mensili: {len(monthly)}", f"Righe con problemi: {sum(x['row_problem'] for x in result)}",
           f"Righe ENERGY con P&L: {sum(x['pnl_calculable'] for x in result)}",
           f"Righe non applicabili: {sum(not x['pnl_applicable'] for x in result)}", "", "MD5 input:",
           *(f"{path.name} {digest}" for path, digest in zip(inputs, before_hash)), "", "MD5 CSV esportati:",
           *(f"{name} {file_hash(args.output_dir / name)}" for name in output_names), "", "MD5 codice Python:",
           *(f"{path.name} {file_hash(path)}" for path in sorted(code_dir.glob("*.py"))), "",
           f"Python: {sys.version}", f"Piattaforma: {platform.platform()}", "Dipendenze: solo libreria standard"]
    (args.output_dir / "validation.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"Completato: {len(result)} deal; {len(monthly)} gruppi mensili. Output: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
