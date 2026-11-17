from __future__ import annotations
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/biomedical-publication-suite/scripts'
sys.path.insert(0, str(SCRIPTS))
import init_publication_package as init

class PackageWorkflows(unittest.TestCase):
    def run_cli(self, name, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str,args)], capture_output=True, text=True)

    def test_validate_version_named_installation(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            installed = Path(temporary_root) / "1.2.1"
            shutil.copytree(ROOT, installed, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            command = [sys.executable, str(installed / "scripts" / "validate_suite.py")]
            valid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

            manifest_path = installed / ".codex-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["name"] = "different-skill"
            manifest_path.write_text(json.dumps(manifest))
            invalid = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("Plugin name differs from the packaged skill name", json.loads(invalid.stdout)["errors"])

    def test_lean_scaffold_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            a=self.run_cli('init_publication_package.py','--repo-root',t);self.assertEqual(0,a.returncode,a.stderr)
            p=Path(t)/'manuscript/manuscript.md';p.write_text('User draft')
            self.assertEqual(0,self.run_cli('init_publication_package.py','--repo-root',t).returncode);self.assertEqual('User draft',p.read_text())

    def test_evidence_profile_does_not_create_manuscript(self):
        with tempfile.TemporaryDirectory() as t:
            a=self.run_cli('init_publication_package.py','--repo-root',t,'--profile','evidence');self.assertEqual(0,a.returncode,a.stderr)
            p=Path(t)/'manuscript';self.assertFalse((p/'manuscript.md').exists());self.assertTrue((p/'literature_register.csv').exists())

    def test_overwrite_has_recoverable_backup(self):
        with tempfile.TemporaryDirectory() as t:
            self.run_cli('init_publication_package.py','--repo-root',t)
            p=Path(t)/'manuscript';(p/'manuscript.md').write_text('Precious original')
            a=self.run_cli('init_publication_package.py','--repo-root',t,'--overwrite');self.assertEqual(0,a.returncode,a.stderr)
            self.assertEqual('Precious original',next((p/'.scaffold-backups').glob('*/manuscript.md')).read_text())

    def test_scaffold_rejects_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(2,self.run_cli('init_publication_package.py','--repo-root',t,'--package-dir','../escape').returncode)
            p=Path(t)/'manuscript';p.mkdir();outside=Path(t)/'original';outside.write_text('unchanged');(p/'manuscript.md').symlink_to(outside)
            self.assertEqual(2,self.run_cli('init_publication_package.py','--repo-root',t,'--overwrite').returncode);self.assertEqual('unchanged',outside.read_text())

    def test_additive_headers_pass_legacy_qc_scaffold(self):
        with tempfile.TemporaryDirectory() as t:
            self.run_cli('init_publication_package.py','--repo-root',t,'--profile','submission','--include-literature')
            a=self.run_cli('publication_qc.py','--repo-root',t,'--stage','scaffold','--no-write-report')
            self.assertEqual(0,a.returncode,a.stdout+a.stderr)

if __name__ == '__main__': unittest.main()
