#!/usr/bin/env python3
"""Keep an installed copy of this plugin's skills current, and say what changed.

Run on first use of a skill in a session. It prints at most two things:

* "UPDATED: ..." when the skills were updated since they were last used, with
  the changelog entries between the two versions, including each version's
  "How to use it" notes. It reads the changelog shipped with the plugin and
  falls back to the public copy on GitHub.
* One status line from a weekly check against the public version number, or an
  "UPDATE AVAILABLE" block with the exact commands for the way the skills were
  installed.

`--whats-new` prints the published changes newer than this copy; run it right
after installing an update, while the old version is still loaded, so the user
hears what changed without waiting for a restart.

It never downloads or changes the skills. The only network requests are
anonymous reads of the public version file and changelog; nothing about the
user or their work is sent.

State is kept outside the skill folders, so an update does not erase it, and it
is shared by all of the plugin's skills:
    $XDG_CACHE_HOME/biomedical-publication-suite/update-check.json
    (default ~/.cache/biomedical-publication-suite/update-check.json)

Settings (environment variables):
    BPS_UPDATE_CHECK=off           no network check (the local UPDATED notice still appears)
    BPS_UPDATE_INTERVAL_DAYS=7     days between checks
    BPS_UPDATE_STATE_DIR=<folder>  where to keep the note
Options: --force checks now regardless of the interval; --whats-new is described above.
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
RAW_BASE = f"https://raw.githubusercontent.com/{PUBLIC_REPO}/main/plugins/{NAME}"
LATEST_URL = f"{RAW_BASE}/skills/{NAME}/VERSION"
CHANGELOG_URL = f"{RAW_BASE}/CHANGELOG.md"
RELEASES_URL = f"https://github.com/{PUBLIC_REPO}/releases/latest"
SKILL_DIR = Path(__file__).resolve().parents[1]
RETRY_AFTER_FAILURE = timedelta(days=1)
TIMEOUT_SECONDS = 4
MAX_ENTRY_CHARS = 4000
HEADING = re.compile(r"^## (\d+(?:\.\d+){1,3})\b.*$", re.M)


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


def fetch_text(url: str, limit: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": f"{NAME}-update-check"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read(limit).decode("utf-8")


def fetch_latest() -> str:
    text = fetch_text(LATEST_URL, 64).strip()
    if not re.fullmatch(r"\d+(\.\d+){1,3}", text):
        raise ValueError(f"unexpected version text {text[:20]!r}")
    return text


def fetch_changelog() -> str:
    text = fetch_text(CHANGELOG_URL, 400_000)
    if not HEADING.search(text):
        raise ValueError("unexpected changelog text")
    return text


def local_changelog(skill_dir: Path = SKILL_DIR) -> str | None:
    for candidate in (skill_dir.parent.parent / "CHANGELOG.md", skill_dir / "CHANGELOG.md"):
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        if HEADING.search(text):
            return text
    return None


def changelog_entries(text: str, after: str, upto: str | None = None) -> list[tuple[str, str]]:
    """Entries for versions newer than `after` and no newer than `upto`, newest first."""
    marks = list(HEADING.finditer(text))
    entries = []
    for i, mark in enumerate(marks):
        version = mark.group(1)
        if as_tuple(version) <= as_tuple(after):
            continue
        if upto is not None and as_tuple(version) > as_tuple(upto):
            continue
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[mark.start():end].strip()
        if len(body) > MAX_ENTRY_CHARS:
            body = body[:MAX_ENTRY_CHARS].rstrip() + f"\n[...] Full notes: {RELEASES_URL}"
        entries.append((version, body))
    entries.sort(key=lambda item: as_tuple(item[0]), reverse=True)
    return entries


def print_entries(entries: list[tuple[str, str]]) -> None:
    for _, body in entries:
        print(body)
        print()


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
        "and replace each of this plugin's skill folders with the one in the zip.",
    ]


def whats_new(installed: str, path: Path, state: dict) -> int:
    """Print the published changes newer than this copy (run right after updating)."""
    try:
        text = fetch_changelog()
    except Exception as error:  # Network, sandbox, DNS, or an unexpected reply.
        print(f"Could not read the published changelog ({type(error).__name__}). See {RELEASES_URL}")
        return 0
    entries = changelog_entries(text, after=installed)
    if not entries:
        print(f"No published changes are newer than {installed}.")
        return 0
    print(f"WHAT'S NEW since {installed}:")
    print()
    print_entries(entries)
    print("The new version takes effect after Claude Code restarts, or in a new Codex session.")
    state["whats_new_shown_for"] = entries[0][0]
    write_state(path, state)
    return 0


def report_update(installed: str, state: dict, network_ok: bool) -> None:
    """Announce an update since last use, once, with what changed."""
    last_seen = state.get("last_seen_version") or state.get("installed")
    if not last_seen:
        state["last_seen_version"] = installed  # First use: nothing to compare with.
        return
    if as_tuple(installed) <= as_tuple(last_seen):
        return  # Same version, or an older copy elsewhere; keep the newest version seen.
    print(f"UPDATED: version {installed} is now in use (previously {last_seen}).")
    shown = state.get("whats_new_shown_for")
    if shown and as_tuple(shown) >= as_tuple(installed):
        print("Its changes were shown when the update was installed.")
    else:
        text = local_changelog()
        if text is None and network_ok:
            try:
                text = fetch_changelog()
            except Exception:  # Fall back to the release page below.
                text = None
        entries = changelog_entries(text, after=last_seen, upto=installed) if text else []
        if entries:
            print("WHAT'S NEW:")
            print()
            print_entries(entries)
        else:
            print(f"What changed: {RELEASES_URL}")
    state["last_seen_version"] = installed


def main(argv: list[str]) -> int:
    installed = installed_version()
    path = state_path()
    state = read_state(path)
    check_off = os.environ.get("BPS_UPDATE_CHECK", "").lower() in {"off", "0", "false", "no"}

    if "--whats-new" in argv:
        return whats_new(installed, path, state)

    report_update(installed, state, network_ok=not check_off)
    write_state(path, state)

    if check_off:
        print("Update check is turned off.")
        return 0
    try:
        interval = timedelta(days=float(os.environ.get("BPS_UPDATE_INTERVAL_DAYS", "7")))
    except ValueError:
        interval = timedelta(days=7)

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
