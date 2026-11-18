#!/usr/bin/env python3
"""Open and close the audit's self-contained workspace, `_audit/` at the project root.

  open    Create _audit/ and fill it without changing anything outside it:
            baseline/      the project as found: every file except archives, version
                           control and environments (raw data too when it can be cloned)
            work/          an isolated working copy of the same files, raw data included:
                           every rerun, fix and new analysis happens here
            MANIFEST.tsv   size and sha256 of every file, and the target of every link
            raw_paths.txt  raw-data locations declared with --raw; inventory.py and
                           safe_move.py read it, so the declaration is made once
            runs/, proposal/, inventory/, register.md, README.md
          Files are cloned on APFS (instant; disk is used only when a copy changes) and
          copied elsewhere. The folder is marked so that iCloud Drive does not sync it.
          Nothing in work/ reaches back into the project or outside it:
            - a link to something inside the project is recreated in work/ and points at
              the working copy; a link to a file outside the project is replaced by a
              clone of that file; a link to an outside folder is left out (README lists it);
            - environments are not mirrored: Python virtual environments and node_modules
              are left out, and only renv's small setup files are copied (not its library).
              Run the project's environment without changing it, or build one inside work/;
            - raw data that can be neither cloned nor copied (--copy-raw-max-mb) is left
              out and listed, unless --allow-links, which links it file by file (code that
              writes to a linked file changes the real raw data).
          The one exception to that isolation is what --allow-links links, and tools' own
          package caches outside the project (renv, pip, npm), which are not project files.

  status  What has changed in the project since open.

  close   After the approved changes are implemented and verified: refuse if any project
          link points into _audit/ or archive/ resolves outside the project; keep the audit's
          record in archive/audit_<date>/ (prior_versions/<path> for every file edited or
          removed since open, each checked against its starting hash; files moved unchanged
          by safe_move.py need no copy; MANIFEST.tsv; raw_paths.txt; the analysis register
          and the report; LINKS.tsv for changed links); add an entry to archive/README.md; then
          erase _audit/. Every manifest path and every copy is checked first; if anything fails,
          nothing is erased.
          Dry run unless --confirm.

Examples
  python3 audit_workspace.py open --root .
  python3 audit_workspace.py open --root . --raw measurements     # raw data not under raw/
  python3 audit_workspace.py status --root .
  python3 audit_workspace.py close --root .            # shows what will happen
  python3 audit_workspace.py close --root . --confirm
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import ctypes.util
import datetime as dt
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rawpaths  # noqa: E402  one definition of raw data for every script

WS = "_audit"
MANIFEST = "MANIFEST.tsv"
SKIP_DIRS = {WS, ".git", ".hg", ".svn", "__pycache__", ".ipynb_checkpoints", ".Rproj.user",
             ".quarto", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".Trash"}
ENV_DIRS = {".venv", "venv", "node_modules"}   # never mirrored: absolute paths and links inside
RENV = "renv"                                  # only its top-level setup files are copied
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini", ".localized"}
ARCHIVE_DIR_RE = re.compile(
    r"^_*(archives?|archived|old|older|deprecated|legacy|attic|graveyard|trash|"
    r"backups?|bak|obsolete|superseded|retired|unused)$", re.I)
SF_DATALESS = 0x40000000
PRESERVED = {"cloned", "copied"}
DISPOSITIONS = ("cloned", "copied", "raw, cloned", "raw, hashed in place",
                "not preserved (too large to copy, cannot clone)")
NO_SYNC_XATTR = "com.apple.fileprovider.ignore#P"


def _load_clonefile():
    if sys.platform != "darwin" or os.environ.get("AUDIT_WS_NO_CLONE"):
        return None
    try:
        fn = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True).clonefile
    except (OSError, AttributeError, TypeError):
        return None
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32]
    fn.restype = ctypes.c_int
    return fn


_CLONEFILE = _load_clonefile()
CLONE_NOFOLLOW = 0x0001


def clone(src: Path, dst: Path) -> bool:
    """Copy-on-write clone of a file or folder (APFS). False when the filesystem cannot."""
    if _CLONEFILE is None:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    return _CLONEFILE(os.fsencode(str(src)), os.fsencode(str(dst)), CLONE_NOFOLLOW) == 0


def place(src: Path, dst: Path, max_copy_bytes: float) -> str:
    """Clone src to dst, else copy it when it is small enough: 'cloned', 'copied' or ''."""
    if clone(src, dst):
        return "cloned"
    if src.stat().st_size <= max_copy_bytes:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return "copied"
    return ""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def within(parent: Path, p: Path) -> bool:
    return p == parent or parent in p.parents


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def walk(root: Path):
    """Project files and links, plus the environment and archive folders left out."""
    files, links, envs, renvs, archives = [], [], [], [], []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        rel_dir = d.relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        keep = []
        for name in sorted(dirnames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            full = d / name
            if os.path.islink(full):
                if not (rel_dir == "" and name == WS):
                    links.append(rel)
            elif name in SKIP_DIRS:
                continue
            elif name in ENV_DIRS or (full / "pyvenv.cfg").exists():
                envs.append(rel)
            elif name == RENV:
                renvs.append(rel)
            elif ARCHIVE_DIR_RE.match(name):
                archives.append(rel)
            else:
                keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            if name in JUNK:
                continue
            rel = f"{rel_dir}/{name}" if rel_dir else name
            (links if os.path.islink(d / name) else files).append(rel)
    return files, links, envs, renvs, archives


def mark_no_sync(ws: Path) -> bool:
    """Keep the workspace out of iCloud Drive (File Provider honors this attribute)."""
    if sys.platform != "darwin":
        return False
    try:
        return subprocess.run(["xattr", "-w", NO_SYNC_XATTR, "1", str(ws)],
                              capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def cmd_open(args) -> int:
    root = Path(args.root).resolve()
    ws = root / WS
    if os.path.lexists(ws):
        print(f"error: {ws} already exists. Read {WS}/README.md; close it or remove it first.",
              file=sys.stderr)
        return 2
    root_real = Path(os.path.realpath(root))
    try:
        locations = rawpaths.declared(root, args.raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    files, links, envs, renvs, archives = walk(root)
    evicted = [r for r in files if getattr(os.lstat(root / r), "st_flags", 0) & SF_DATALESS]
    if evicted and not args.allow_evicted:
        print(f"error: {len(evicted)} files are evicted cloud placeholders (e.g. {evicted[0]}). "
              "Materialize them first (SKILL.md, step 1) or pass --allow-evicted.", file=sys.stderr)
        return 2
    raw_files = {r for r in files if rawpaths.is_raw(r, locations)}
    raw_total = sum((root / r).stat().st_size for r in raw_files)
    copy_raw = raw_total <= args.copy_raw_max_mb * 1_000_000
    max_copy = args.max_copy_mb * 1_000_000

    ws.mkdir()
    no_sync = mark_no_sync(ws)
    base, work = ws / "baseline", ws / "work"
    for d in (base, work, ws / "runs", ws / "proposal", ws / "inventory"):
        d.mkdir()
    rows: list[tuple[str, str, str, str]] = []
    notes: dict[str, list[str]] = {k: [] for k in (
        "not_preserved", "not_in_work", "raw_linked", "raw_left_out", "link_cloned",
        "link_left_out", "link_linked")}
    methods: set[str] = set()
    for rel in files:
        src = root / rel
        size, digest = src.stat().st_size, sha256(src)
        if rel in raw_files:
            how = "cloned" if clone(src, base / rel) else "hashed in place"
            rows.append((rel, str(size), digest, f"raw, {how}"))
            got = place(src, work / rel, float("inf") if copy_raw else -1)
            if got:
                methods.add(got)
            elif args.allow_links:
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(src, work / rel)
                notes["raw_linked"].append(rel)
            else:
                notes["raw_left_out"].append(rel)
            continue
        how = place(src, base / rel, max_copy)
        rows.append((rel, str(size), digest, how or "not preserved (too large to copy, cannot clone)"))
        if how:
            methods.add(how)
        else:
            notes["not_preserved"].append(rel)
        if not place(src, work / rel, max_copy):
            notes["not_in_work"].append(rel)
    for rel in links:
        p = root / rel
        target = os.readlink(p)
        resolved = Path(os.path.realpath(p))
        rows.append((rel, "", "", f"symlink:{target}"))
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if within(root_real / WS, resolved) or within(resolved, root_real):
            notes["link_left_out"].append(f"{rel} -> {target} (points into the workspace or above the project)")
        elif within(root_real, resolved):
            os.symlink(os.path.relpath(work / resolved.relative_to(root_real), dst.parent), dst)
        elif args.allow_links:
            os.symlink(resolved, dst)
            notes["link_linked"].append(f"{rel} -> {resolved}")
        elif resolved.is_file() and place(resolved, dst, max_copy):
            notes["link_cloned"].append(f"{rel} -> {target}")
        else:
            notes["link_left_out"].append(f"{rel} -> {target}")
    for rel in renvs:
        for item in sorted((root / rel).iterdir()):
            if item.is_file() and not item.is_symlink():
                (work / rel).mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, work / rel / item.name)
    with open(ws / MANIFEST, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["path", "size_bytes", "sha256", "disposition"])
        w.writerows(sorted(rows))
    (ws / "raw_paths.txt").write_text(
        "# Raw-data locations declared when the workspace opened, one per line. inventory.py and\n"
        "# safe_move.py read this file. Folders named raw/, raw_data/, ... are raw data anyway.\n"
        + "".join(f"{loc}\n" for loc in locations), encoding="utf-8")
    (ws / "register.md").write_text(
        "# Analysis register\n\nEach entry is written before its analysis runs or is delegated. "
        "Format: references/templates.md, section 1.\n\n## Considered and set aside\n\n",
        encoding="utf-8")

    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    kept = sum(1 for r in rows if r[3] in PRESERVED)
    method = ("cloned (copy-on-write)" if methods == {"cloned"} else
              "copied" if methods == {"copied"} else "cloned or copied")
    readme = f"""# Audit workspace

