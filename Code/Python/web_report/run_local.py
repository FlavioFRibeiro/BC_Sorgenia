"""Avvio locale semplice: python Code/Python/web_report/run_local.py."""
import os
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    directory = Path(__file__).resolve().parent
    interpreter = directory / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not interpreter.is_file():
        raise SystemExit("Creare prima l'ambiente .venv come descritto nel README del report web.")
    raise SystemExit(subprocess.call([str(interpreter), "-m", "streamlit", "run", "app.py",
                                     "--server.address", "127.0.0.1", *sys.argv[1:]], cwd=directory))
