"""Confronto integrale R/Python: report esatto, CSV verificati campo per campo."""
import argparse
import csv
import difflib
import math
from collections import Counter
from itertools import zip_longest
from pathlib import Path

from functions import DETAIL_NUMERIC, file_hash, require
from report import md_table


def compare_csv(r_path, python_path, detail):
    counts = Counter()
    differences = Counter()
    max_absolute = Counter()
    max_relative = Counter()
    exact_rows = 0
    with Path(r_path).open(encoding="utf-8-sig", newline="") as r_file, Path(python_path).open(encoding="utf-8-sig", newline="") as py_file:
        r_reader = csv.DictReader(r_file, delimiter=";", strict=True)
        py_reader = csv.DictReader(py_file, delimiter=";", strict=True)
        require(r_reader.fieldnames == py_reader.fieldnames, "Schemi R/Python diversi")
        columns = r_reader.fieldnames
        numeric = DETAIL_NUMERIC if detail else set(columns) - {"counterparty", "purpose", "market"}
        rows = 0
        for rows, (r_row, py_row) in enumerate(zip_longest(r_reader, py_reader), 1):
            require(r_row is not None and py_row is not None, f"Numero righe R/Python diverso: {r_path.name}")
            exact = True
            for name in columns:
                r_text, py_text = r_row[name], py_row[name]
                counts[name] += 1
                if name not in numeric or r_text == "NA" or py_text == "NA":
                    require(r_text == py_text, f"Campo testuale/NA diverso: {r_path.name}, riga {rows}, {name}")
                    continue
                r_value, py_value = float(r_text.replace(",", ".")), float(py_text.replace(",", "."))
                if r_value != py_value:
                    exact = False
                    differences[name] += 1
                    absolute = abs(r_value - py_value)
                    relative = absolute / max(abs(r_value), abs(py_value), 1e-300)
                    max_absolute[name] = max(max_absolute[name], absolute)
                    max_relative[name] = max(max_relative[name], relative)
                    require(math.isclose(r_value, py_value, rel_tol=1e-12, abs_tol=1e-12),
                            f"Differenza numerica oltre tolleranza: {r_path.name}, riga {rows}, {name}: {r_text} / {py_text}")
            exact_rows += int(exact)
    return dict(file=r_path.name, rows=rows, columns=columns, counts=counts, differences=differences,
                max_absolute=max_absolute, max_relative=max_relative, exact_rows=exact_rows,
                bytes_equal=file_hash(r_path) == file_hash(python_path))


def normalized_report(text):
    # Si neutralizzano soltanto linguaggio e link delle note: nessun numero o risultato.
    return (text.replace("Elaborazione in Python", "Elaborazione in IMPLEMENTAZIONE")
            .replace("Elaborazione in R", "Elaborazione in IMPLEMENTAZIONE")
            .replace("NOTE_TECNICHE_PYTHON.md", "NOTE_TECNICHE_IMPLEMENTAZIONE.md")
            .replace("NOTE_TECNICHE_R.md", "NOTE_TECNICHE_IMPLEMENTAZIONE.md"))


def compare_reports(r_path, python_path):
    r_text = normalized_report(Path(r_path).read_text(encoding="utf-8-sig"))
    py_text = normalized_report(Path(python_path).read_text(encoding="utf-8-sig"))
    diff = list(difflib.unified_diff(r_text.splitlines(), py_text.splitlines(), fromfile="R", tofile="Python"))
    require(not diff, "Report R/Python diversi:\n" + "\n".join(diff[:30]))


def compare_outputs(r_dir, python_dir):
    r_dir, python_dir = Path(r_dir), Path(python_dir)
    results = []
    for name, detail in (("deals_enriched_pnl.csv", True), ("monthly_summary.csv", False)):
        require((r_dir / name).is_file(), f"Riferimento R assente: {r_dir / name}; eseguire prima la pipeline R")
        results.append(compare_csv(r_dir / name, python_dir / name, detail))
    compare_reports(r_dir / "report_it.md", python_dir / "report_it.md")
    lines = ["# Confronto R / Python", "", "## Report: coincidenza esatta del 100%", "",
             "Il contenuto dei due report coincide integralmente dopo aver neutralizzato soltanto il nome del linguaggio e il link delle rispettive note tecniche. Nessun numero, importo o risultato viene modificato per il confronto: non si applica alcuna tolleranza al report.", "",
             "## CSV: confronto integrale", "",
             "Si controllano schema, ordine, ogni riga, ogni campo originale, chiavi, stati, NA e numeri. Le differenze non esatte dei double sono contate esplicitamente. La tolleranza numerica tra linguaggi e' relativa 1e-12 e assoluta 1e-12; la rilettura del CSV Python usa invece uguaglianza numerica esatta.", ""]
    for result in results:
        n_diff = sum(result["differences"].values())
        lines += [f"### {result['file']}", "", f"Righe: {result['rows']}; colonne: {len(result['columns'])}; righe numericamente esatte: {result['exact_rows']}; celle numeriche non esatte ma entro tolleranza: {n_diff}.", "",
                  f"File identici anche byte per byte: {'SI' if result['bytes_equal'] else 'NO'}.", "",
                  *md_table(["colonna", "celle verificate", "differenze double", "massimo scarto assoluto", "massimo scarto relativo"],
                            [(name, result["counts"][name], result["differences"][name],
                              format(result["max_absolute"][name], ".17g"), format(result["max_relative"][name], ".17g"))
                             for name in result["columns"]]), ""]
    lines += ["## Interpretazione", "",
              "Ogni implementazione e' deterministica nel proprio ambiente. La conversione delle stringhe decimali in double puo' differire nell'ultimo bit tra R e Python. R usa inoltre un accumulatore esteso per sum(), mentre Python usa math.fsum(): conversione e somma possono produrre differenze nelle ultime cifre binarie del dettaglio e degli aggregati. L'uguaglianza del report e' controllata esattamente alla precisione pubblicata, senza forzare o copiare i risultati R nella pipeline Python.", "",
              "## MD5 dei file confrontati", ""]
    lines += md_table(["file", "MD5 R", "MD5 Python"],
                      [(name, file_hash(r_dir / name), file_hash(python_dir / name))
                       for name in ("deals_enriched_pnl.csv", "monthly_summary.csv", "report_it.md")])
    (python_dir / "comparison_R_python.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Confronto R/Python: report esatto al 100%; CSV verificati integralmente", flush=True)
    return results


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("r_dir", nargs="?", type=Path, default=root / "Output" / "R")
    parser.add_argument("python_dir", nargs="?", type=Path, default=root / "Output" / "python")
    args = parser.parse_args()
    compare_outputs(args.r_dir, args.python_dir)