Temporary. Opened {now}. Everything the audit produces lives here, and nothing outside this
folder changes until the user decides what to implement. After implementation it is erased
with `audit_workspace.py close`, which first keeps the audit's record, and the prior version of
every edited file, in archive/audit_<date>/.{" Marked so that iCloud Drive does not sync it." if no_sync else ""}

**Status:** part 1, audit in progress.

- `baseline/`: the project as found ({kept} files {method}). `MANIFEST.tsv` records the size
  and sha256 of every file and the target of every link. Raw data ({len(raw_files)} files,
  {human(raw_total)}) is protected where it sits.
- `work/`: the isolated working copy. Run the pipeline here. Nothing in it reaches back into
  the project, apart from anything listed below as linked (--allow-links) and tools' own package
  caches outside the project.
- `raw_paths.txt`: raw-data locations declared at open ({", ".join(locations) or "none"}).
- `runs/`: outputs of each run in the reproduction chain.
- `register.md`: the analysis register.
- `REPORT.md`: the updated scientific narrative, findings and recommendations (end of part 1).
- `proposal/`: the reorganization plan, rewritten drafts, anything else proposed.
- `inventory/`: scan outputs.
"""
    sections = [
        ("not_preserved", "Not preserved in baseline/ (too large to copy, cannot clone). Part 2 may "
                          "change these only with the user's explicit approval"),
        ("not_in_work", "Not in work/ (too large to copy); regenerate them there if needed"),
        ("raw_left_out", "Raw data not in work/ (it cannot be cloned here, and in total it exceeds "
                         "--copy-raw-max-mb). Read it from the project without writing to it, or "
                         "reopen with a larger --copy-raw-max-mb or with --allow-links"),
        ("raw_linked", "Raw data LINKED into work/ (--allow-links): code that writes to these paths "
                       "changes the real files. Fix anything that writes to raw data before running"),
        ("link_cloned", "Links to files outside the project, replaced in work/ by a clone of the file"),
        ("link_linked", "Links to outside the project, kept as links (--allow-links): writes through "
                        "them change files outside the project"),
        ("link_left_out", "Links left out of work/"),
    ]
    for key, title in sections:
        if notes[key]:
            items = notes[key]
            readme += f"\n{title}:\n" + "".join(f"- `{x}`\n" for x in items[:40])
            if len(items) > 40:
                readme += f"- ...and {len(items) - 40} more\n"
    if envs or renvs:
        readme += ("\nEnvironments not mirrored: " + ", ".join(f"`{v}`" for v in envs + renvs)
                   + (" (renv: only its setup files are in work/, not its library)" if renvs else "")
                   + ". Run the project's environment without changing it (call its interpreter, "
                     "with PYTHONDONTWRITEBYTECODE=1); never install into it. If packages must "
                     "change, build them inside work/ (a new venv, `renv::restore()` run in work/, "
                     "`npm ci` in work/).\n")
    if archives:
        readme += ("\nArchive folders left out of the working copy: "
                   + ", ".join(f"`{a}`" for a in archives) + "\n")
    (ws / "README.md").write_text(readme, encoding="utf-8")

    print(f"Opened {ws}{' (not synced to iCloud)' if no_sync else ''}")
    print(f"  baseline: {kept} files {method}; manifest of {len(rows)} entries")
    print(f"  raw data: {len(raw_files)} files ({human(raw_total)})"
          + (f"; declared locations: {', '.join(locations)}" if locations else ""))
    for key, title in sections:
        if notes[key]:
            print(f"  {title.split('.')[0].split(' (')[0]}: {len(notes[key])} (listed in {WS}/README.md)")
    if envs or renvs:
        print(f"  environments not mirrored: {', '.join(envs + renvs)} (use read-only, or build in work/)")
    return 0


def load_manifest(ws: Path) -> list[dict]:
    """The manifest written at open. ValueError if it was altered into something unsafe."""
    with open(ws / MANIFEST, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    seen = set()
    for r in rows:
        rel, disp = r.get("path") or "", r.get("disposition") or ""
        parts = rel.split("/")
        if (not rel or rel.startswith("/") or "\\" in rel or any(x in ("", ".", "..") for x in parts)
                or rel in seen or parts[0] == WS
                or not (disp in DISPOSITIONS or disp.startswith("symlink:"))):
            raise ValueError(f"{WS}/{MANIFEST} has an invalid entry: {rel!r} ({disp!r})")
        seen.add(rel)
    return rows


def logged_moves(root: Path) -> tuple[dict[str, str], set[str]]:
    """Completed moves and junk deletions from safe_move.py's log."""
    moved, junk = {}, set()
    log = root / "archive" / "file_moves.csv"
    if log.is_file() and not log.is_symlink():
        with open(log, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("status") != "done" or not r.get("src"):
                    continue
                if r.get("action") in {"move", "rename", "archive"} and r.get("dst"):
                    moved[r["src"]] = r["dst"]
                elif r.get("action") == "delete_junk":
                    junk.add(r["src"])
    return moved, junk


def since_open(root: Path, ws: Path) -> dict[str, list]:
    """Sort the baseline's entries by what happened to them since open.

    changed:  (path, now_at) edited in place, or moved (logged) and edited
    removed:  path gone, with no logged destination inside the project
    moved:    (path, now_at) moved unchanged, logged in archive/file_moves.csv
    links:    (path, target at open, what happened)
    not_kept: edited or gone, but not preserved at open
    """
    root_real = Path(os.path.realpath(root))
    moved, junk = logged_moves(root)

    def regular_inside(p: Path) -> bool:
        return (os.path.isfile(p) and not os.path.islink(p)
                and within(root_real, Path(os.path.realpath(p))))

    def follow(p: str) -> str:
        seen = set()
        while p in moved and p not in seen:
            seen.add(p)
            p = moved[p]
        return p

    out: dict[str, list] = {"changed": [], "removed": [], "moved": [], "links": [], "not_kept": []}
    for row in load_manifest(ws):
        rel, disp = row["path"], row["disposition"]
        if disp.startswith("raw") or rel in junk:
            continue
        if disp.startswith("symlink:"):
            old = disp[len("symlink:"):]
            p = root / rel
            if os.path.islink(p):
                if os.readlink(p) != old:
                    out["links"].append((rel, old, f"now points to {os.readlink(p)}"))
            elif os.path.lexists(p):
                out["links"].append((rel, old, "replaced by a file or folder"))
            else:
                dest = follow(rel)
                out["links"].append((rel, old, f"moved to {dest}" if dest != rel else "removed"))
            continue
        here: Path | None = root / rel
        now_at = rel
        if not regular_inside(here):
            dest = follow(rel)
            here = root / dest if dest != rel and regular_inside(root / dest) else None
            now_at = dest
        if here is not None and str(here.stat().st_size) == row["size_bytes"] \
                and sha256(here) == row["sha256"]:
            if now_at != rel:
                out["moved"].append((rel, now_at))
            continue
        if disp not in PRESERVED:
            out["not_kept"].append(rel)
        elif here is None:
            out["removed"].append(rel)
        else:
            out["changed"].append((rel, now_at))
    return out


def cmd_status(args) -> int:
    root = Path(args.root).resolve()
    ws = root / WS
    if os.path.islink(ws) or not (ws / MANIFEST).is_file():
        print("No audit workspace here.")
        return 0
    first = (ws / "README.md").read_text(encoding="utf-8").split("**Status:**")
    print(f"Workspace: {ws}")
    if len(first) > 1:
        print("Status:" + first[1].split("\n")[0])
    try:
        rawpaths.declared(root)
        st = since_open(root, ws)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Since open: {len(st['changed'])} edited, {len(st['removed'])} removed, "
          f"{len(st['moved'])} moved unchanged (logged), {len(st['links'])} links changed")
    for rel, now_at in st["changed"][:40]:
        print(f"  edited   {rel}" + (f"  (now at {now_at})" if now_at != rel else ""))
    for rel in st["removed"][:40]:
        print(f"  removed  {rel}")
    for rel, old, what in st["links"][:40]:
        print(f"  link     {rel} -> {old}: {what}")
    for rel in st["not_kept"]:
        print(f"  NOT PRESERVED, edited or removed: {rel}")
    return 0


