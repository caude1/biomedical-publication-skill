#!/usr/bin/env python3
"""Check, at most once a week, whether a newer version of this skill is published.

Prints one short status line, or an UPDATE AVAILABLE block with the exact
commands for the way the skill was installed. It never downloads or changes
the skill. The only network request is an anonymous read of the public
version file; nothing about the user or their work is sent.

State is kept outside the skill folder, so an update does not erase it:
    $XDG_CACHE_HOME/biomedical-publication-suite/update-check.json
    (default ~/.cache/biomedical-publication-suite/update-check.json)

Settings (environment variables):
    BPS_UPDATE_CHECK=off           never check
    BPS_UPDATE_INTERVAL_DAYS=7     days between checks
    BPS_UPDATE_STATE_DIR=<folder>  where to keep the note
Use --force to check now regardless of the interval.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

NAME = "biomedical-publication-suite"
PUBLIC_REPO = "caude1/biomedical-publication-skill"
LATEST_URL = (
    f"https://raw.githubusercontent.com/{PUBLIC_REPO}/main/plugins/{NAME}/skills/{NAME}/VERSION"
)
RELEASES_URL = f"https://github.com/{PUBLIC_REPO}/releases/latest"
SKILL_DIR = Path(__file__).resolve().parents[1]
RETRY_AFTER_FAILURE = timedelta(days=1)
TIMEOUT_SECONDS = 4


def installed_version(skill_dir: Path = SKILL_DIR) -> str:
    return (skill_dir / "VERSION").read_text(encoding="utf-8").strip()


def as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def state_path() -> Path:
    folder = os.environ.get("BPS_UPDATE_STATE_DIR")
    if not folder:
        cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        folder = os.path.join(cache, NAME)
    return Path(folder) / "update-check.json"


def read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(path: Path, state: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass  # A read-only home or a sandbox is not a reason to interrupt the user's task.


def parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def is_due(state: dict, now: datetime, interval: timedelta) -> bool:
    checked = parse_time(state.get("last_checked"))
    attempted = parse_time(state.get("last_failed_attempt"))
    if attempted and now - attempted < RETRY_AFTER_FAILURE:
        return False
    return checked is None or now - checked >= interval


def fetch_latest() -> str:
    request = urllib.request.Request(LATEST_URL, headers={"User-Agent": f"{NAME}-update-check"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        text = response.read(64).decode("utf-8").strip()
    if not re.fullmatch(r"\d+(\.\d+){1,3}", text):
        raise ValueError(f"unexpected version text {text[:20]!r}")
    return text


def install_kind(skill_dir: Path = SKILL_DIR) -> str:
    parts = skill_dir.parts
    for i in range(len(parts) - 2):
        if parts[i + 1 : i + 3] == ("plugins", "cache"):
            if parts[i] == ".codex":
                return "codex"
            return "claude"
    return "folder"


def update_instructions(kind: str) -> list[str]:
    if kind == "claude":
        return [
            "Update in Claude Code with:",
            f"  claude plugin marketplace update {NAME}",
            f"  claude plugin update {NAME}@{NAME}",
            "then restart Claude Code. Inside a session, /plugin offers the same update.",
            f"To get future updates automatically: /plugin > Marketplaces > {NAME} > Enable auto-update.",
        ]
    if kind == "codex":
        return [
            "Update in Codex with:",
            f"  codex plugin marketplace upgrade {NAME}",
            "then start a new session.",
        ]
    return [
        f"Download {NAME}.zip from {RELEASES_URL}",
        "and replace this skill folder with the one in the zip.",
    ]


def main(argv: list[str]) -> int:
    if os.environ.get("BPS_UPDATE_CHECK", "").lower() in {"off", "0", "false", "no"}:
        print("Update check is turned off.")
        return 0
    try:
        interval = timedelta(days=float(os.environ.get("BPS_UPDATE_INTERVAL_DAYS", "7")))
    except ValueError:
        interval = timedelta(days=7)

    installed = installed_version()
    path = state_path()
    state = read_state(path)
    now = datetime.now(timezone.utc)

    if "--force" not in argv and not is_due(state, now, interval):
        checked = parse_time(state.get("last_checked"))
        when = f"last checked {checked.date().isoformat()}" if checked else "retrying after a failed attempt"
        print(f"Update check not due (installed {installed}; {when}).")
        return 0

    try:
        latest = fetch_latest()
    except Exception as error:  # Network, sandbox, DNS, or an unexpected reply.
        state["last_failed_attempt"] = now.isoformat(timespec="seconds")
        write_state(path, state)
        print(f"Update check could not reach GitHub ({type(error).__name__}); will retry tomorrow.")
        return 0

    state.update(
        last_checked=now.isoformat(timespec="seconds"),
        installed=installed,
        latest=latest,
    )
    state.pop("last_failed_attempt", None)
    write_state(path, state)

    if as_tuple(latest) > as_tuple(installed):
        print(f"UPDATE AVAILABLE: version {latest} is published; this copy is {installed}.")
        print(f"What changed: {RELEASES_URL}")
        for line in update_instructions(install_kind()):
            print(line)
    else:
        print(f"Up to date (installed {installed}; latest {latest}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
