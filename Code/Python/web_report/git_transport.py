"""Trasporto Git byte-preserving dei file sottoposti a controllo SHA-256."""
import hashlib
import subprocess

GIT_ATTRIBUTES = "Code/Python/functions.py -text\nCode/Python/web_report/data/** -text\n"


def write_attributes(checkout):
    # La regola -text impedisce ogni conversione CRLF/LF per il payload verificato.
    (checkout / ".gitattributes").write_bytes(GIT_ATTRIBUTES.encode("ascii"))


def git_blob(checkout, path, revision=""):
    # revision vuota => index (:path); HEAD => contenuto realmente committato.
    process = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=checkout,
                             capture_output=True)
    if process.returncode:
        raise ValueError(f"Payload Git non disponibile: {path}")
    return process.stdout


def verify_git_payload(checkout, expected, revision=""):
    for path, expected_sha in expected.items():
        actual = hashlib.sha256(git_blob(checkout, path, revision)).hexdigest()
        if actual != expected_sha:
            raise ValueError(f"Git ha alterato i byte del payload: {path}")
    return True