def cmd_close(args) -> int:
    root = Path(args.root).resolve()
    ws = root / WS
    if not os.path.lexists(ws):
        print("No audit workspace here; nothing to close.")
        return 0
    if os.path.islink(ws) or not (ws / MANIFEST).is_file():
        print(f"error: {ws} is not a workspace made by this script (a link, or no {MANIFEST}).",
              file=sys.stderr)
        return 2
    root_real = Path(os.path.realpath(root))
    ws_real = Path(os.path.realpath(ws))
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        if d == ws:
            dirnames[:] = []
            continue
        for name in dirnames + filenames:
            p = d / name
            if p != ws and os.path.islink(p) and within(ws_real, Path(os.path.realpath(p))):
                print(f"error: {p.relative_to(root)} links into {WS}/; resolve it before closing.",
                      file=sys.stderr)
                return 2
    arch = root / "archive"
    if os.path.lexists(arch) and (not arch.is_dir()
                                  or not within(root_real, Path(os.path.realpath(arch)))):
        print("error: archive/ is not a folder inside the project; fix it before closing.",
              file=sys.stderr)
        return 2
    readme = arch / "README.md"
    if os.path.lexists(readme) and (os.path.islink(readme) or not readme.is_file()):
        print("error: archive/README.md is a link or not a file; fix it before closing.",
              file=sys.stderr)
        return 2

    try:
        rawpaths.declared(root)
        st = since_open(root, ws)
    except ValueError as exc:
        print(f"error: {exc}; nothing was erased.", file=sys.stderr)
        return 2
    keep = [rel for rel, _ in st["changed"]] + st["removed"]
    date = dt.date.today().isoformat()
    dest = arch / f"audit_{date}"
    n = 2
    while os.path.lexists(dest):
        dest = arch / f"audit_{date}_{n}"
        n += 1
    size = 0
    for dirpath, _, filenames in os.walk(ws):
        for name in filenames:
            fp = os.path.join(dirpath, name)
            if not os.path.islink(fp):
                size += os.path.getsize(fp)
    print(f"Keep in {dest.relative_to(root)}/: prior versions of {len(st['changed'])} edited and "
          f"{len(st['removed'])} removed files, the starting manifest, the register and the report")
    for rel, now_at in st["changed"][:60]:
        print(f"  edited   {rel}" + (f"  (now at {now_at})" if now_at != rel else ""))
    for rel in st["removed"][:60]:
        print(f"  removed  {rel}")
    if st["moved"]:
        print(f"Moved unchanged (logged in archive/file_moves.csv, no copy needed): {len(st['moved'])}")
    if st["links"]:
        print(f"Links changed (recorded in LINKS.tsv): {len(st['links'])}")
    if st["not_kept"]:
        print("NOT PRESERVED at open and since edited or removed; no prior version exists "
              "(their starting hashes stay in MANIFEST.tsv):")
        for rel in st["not_kept"]:
            print(f"  {rel}")
    print(f"Then erase {WS}/ ({human(size)}; links inside it are removed, not followed).")
    if not args.confirm:
        print("\nDry run. Rerun with --confirm once the approved changes are implemented and verified.")
        return 0

    dest.mkdir(parents=True)
    dest_real = Path(os.path.realpath(dest))
    if not within(root_real, dest_real):
        print("error: the archive destination resolves outside the project; nothing erased.",
              file=sys.stderr)
        return 2
    base_real = Path(os.path.realpath(ws / "baseline"))
    starting = {r["path"]: r["sha256"] for r in load_manifest(ws)}

    def regular(p: Path, inside: Path) -> bool:
        return (not os.path.islink(p) and p.is_file()
                and within(inside, Path(os.path.realpath(p))))

    for rel in keep:
        src, out = ws / "baseline" / rel, dest / "prior_versions" / rel
        try:
            ok = regular(src, base_real)
            if ok:
                out.parent.mkdir(parents=True, exist_ok=True)
                if not clone(src, out):
                    shutil.copy2(src, out, follow_symlinks=False)
                ok = regular(out, dest_real) and sha256(out) == starting[rel]
        except OSError as exc:
            ok = False
            print(f"error: {exc}", file=sys.stderr)
        if not ok:
            shutil.rmtree(dest)
            print(f"error: could not keep a verified prior version of {rel} (its baseline copy is "
                  f"missing, not a regular file, or changed); nothing was erased.", file=sys.stderr)
            return 1
    shutil.copy2(ws / MANIFEST, dest / MANIFEST)
    if (ws / "raw_paths.txt").is_file():
        shutil.copy2(ws / "raw_paths.txt", dest / "raw_paths.txt")
    if st["links"]:
        with open(dest / "LINKS.tsv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, delimiter="\t", lineterminator="\n")
            w.writerow(["path", "target_at_open", "since"])
            w.writerows(st["links"])
    for name, kept_as in (("register.md", "analysis_register.md"), ("REPORT.md", "audit_report.md")):
        if (ws / name).is_file():
            shutil.copy2(ws / name, dest / kept_as)
    entry = (f"\n## {date} audit\n- `{dest.name}/`: the audit's record: `prior_versions/` (the files "
             f"the approved changes edited or removed, {len(keep)}, at their original paths); "
             f"`{MANIFEST}` (size and sha256 of every file as found, and every link); "
             "`raw_paths.txt` (raw-data locations declared); "
             "`analysis_register.md` and `audit_report.md`"
             + ("; `LINKS.tsv` (links that changed)" if st["links"] else "")
             + ". See docs/CHANGELOG.md and archive/file_moves.csv.\n")
    prev = readme.read_text(encoding="utf-8") if readme.is_file() else "# Archive\n"
    tmp = arch / f".README.md.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(prev.rstrip("\n") + "\n" + entry)
    os.replace(tmp, readme)          # a new file: never writes through a hard link
    shutil.rmtree(ws)
    print(f"Closed: the audit's record is in {dest.relative_to(root)}/; {WS}/ erased.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    o.add_argument("--root", default=".")
    o.add_argument("--raw", action="append", default=[],
                   help="raw-data location outside a folder named raw/raw_data/... (repeatable); "
                        "recorded in _audit/raw_paths.txt for every later scan and move")
    o.add_argument("--copy-raw-max-mb", type=float, default=500,
                   help="when files cannot be cloned, copy raw data into work/ only if its total "
                        "is at most this (default 500); raw data then stays out of baseline/, "
                        "hashed in place")
    o.add_argument("--max-copy-mb", type=float, default=500,
                   help="when files cannot be cloned, copy each non-raw file only up to this "
                        "size (default 500)")
    o.add_argument("--allow-links", action="store_true",
                   help="link into work/ the raw data that cannot be cloned or copied, and every "
                        "link to a file or folder outside the project (writes through these links "
                        "reach the real files)")
    o.add_argument("--allow-evicted", action="store_true",
                   help="proceed although some files are evicted cloud placeholders")
    o.set_defaults(func=cmd_open)
    st = sub.add_parser("status")
    st.add_argument("--root", default=".")
    st.set_defaults(func=cmd_status)
    c = sub.add_parser("close")
    c.add_argument("--root", default=".")
    c.add_argument("--confirm", action="store_true", help="actually keep the record and erase")
    c.set_defaults(func=cmd_close)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
