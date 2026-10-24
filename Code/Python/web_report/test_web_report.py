"""Verifiche di regressione dati, filtri, download, integrita e interfaccia Streamlit."""
import csv
import io
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from data_model import (CORE_PATH, DETAIL_COLUMNS, DIMENSIONS, MONTH_COLUMNS, SNAPSHOT_FILES, WEB_DIR,
                        canonical_json, csv_bytes, filter_indices, finance, fmt, load_snapshot,
                        read_monthly, reconcile_reference, sha256, statistics, summary)


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_snapshot(WEB_DIR / "data")

    def test_full_baseline(self):
        rows = self.snapshot.rows
        stats = statistics(rows)
        self.assertEqual(len(rows), 216804)  # Riferimenti del case, mai filtri della logica.
        self.assertEqual(fmt(stats["pnl"]), "-540.640,69")
        self.assertEqual(fmt(stats["known_margin"]), "-14.214.839,86")
        self.assertEqual(fmt(stats["revenue_energy"]), "106.297.856,58")
        self.assertEqual(fmt(stats["revenue_service"]), "903.553,50")
        self.assertEqual(fmt(stats["cost_energy"]), "121.416.249,94")
        monthly = reconcile_reference(rows, read_monthly(WEB_DIR / "data" / "monthly_reference.csv"))
        self.assertEqual(len(monthly), 117)

    def test_every_dimension_and_combined_selection(self):
        catalog = self.snapshot.catalog
        for pos, field in enumerate(DIMENSIONS):
            selected = list(catalog)
            value = catalog[pos][0]
            selected[pos] = (value,)
            indices = filter_indices(self.snapshot.rows, selected)
            self.assertTrue(indices, field)
            from data_model import dimensions
            self.assertTrue(all(dimensions(self.snapshot.rows[i])[pos] == value for i in indices), field)
        selected = list(catalog)
        selected[2], selected[4], selected[5], selected[6] = ("ITALY",), ("Buy",), ("HEDGE",), ("ENERGY",)
        rows = [self.snapshot.rows[i] for i in filter_indices(self.snapshot.rows, selected)]
        result = summary(rows)
        self.assertEqual(result["statistics"]["n_rows"], len(rows))
        self.assertEqual(sum(x["n_rows"] for x in result["monthly"]), len(rows))
        self.assertEqual(result["statistics"]["revenue_energy"], 0)

    def test_empty_and_services(self):
        selected = list(self.snapshot.catalog)
        selected[2] = ()
        self.assertEqual(filter_indices(self.snapshot.rows, selected), [])
        selected = list(self.snapshot.catalog)
        selected[-1] = ("SERVICE_POWER",)
        rows = [self.snapshot.rows[i] for i in filter_indices(self.snapshot.rows, selected)]
        result = summary(rows)
        self.assertEqual(len(rows), 6)
        self.assertIsNone(result["statistics"]["pnl"])
        self.assertIsNone(result["statistics"]["volume_energy"])
        self.assertTrue(all(x["pnl_energy"] is None for x in result["monthly"]))
        self.assertEqual(fmt(result["statistics"]["revenue_service"]), "903.553,50")

    def test_hour25_negative_prices_and_incomplete_pnl(self):
        rows = self.snapshot.rows
        special = [row for row in rows if row["delivery_hour"] == 25]
        self.assertEqual(len(special), 25)
        self.assertTrue(all(x["ORA"] == "25" and x["HOUR"] == "25" for x in special))
        self.assertTrue(any(x["contract_price"] is not None and x["contract_price"] < 0 for x in rows))
        copied = [dict(rows[0])]
        copied[0].update(pnl=None, market_value_signed=None, pnl_calculable=False, row_problem=True)
        self.assertIsNone(summary(copied)["statistics"]["pnl"])
        self.assertIsNone(summary(copied)["monthly"][0]["pnl_energy"])
        self.assertEqual(summary(copied)["statistics"]["n_energy_incomplete"], 1)

    def test_export_all_rows_and_originals(self):
        rows = self.snapshot.rows[:245]
        payload = csv_bytes(rows, DETAIL_COLUMNS)
        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        actual = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(actual), 245)
        self.assertEqual(list(actual[0]), DETAIL_COLUMNS)
        for source, exported in zip(rows, actual):
            for field in finance.DEAL_COLUMNS:
                self.assertEqual(source[field], exported[field])
            if source["pnl"] is None:
                self.assertEqual(exported["pnl"], "NA")
            else:
                self.assertEqual(float(exported["pnl"].replace(",", ".")), source["pnl"])
        monthly = finance.monthly_summary(rows)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(csv_bytes(monthly, MONTH_COLUMNS).decode("utf-8-sig")), delimiter=";"))), len(monthly))

    def test_manifest_and_hash_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in (*SNAPSHOT_FILES, "manifest.json"):
                shutil.copyfile(WEB_DIR / "data" / name, target / name)
            manifest_path = target / "manifest.json"
            original = manifest_path.read_bytes()
            manifest = json.loads(original)
            manifest["detail_schema"] = ["wrong"]
            payload = {k: v for k, v in manifest.items() if k != "dataset_id"}
            import hashlib
            manifest["dataset_id"] = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
            manifest_path.write_text(canonical_json(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Schema"):
                load_snapshot(target)
            manifest_path.write_bytes(original)
            with (target / "deals.csv.gz").open("ab") as handle:
                handle.write(b"alterato")
            with self.assertRaisesRegex(ValueError, "alterato"):
                load_snapshot(target)

    def test_snapshot_reproducibility(self):
        from prepare_data import prepare
        root = WEB_DIR.parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data"
            prepare(root / "Output" / "python", target, root / "Output" / "R" / "report_it.md")
            for name in (*SNAPSHOT_FILES, "manifest.json"):
                self.assertEqual(sha256(target / name), sha256(WEB_DIR / "data" / name), name)


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from streamlit.testing.v1 import AppTest
        cls.app = AppTest.from_file(str(WEB_DIR / "app.py"), default_timeout=120).run()

    def check_no_exception(self):
        self.assertFalse(self.app.exception, [x.message for x in self.app.exception])

    def test_01_overview(self):
        self.check_no_exception()
        self.assertTrue(any("-540,6 k€" in x.value for x in self.app.markdown))
        self.assertTrue(any(x.value == "-14,2 M€" for x in self.app.metric))

    def test_02_services_filters_and_navigation(self):
        self.app.multiselect(key="filter_commodity").set_value(["SERVICE_POWER"]).run()
        self.check_no_exception()
        self.assertTrue(any("Non applicabile" in x.value for x in self.app.markdown))
        self.app.radio(key="navigation").set_value("Conto Economico").run()
        self.check_no_exception()
        self.assertEqual(self.app.multiselect(key="filter_commodity").value, ["SERVICE_POWER"])
        self.assertTrue(any(x.value == "903,6 k€" for x in self.app.metric))

    def test_03_empty_and_reset(self):
        self.app.multiselect(key="filter_market").set_value([]).run()
        self.check_no_exception()
        self.assertTrue(any("Nessun dato" in x.value for x in self.app.info))
        self.app.button[0].click().run()
        self.check_no_exception()
        self.assertEqual(set(self.app.multiselect(key="filter_market").value), {"FRANCE", "GERMANYDE", "ITALY"})

    def test_04_detail_pagination_and_hour25(self):
        self.app.radio(key="navigation").set_value("Dettaglio e controlli").run()
        self.check_no_exception()
        self.assertEqual(len(self.app.dataframe[1].value), 100)
        self.app.number_input(key="detail_page").set_value(2).run()
        self.check_no_exception()
        self.app.selectbox(key="detail_hour").set_value(25).run()
        self.check_no_exception()
        self.assertEqual(len(self.app.dataframe[1].value), 25)
        self.assertTrue(all(self.app.dataframe[1].value["ORA"] == "25"))
        self.app.button(key="prepare_download").click().run()
        self.check_no_exception()
        self.assertEqual(len(self.app.get("download_button")), 2)
        self.app.multiselect(key="filter_commodity").set_value(["SERVICE_POWER"]).run()
        self.check_no_exception()
        self.assertIsNone(self.app.selectbox(key="detail_hour").value)
        self.assertEqual(len(self.app.dataframe[1].value), 6)
        self.assertEqual(len(self.app.get("download_button")), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
