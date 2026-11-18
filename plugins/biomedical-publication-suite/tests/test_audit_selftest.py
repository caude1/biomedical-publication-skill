"""Run the senior-investigator-audit helper scripts' own regression checks."""
import subprocess
import sys
import unittest
from pathlib import Path

SELFTEST = Path(__file__).resolve().parents[1] / "skills/senior-investigator-audit/scripts/selftest.py"


class AuditSelftest(unittest.TestCase):
    def test_audit_helpers_pass_their_selftest(self):
        result = subprocess.run([sys.executable, str(SELFTEST)], capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-4000:])
        self.assertIn("checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
