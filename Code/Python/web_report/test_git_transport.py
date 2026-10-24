"""Regressione Windows -> Git -> checkout Linux, senza accesso di rete."""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from git_transport import git_blob, verify_git_payload, write_attributes


class GitTransportTests(unittest.TestCase):
    def test_public_repository_requires_explicit_authorization(self):
        from publish import validate_repository
        public = {"full_name": "FlavioFRibeiro/BC_Sorgenia", "private": False}
        with self.assertRaisesRegex(ValueError, "autorizzazione"):
            validate_repository(public)
        self.assertEqual(validate_repository(public, allow_public=True), public)
        private = dict(public, private=True)
        self.assertEqual(validate_repository(private), private)
        with self.assertRaisesRegex(ValueError, "inatteso"):
            validate_repository({"full_name": "other/repo", "private": False}, allow_public=True)

    def test_transport_preserves_manifest_payload_in_linux_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "windows"
            repo.mkdir()
            def git(*args):
                process = subprocess.run(["git", *args], cwd=repo, capture_output=True)
                self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
            git("init")
            git("config", "core.autocrlf", "true")
            files = {"Code/Python/functions.py": b"# Modulo condiviso\r\n",
                     "Code/Python/web_report/data/monthly_reference.csv": b'"anno";"importo"\r\n"2026";"12,34"\r\n',
                     "Code/Python/web_report/data/reference.json": b'{"value":12.34}\n'}
            for name, payload in files.items():
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            git("add", ".")
            monthly = "Code/Python/web_report/data/monthly_reference.csv"
            # Riproduce esattamente il difetto visto in Cloud.
            self.assertEqual(git_blob(repo, monthly), files[monthly].replace(b"\r\n", b"\n"))
            expected = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
            with self.assertRaisesRegex(ValueError, "alterato"):
                verify_git_payload(repo, expected)
            write_attributes(repo)
            git("add", "--renormalize", ".")
            git("add", ".gitattributes")
            self.assertTrue(verify_git_payload(repo, expected))
            git("-c", "user.name=Transport Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
                "commit", "-m", "Verify byte preserving snapshot")
            linux = root / "linux"
            process = subprocess.run(["git", "clone", "--config", "core.autocrlf=false", str(repo), str(linux)], capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
            for name, payload in files.items():
                self.assertEqual((linux / name).read_bytes(), payload)
            self.assertTrue(verify_git_payload(linux, expected, "HEAD"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
