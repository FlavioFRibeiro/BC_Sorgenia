#!/usr/bin/env python
"""Pubblica il codebase nel repository autorizzato, senza salvare credenziali."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from data_model import WEB_DIR, finance, load_snapshot, sha256
from git_transport import git_blob, verify_git_payload, write_attributes

REPOSITORY = "FlavioFRibeiro/BC_Sorgenia"
REMOTE = f"https://github.com/{REPOSITORY}.git"
ROOT = WEB_DIR.parents[2]


def run_git(arguments, cwd=None, capture=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    process = subprocess.run(["git", "-c", "credential.interactive=never", *arguments], cwd=cwd,
                             env=env, capture_output=True, text=True, encoding="utf-8")
    # Gli errori Git non includono credenziali: il remote contiene soltanto owner/repo.
    if process.returncode:
        raise RuntimeError(process.stderr.strip())
    return process.stdout.strip() if capture else None


def validate_repository(metadata, allow_public=False):
    finance.require(metadata["full_name"].lower() == REPOSITORY.lower(), "Repository inatteso")
    finance.require(metadata["private"] is True or allow_public,
                    "Pubblicazione bloccata: repository pubblico; serve l'autorizzazione esplicita --allow-public")
    return metadata


def repository_metadata(allow_public=False):
    # Flusso standard Git Credential Manager: token solo in memoria, mai stampato/salvato.
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    result = subprocess.run(["git", "-c", "credential.interactive=never", "credential", "fill"],
                            input=f"protocol=https\nhost=github.com\npath={REPOSITORY}.git\n\n",
                            text=True, capture_output=True, env=env)
    finance.require(result.returncode == 0, "Accesso GitHub non disponibile nel gestore credenziali")
    credential = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    finance.require(bool(credential.get("password")), "Credenziale GitHub non disponibile")
    request = urllib.request.Request(f"https://api.github.com/repos/{REPOSITORY}",
                                    headers={"Authorization": "Bearer " + credential["password"],
                                             "Accept": "application/vnd.github+json", "User-Agent": "Sorgenia-Business-Case"})
    with urllib.request.urlopen(request, timeout=30) as response:
        metadata = json.load(response)
    return validate_repository(metadata, allow_public)


def selected_files():
    files = []
    for name in ("README.md", "DEAL.csv", "CurveOrariePower.csv"):
        files.append(ROOT / name)
    files += list((ROOT / "Code" / "R").glob("*.R"))
    files += list((ROOT / "Code" / "Python").glob("*.py"))
    files += list((ROOT / "Code").glob("NOTE_TECNICHE*.md"))
    for directory in (ROOT / "Output" / "R", ROOT / "Output" / "python"):
        files += list(directory.glob("*.md")) + list(directory.glob("*.txt"))
        files.append(directory / "monthly_summary.csv")
    for path in WEB_DIR.iterdir():
        if path.is_file() and (path.suffix in (".py", ".md", ".txt", ".lock") or path.name == ".gitignore"):
            files.append(path)
    files += list((WEB_DIR / ".streamlit").glob("*.toml"))
    files = [path for path in files if path.name != "secrets.toml"]
    files += [WEB_DIR / "data" / name for name in ("manifest.json", "deals.csv.gz", "monthly_reference.csv", "reference.json")]
    if (WEB_DIR / "qa").is_dir():
        files += [path for path in (WEB_DIR / "qa").iterdir() if path.suffix in (".json", ".txt", ".png", ".md")
                  and path.name != "repository_publication.json"]
    return sorted(set(files))


def publish(push=False, allow_public=False):
    metadata = repository_metadata(allow_public)
    visibility = "privata" if metadata["private"] else "pubblica (autorizzata)"
    print(f"Repository verificato: {metadata['full_name']}; visibilita {visibility}")
    if not push:
        return metadata
    load_snapshot(WEB_DIR / "data")
    base = WEB_DIR / ".publish"
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-", dir=base) as tmp:
        checkout = Path(tmp).resolve()
        finance.require(checkout.is_relative_to(base.resolve()), "Checkout fuori dalla cartella prevista")
        run_git(["clone", REMOTE, str(checkout)])
        branch = metadata["default_branch"]
        head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=checkout, capture_output=True)
        if head.returncode:
            run_git(["checkout", "-b", branch], cwd=checkout)
        else:
            run_git(["checkout", branch], cwd=checkout)
        reference_path = "Code/Python/web_report/data/monthly_reference.csv"
        if head.returncode == 0:
            old_reference = git_blob(checkout, reference_path, "HEAD")
            original_reference = (WEB_DIR / "data" / "monthly_reference.csv").read_bytes()
            if old_reference != original_reference and old_reference == original_reference.replace(b"\r\n", b"\n"):
                print("Diagnosi confermata: Git aveva convertito monthly_reference.csv da CRLF a LF.", flush=True)
        for path in selected_files():
            relative = path.relative_to(ROOT)
            target = checkout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        # Configurazione Cloud alla radice del repository; ambiente locale rimane in web_report.
        (checkout / ".streamlit").mkdir(exist_ok=True)
        shutil.copyfile(WEB_DIR / ".streamlit" / "config.toml", checkout / ".streamlit" / "config.toml")
        (checkout / ".python-version").write_text("3.12\n", encoding="ascii")
        (checkout / ".gitignore").write_text("**/__pycache__/\n**/.venv/\n**/.runtime/\n**/.cache/\n**/.publish/\n**/secrets.toml\nOutput/**/deals_enriched_pnl.csv\n", encoding="ascii")
        write_attributes(checkout)
        run_git(["add", "--", "README.md", "DEAL.csv", "CurveOrariePower.csv", "Code", "Output", ".streamlit", ".python-version", ".gitignore", ".gitattributes"], cwd=checkout)
        run_git(["add", "--renormalize", "--", "Code/Python/functions.py", "Code/Python/web_report/data"], cwd=checkout)
        expected_payload = {"Code/Python/functions.py": sha256(ROOT / "Code" / "Python" / "functions.py"),
                            **{f"Code/Python/web_report/data/{name}": sha256(WEB_DIR / "data" / name)
                               for name in ("manifest.json", "deals.csv.gz", "monthly_reference.csv", "reference.json")}}
        verify_git_payload(checkout, expected_payload)
        changed = run_git(["diff", "--cached", "--name-only"], cwd=checkout, capture=True)
        if changed:
            run_git(["-c", "user.name=Flavio F Ribeiro", "-c", "user.email=flarib@msn.com", "-c", "commit.gpgsign=false",
                     "commit", "-m", "Preserve snapshot bytes across Windows and Linux deployments"], cwd=checkout)
            run_git(["push", "origin", branch], cwd=checkout)
        verify_git_payload(checkout, expected_payload, "HEAD")
        commit = run_git(["rev-parse", "HEAD"], cwd=checkout, capture=True)
    result = {"repository": metadata["html_url"], "private": metadata["private"], "branch": branch, "commit": commit,
              "entrypoint": "Code/Python/web_report/app.py", "python": "3.12", "viewer_email": "flarib@msn.com",
              "streamlit_url": "https://bc-sorgenia.streamlit.app/",
              "streamlit_deployment_verified": False, "access_policy_verified": False}
    (WEB_DIR / "qa").mkdir(exist_ok=True)
    (WEB_DIR / "qa" / "repository_publication.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Codebase pubblicato. Commit: {commit}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="Pubblica il codebase verificato")
    parser.add_argument("--allow-public", action="store_true", help="Consente il repository pubblico su autorizzazione esplicita del proprietario")
    args = parser.parse_args()
    publish(args.push, args.allow_public)
