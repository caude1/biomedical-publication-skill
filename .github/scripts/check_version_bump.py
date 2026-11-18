"""Fail when the skill changed but its version did not.

Claude Code treats a plugin as updated only when the version in plugin.json
changes, so a change shipped under the old number never reaches people who
installed the plugin. Usage: python3 check_version_bump.py BASE_COMMIT
"""
import json
import re
import subprocess
import sys

PLUGIN = "plugins/biomedical-publication-suite"
SHIPPED = [f"{PLUGIN}/skills", f"{PLUGIN}/.claude-plugin", f"{PLUGIN}/.codex-plugin"]
MANIFESTS = [f"{PLUGIN}/.claude-plugin/plugin.json", f"{PLUGIN}/.codex-plugin/plugin.json"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def version_at(commit: str | None, path: str) -> str:
    text = git("show", f"{commit}:{path}") if commit else open(path, encoding="utf-8").read()
    return json.loads(text)["version"]


def as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else ""
    current = {path: version_at(None, path) for path in MANIFESTS}
    if len(set(current.values())) != 1:
        fail(f"The two plugin.json files disagree on the version: {current}")
    new = next(iter(current.values()))

    if not base or set(base) == {"0"} or subprocess.run(
        ["git", "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True
    ).returncode:
        print(f"No earlier commit to compare with; version is {new}.")
        return

    changed = git("diff", "--name-only", base, "HEAD", "--", *SHIPPED).split()
    if not changed:
        print(f"The installed skill is unchanged; version stays {new}.")
        return

    old = version_at(base, MANIFESTS[0])
    if as_tuple(new) <= as_tuple(old):
        fail(
            f"The skill changed ({len(changed)} files, e.g. {changed[0]}) but the version is "
            f"{new}, not higher than {old}. Raise \"version\" in both plugin.json files and add "
            f"a CHANGELOG entry, or friends who installed the plugin will not receive the change."
        )
    changelog = open(f"{PLUGIN}/CHANGELOG.md", encoding="utf-8").read()
    if not re.search(rf"^## {re.escape(new)}\b", changelog, re.M):
        fail(f"CHANGELOG.md has no '## {new}' entry describing this release.")
    print(f"Version raised from {old} to {new} for {len(changed)} changed files.")


if __name__ == "__main__":
    main()
