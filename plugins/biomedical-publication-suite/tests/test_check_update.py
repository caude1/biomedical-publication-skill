"""Offline tests for the weekly update check."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/biomedical-publication-suite/scripts/check_update.py"
spec = importlib.util.spec_from_file_location("check_update", SCRIPT)
cu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cu)

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
WEEK = timedelta(days=7)


class Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"BPS_UPDATE_STATE_DIR": self.tmp.name}, clear=False)
        self.env.start()
        os.environ.pop("BPS_UPDATE_CHECK", None)
        os.environ.pop("BPS_UPDATE_INTERVAL_DAYS", None)
        self.state_file = Path(self.tmp.name) / "update-check.json"

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_check(self, *, latest=None, error=None, installed="1.4.0", args=()):
        out = io.StringIO()
        side = error if error else (lambda *a, **k: Reply(f"{latest}\n".encode()))
        with patch.object(cu.urllib.request, "urlopen", side_effect=side) as opened, \
                patch.object(cu, "installed_version", return_value=installed), \
                contextlib.redirect_stdout(out):
            code = cu.main(list(args))
        return code, out.getvalue(), opened

    def test_version_file_matches_manifest(self):
        manifest = json.loads((SCRIPT.parents[3] / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(cu.installed_version(), manifest["version"])

    def test_first_run_checks_and_records(self):
        code, out, opened = self.run_check(latest="1.4.0")
        self.assertEqual(code, 0)
        self.assertIn("Up to date", out)
        self.assertEqual(opened.call_count, 1)
        state = json.loads(self.state_file.read_text())
        self.assertEqual(state["latest"], "1.4.0")
        self.assertIn("last_checked", state)

    def test_newer_version_is_announced_with_commands(self):
        _, out, _ = self.run_check(latest="1.10.0", installed="1.9.2")
        self.assertIn("UPDATE AVAILABLE: version 1.10.0", out)
        self.assertIn(cu.RELEASES_URL, out)

    def test_not_due_within_interval_makes_no_request(self):
        self.run_check(latest="1.4.0")
        _, out, opened = self.run_check(latest="9.9.9")
        self.assertIn("not due", out)
        self.assertEqual(opened.call_count, 0)

    def test_due_again_after_interval(self):
        old = (datetime.now(timezone.utc) - WEEK - timedelta(hours=1)).isoformat(timespec="seconds")
        self.state_file.write_text(json.dumps({"last_checked": old}))
        _, out, opened = self.run_check(latest="1.5.0")
        self.assertEqual(opened.call_count, 1)
        self.assertIn("UPDATE AVAILABLE", out)

    def test_force_ignores_interval(self):
        self.run_check(latest="1.4.0")
        _, _, opened = self.run_check(latest="1.4.0", args=["--force"])
        self.assertEqual(opened.call_count, 1)

    def test_network_failure_is_quiet_and_retried_after_a_day(self):
        code, out, _ = self.run_check(error=urllib.error.URLError("offline"))
        self.assertEqual(code, 0)
        self.assertIn("could not reach GitHub", out)
        state = json.loads(self.state_file.read_text())
        self.assertNotIn("last_checked", state)
        self.assertTrue(cu.is_due({"last_failed_attempt": (NOW - timedelta(days=2)).isoformat()}, NOW, WEEK))
        self.assertFalse(cu.is_due({"last_failed_attempt": (NOW - timedelta(hours=2)).isoformat()}, NOW, WEEK))
        _, out, _ = self.run_check(latest="1.4.0")
        self.assertIn("retrying after a failed attempt", out)

    def test_unexpected_reply_is_treated_as_failure(self):
        _, out, _ = self.run_check(latest="<html>not found</html>")
        self.assertIn("could not reach GitHub", out)

    def test_turned_off(self):
        with patch.dict(os.environ, {"BPS_UPDATE_CHECK": "off"}):
            _, out, opened = self.run_check(latest="9.9.9")
        self.assertIn("turned off", out)
        self.assertEqual(opened.call_count, 0)

    def test_unwritable_state_does_not_fail(self):
        with patch.object(cu, "state_path", return_value=Path("/nonexistent-root/x/update-check.json")):
            code, out, _ = self.run_check(latest="1.4.0")
        self.assertEqual(code, 0)
        self.assertIn("Up to date", out)

    def test_versions_compare_numerically(self):
        self.assertGreater(cu.as_tuple("1.10.0"), cu.as_tuple("1.9.9"))
        self.assertEqual(cu.as_tuple("1.4.0"), cu.as_tuple("1.4.0"))

    def test_install_kind_from_path(self):
        base = Path("/x/home")
        self.assertEqual(cu.install_kind(base / ".claude/plugins/cache/m/p/1.4.0/skills/s"), "claude")
        self.assertEqual(cu.install_kind(base / ".codex/plugins/cache/m/p/1.4.0/skills/s"), "codex")
        self.assertEqual(cu.install_kind(base / ".claude/skills/s"), "folder")
        self.assertIn("claude plugin update", " ".join(cu.update_instructions("claude")))
        self.assertIn("codex plugin marketplace upgrade", " ".join(cu.update_instructions("codex")))
        self.assertIn(".zip", " ".join(cu.update_instructions("folder")))


if __name__ == "__main__":
    unittest.main()
