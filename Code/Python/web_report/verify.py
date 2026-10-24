#!/usr/bin/env python
"""Esegue e registra i test senza dipendere dalla redirezione stderr della shell."""
import io
import json
import platform
import sys
import time
import unittest
from pathlib import Path

from data_model import CORE_PATH, WEB_DIR, sha256


if __name__ == "__main__":
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(WEB_DIR), pattern="test_web_report.py")
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    target = WEB_DIR / "qa"
    target.mkdir(exist_ok=True)
    (target / "tests.txt").write_text(log.getvalue(), encoding="utf-8")
    metadata = {"passed": result.wasSuccessful(), "tests": result.testsRun, "errors": len(result.errors),
                "failures": len(result.failures), "seconds": round(time.perf_counter() - start, 3),
                "python": platform.python_version(), "snapshot_sha256": sha256(WEB_DIR / "data" / "manifest.json"),
                "core_sha256": sha256(CORE_PATH), "source_sha256": {p.name: sha256(p) for p in WEB_DIR.glob("*.py")}}
    (target / "validation.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(log.getvalue())
    sys.exit(0 if result.wasSuccessful() else 1)
