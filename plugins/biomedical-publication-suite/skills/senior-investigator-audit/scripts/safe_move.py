#!/usr/bin/env python3
"""Apply a reorganization plan with guardrails and a per-file log.

The plan is a CSV with columns: action,src,dst,reason
  move / rename   relocate a file or folder (dst required)
  archive         move into archive/ (dst optional; default keeps the
                  original relative path under archive/)
                  For move, rename and archive, a dst ending in "/" or naming an
                  existing folder means "into this folder".
  delete_junk     remove OS/editor/bytecode junk only (.DS_Store, ~$ lock
                  files, *.pyc, a __pycache__ folder holding only bytecode,
                  .pytest_cache/.mypy_cache/.ruff_cache). Notebook checkpoint
                  folders are not junk: archive them.
  mkdir           create a folder
Lines starting with "#" are ignored. Paths are relative to --root.

Guardrails
  - Dry run unless --apply. Every step is validated and reported (a failing
    step does not stop the others from being checked); if any step fails,
    nothing is changed. The dry run also previews the lines of code and docs
    that mention moved paths, and moved scripts that locate files relative
    to their own location.
  - Never overwrites. Never deletes anything but junk. Anything of uncertain
    value is archived instead.
  - Raw data (files under data/raw or other raw-data folders, and any folder
    that contains them) cannot be moved or archived without --allow-raw-moves,
    and can never be deleted.
  - Sources and destinations must resolve inside the project root: a
    symlinked folder cannot lead a move outside it. Symlinks are moved as links.
  - If a step fails during --apply, the run stops, reports INCOMPLETE, and
    exits 1; the log records exactly what ran.
  - Uses `git mv` for tracked files so history follows the file.
  - Appends one row per affected file to the log (default
    archive/file_moves.csv), with size and sha256 when the file is local.
  - After applying, lists active code/docs that still mention old paths.

Example
  python3 safe_move.py --root . --plan _audit/proposal/reorg_plan.csv          # dry run
  python3 safe_move.py --root . --plan _audit/proposal/reorg_plan.csv --apply
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rawpaths  # noqa: E402  one definition of raw data for every script

JUNK_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".localized"}
JUNK_PREFIXES = ("~$", ".~lock.")
JUNK_EXTS = {".pyc", ".pyo"}
BYTECODE_DIR = "__pycache__"      # the only deletable folder, and only when it holds bytecode alone
RAW_DIR_NAMES = rawpaths.ALL_RAW_NAMES
PROTECTED_NAMES = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "renv",
                   ".Rproj.user", ".quarto", "_audit"}
ARCHIVE_DIR_RE = re.compile(
    r"^_*(archives?|archived|old|older|deprecated|legacy|attic|graveyard|trash|"
    r"backups?|bak|obsolete|superseded|retired|unused)$", re.I)
TEXT_EXTS = {".r", ".py", ".rmd", ".qmd", ".ipynb", ".sh", ".sql", ".md",
             ".txt", ".yaml", ".yml", ".json", ".toml", ".tex", ".do", ".jl",
             ".smk", ".mk", ".cfg", ".ini"}
TEXT_NAMES = {"Makefile", "Snakefile", "Justfile", "_targets.R"}
SKIP_SCAN_DIRS = PROTECTED_NAMES | {"__pycache__", "audit"}
LOG_FIELDS = ["timestamp", "run_id", "step", "action", "src", "dst",
              "size_bytes", "sha256", "reason", "status"]
SF_DATALESS = 0x40000000


class PlanError(Exception):
    pass


def norm(p: str) -> str:
    p = (p or "").strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def check_rel(p: str, what: str) -> str:
    if not p:
        raise PlanError(f"{what} is empty")
    pp = PurePosixPath(p.rstrip("/"))
    if pp.is_absolute() or any(part == ".." for part in pp.parts) or not pp.parts:
        raise PlanError(f"{what} must be a path inside the project root: {p}")
    return str(pp)


def is_junk_file_name(name: str) -> bool:
    return (name in JUNK_FILE_NAMES or name.startswith(JUNK_PREFIXES)
            or os.path.splitext(name)[1].lower() in JUNK_EXTS)


def is_protected(rel: str) -> bool:
    return any(part in PROTECTED_NAMES for part in PurePosixPath(rel).parts)


def in_archive(p: str) -> bool:
    return any(ARCHIVE_DIR_RE.match(x) for x in PurePosixPath(p).parts)


def within(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class VirtualFS:
    """Track the effect of planned steps so later steps are checked against the tree as it
    will be, not as it is now."""

    def __init__(self, root: Path):
        self.root = root
        self.gone: set[str] = set()
        self.added: dict[str, str] = {}      # planned path -> "file" | "dir"
        self.dir_moves: list[tuple[str, str]] = []  # (origin, dest), in order

    def _real_kind(self, p: str) -> str | None:
        real = self.root / p
        if real.is_dir():
            return "dir"
        if os.path.lexists(real):
            return "file"
        return None

    def _gone(self, p: str) -> bool:
        parts = PurePosixPath(p).parts
        return any(str(PurePosixPath(*parts[:i])) in self.gone
                   for i in range(1, len(parts) + 1))

    def kind(self, p: str) -> str | None:
        if p in self.added:
            return self.added[p]
        if self._gone(p):
            return None
        for origin, dest in reversed(self.dir_moves):
            if p.startswith(dest + "/"):
                return self._real_kind(origin + p[len(dest):])
        return self._real_kind(p)

    def origin(self, p: str) -> str:
        """Where a planned path lives on disk before the plan runs."""
        for origin, dest in reversed(self.dir_moves):
            if p == dest or p.startswith(dest + "/"):
                return origin + p[len(dest):]
        return p

    def incoming(self, folder: str) -> list[str]:
        """Planned paths that earlier steps put inside folder."""
        return [p for p in self.added if p.startswith(folder + "/")] + \
               [d for _, d in self.dir_moves if d.startswith(folder + "/")]

    def move(self, src: str, dst: str, kind: str):
        self.gone.add(src)
        self.added.pop(src, None)
        self.gone.discard(dst)
        self.added[dst] = kind
        if kind == "dir":
            self.dir_moves.append((src, dst))
        parent = PurePosixPath(dst).parent
        while str(parent) not in (".", ""):
            self.added.setdefault(str(parent), "dir")
            parent = parent.parent

    def remove(self, p: str):
        self.gone.add(p)
        self.added.pop(p, None)


class Checker:
    """Resolves what each planned path really touches, and applies the protections to that."""

    def __init__(self, root: Path, extra_raw: list[str], log_rel: str | None):
        self.root = root
        self.root_real = Path(os.path.realpath(root))
        self.extra_raw = [norm(x).rstrip("/") for x in extra_raw]
        self.log_rel = log_rel
        self.vfs = VirtualFS(root)
        if log_rel:
            self.vfs.added[log_rel] = "file"          # reserved: nothing may land on the log

    def is_raw(self, rel: str) -> bool:
        """Raw data, or a folder that is itself raw (shared definition in rawpaths.py)."""
        return rawpaths.is_raw_folder(rel, self.extra_raw)

    def entry(self, rel: str) -> tuple[Path, str | None]:
        """The filesystem entry a planned path names: parent folders resolved through symlinks
        (and through earlier planned moves), final component kept as is. Returns the absolute
        entry and its root-relative path, or None when it lies outside the root."""
        p = self.root / self.vfs.origin(rel)
        tail = [p.name]
        parent = p.parent
        while not os.path.lexists(parent) and parent != parent.parent:
            tail.insert(0, parent.name)
            parent = parent.parent
        real = Path(os.path.realpath(parent)).joinpath(*tail)
        if not within(self.root_real, real):
            return real, None
        return real, real.relative_to(self.root_real).as_posix()

    def checked(self, rel: str, role: str) -> tuple[Path, str]:
        real, rrel = self.entry(rel)
        if rrel is None:
            raise PlanError(f"{role} resolves outside the project root (through a symlinked folder?): {rel}")
        if is_protected(rel) or is_protected(rrel):
            raise PlanError(f"{role} is a protected location (version control, environments, "
                            f"or the audit workspace): {rel}")
        if self.log_rel and (rrel == self.log_rel or self.log_rel.startswith(rrel + "/")
                             or rel == self.log_rel or self.log_rel.startswith(rel + "/")):
            if role == "source":
                raise PlanError("this step would move or delete the move log itself")
        return real, rrel

    def touches_raw(self, rel: str, real: Path, rrel: str) -> bool:
        if self.is_raw(rel) or self.is_raw(rrel):
            return True
        if real.is_dir() and not real.is_symlink():
            for dirpath, dirnames, files in os.walk(real):
                for name in dirnames + files:
                    sub = Path(dirpath) / name
                    if self.is_raw(sub.relative_to(self.root_real).as_posix()):
                        return True
        return False


def read_plan(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    missing = {"action", "src"} - set(reader.fieldnames or [])
    if missing:
        raise PlanError(f"plan is missing columns: {', '.join(sorted(missing))}")
    return [dict(r) for r in reader]


def validate(root: Path, plan: list[dict], allow_raw: bool, log_rel: str | None = None,
             extra_raw: list[str] | None = None) -> tuple[list[dict], list[str]]:
    """Check every step against the tree as the plan will leave it. A failing step is reported
    and left out of the simulation, so later steps are still checked."""
    ck = Checker(root, extra_raw or [], log_rel)
    vfs = ck.vfs
    steps, errors = [], []
    for i, r in enumerate(plan, start=1):
        action = (r.get("action") or "").strip().lower()
        src_raw, dst_raw = norm(r.get("src", "")), norm(r.get("dst", ""))
        reason = (r.get("reason") or "").strip()
        step = {"step": i, "action": action, "src": src_raw, "dst": dst_raw,
                "reason": reason, "kind": "", "error": ""}
        try:
            if action not in {"move", "rename", "archive", "delete_junk", "mkdir"}:
                raise PlanError(f"unknown action '{action}'")
            if not reason and action != "mkdir":
                raise PlanError("every step needs a reason")
            if action == "mkdir":
                dst = check_rel(dst_raw or src_raw, "dst")
                ck.checked(dst, "destination")
                if vfs.kind(dst) == "file":
                    raise PlanError(f"mkdir target is a file: {dst}")
                vfs.added.setdefault(dst, "dir")
                step.update(src="", dst=dst, kind="dir")
                steps.append(step)
                continue
            src = check_rel(src_raw, "src")
            kind = vfs.kind(src)
            if kind is None:
                raise PlanError(f"source does not exist (at this point in the plan): {src}")
            step.update(src=src, kind=kind)
            real, rrel = ck.checked(src, "source")
            if action == "delete_junk":
                name = PurePosixPath(src).name
                if real.is_symlink():
                    if not is_junk_file_name(name) and name != BYTECODE_DIR:
                        raise PlanError(f"only junk can be deleted; archive it instead: {src}")
                elif kind == "dir":
                    if name != BYTECODE_DIR:
                        raise PlanError(f"only a __pycache__ folder of bytecode can be deleted; "
                                        f"archive other folders (tool caches and notebook "
                                        f"checkpoints included): {src}")
                    if vfs.incoming(src):
                        raise PlanError(f"an earlier step moves files into {src}; it cannot then be deleted")
                    for q in real.rglob("*"):
                        if q.is_symlink() or (q.is_file() and q.suffix.lower() not in JUNK_EXTS):
                            raise PlanError(f"{src} holds something other than bytecode "
                                            f"({q.name}); archive it instead")
                elif not is_junk_file_name(name):
                    raise PlanError(f"only OS/editor/bytecode junk can be deleted; archive it instead: {src}")
                if ck.touches_raw(src, real, rrel):
                    raise PlanError(f"refusing to delete raw data: {src}")
                vfs.remove(src)
                step["dst"] = ""
                steps.append(step)
                continue
            name = PurePosixPath(src).name
            if action == "archive":
                if in_archive(src):
                    raise PlanError(f"already inside an archive folder: {src}")
                if not dst_raw:
                    dst = f"archive/{src}"
                else:
                    into = dst_raw.endswith("/")
                    dst = check_rel(dst_raw, "dst")
                    if into or vfs.kind(dst) == "dir":
                        dst = f"{dst}/{name}"
                if not in_archive(dst):
                    raise PlanError(f"archive destination must be inside archive/: {dst}")
            else:
                if not dst_raw:
                    raise PlanError("dst is required")
                into = dst_raw.endswith("/")
                dst = check_rel(dst_raw, "dst")
                if into or vfs.kind(dst) == "dir":
                    dst = f"{dst}/{name}"
            step["dst"] = dst
            if dst == src:
                raise PlanError("src and dst are the same")
            if dst.startswith(src + "/"):
                raise PlanError("cannot move a folder into itself")
            if vfs.kind(dst) is not None:
                raise PlanError(f"destination already exists (no overwrite): {dst}")
            ck.checked(dst, "destination")
            if ck.touches_raw(src, real, rrel) and not allow_raw:
                raise PlanError("raw data is protected (this path is or contains raw data); if the move "
                                "is intended (content is never changed), rerun with --allow-raw-moves")
            vfs.move(src, dst, kind)
            steps.append(step)
        except PlanError as exc:
            step["error"] = str(exc)
            steps.append(step)
            errors.append(f"step {i} ({action or '?'} {src_raw} -> {dst_raw}): {exc}")
    return steps, errors


SELF_LOCATING_RE = re.compile(
    r"__file__|\.parents?\[|\.parent\.parent|here::i_am|sys\.path\.insert|"
    r"dirname\(\s*(os\.path\.)?(abspath|realpath)|getActiveDocumentContext|sys\.frame\(1\)\$ofile|"
    r"commandArgs\(trailingOnly\s*=\s*FALSE\)")
CODE_EXTS = {".r", ".py", ".rmd", ".qmd", ".sh", ".ipynb", ".jl"}


def depth_warnings(root: Path, steps: list[dict]) -> list[str]:
    """Moved code that finds files relative to its own location breaks when its depth changes."""
    out = []
    for s in steps:
        if s["error"] or s["action"] not in {"move", "rename", "archive"} or not s["dst"]:
            continue
        shift = len(PurePosixPath(s["dst"]).parts) - len(PurePosixPath(s["src"]).parts)
        if shift == 0 or s["action"] == "archive":
            continue
        for m in expand(root, s["src"], s["kind"]):
            if os.path.splitext(m)[1].lower() not in CODE_EXTS:
                continue
            try:
                text = (root / m).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            hit = SELF_LOCATING_RE.search(text)
            if hit:
                new = s["dst"] + m[len(s["src"]):]
                out.append(f"{new} (was {m}): locates files relative to itself (`{hit.group(0)}`) and moves "
                           f"{abs(shift)} level{'s' if abs(shift) > 1 else ''} "
                           f"{'deeper' if shift > 0 else 'up'}; update its root path")
    return out


def sha256(path: Path, max_mb: float) -> str:
    try:
        st = os.stat(path)
    except OSError:
        return ""
    if st.st_size > max_mb * 1_000_000 or getattr(st, "st_flags", 0) & SF_DATALESS:
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def expand(root: Path, rel: str, kind: str) -> list[str]:
    if kind != "dir":
        return [rel]
    out = []
    for dirpath, _, files in os.walk(root / rel):
        for f in files:
            out.append((Path(dirpath) / f).relative_to(root).as_posix())
    return sorted(out)


def git_tracked(root: Path, rel: str) -> bool:
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", rel],
                           capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def in_git_repo(root: Path) -> bool:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except FileNotFoundError:
        return False


def apply(root: Path, steps: list[dict], log_path: Path, run_id: str,
          use_git: bool, hash_max_mb: float) -> tuple[list[tuple[str, str]], str | None]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    new_log = not log_path.exists()
    renamed: list[tuple[str, str]] = []
    with open(log_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if new_log:
            w.writeheader()
        for s in steps:
            now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
            action, src, dst = s["action"], s["src"], s["dst"]
            if action == "mkdir":
                target = root / dst
                parent = target.parent
                while not os.path.lexists(parent) and parent != parent.parent:
                    parent = parent.parent
                if not within(Path(os.path.realpath(root)), Path(os.path.realpath(parent))):
                    return renamed, f"step {s['step']} (mkdir {dst}): resolves outside the project root"
                target.mkdir(parents=True, exist_ok=True)
                w.writerow({"timestamp": now, "run_id": run_id, "step": s["step"],
                            "action": "mkdir", "src": "", "dst": dst, "size_bytes": "",
                            "sha256": "", "reason": s["reason"], "status": "done"})
                continue
            members = expand(root, src, s["kind"])
            meta = {}
            for m in members:
                p = root / m
                try:
                    size = os.lstat(p).st_size
                except OSError:
                    size = ""
                meta[m] = (size, sha256(p, hash_max_mb) if action != "delete_junk" else "")
            status = "done"
            root_real = Path(os.path.realpath(root))
            try:
                if not within(root_real, Path(os.path.realpath((root / src).parent))):
                    raise OSError("source now resolves outside the project root")
                if action == "delete_junk":
                    target = root / src
                    if target.is_symlink() or not target.is_dir():
                        target.unlink()
                    else:
                        if any(q.is_symlink() or (q.is_file() and q.suffix.lower() not in JUNK_EXTS)
                               for q in target.rglob("*")):
                            raise OSError(f"{src} now holds something other than bytecode")
                        shutil.rmtree(target)
                else:
                    if os.path.lexists(root / dst):
                        raise OSError(f"destination exists, refusing to overwrite: {dst}")
                    (root / dst).parent.mkdir(parents=True, exist_ok=True)
                    if not within(root_real, Path(os.path.realpath((root / dst).parent))):
                        raise OSError("destination now resolves outside the project root")
                    if use_git and git_tracked(root, src):
                        subprocess.run(["git", "-C", str(root), "mv", src, dst], check=True,
                                       capture_output=True, text=True)
                    else:
                        try:
                            os.rename(root / src, root / dst)
                        except OSError:
                            shutil.move(str(root / src), str(root / dst))
                    renamed.append((src, dst))
            except (OSError, subprocess.CalledProcessError) as exc:
                status = f"failed: {exc}"
            for m in members:
                size, digest = meta[m]
                w.writerow({
                    "timestamp": now, "run_id": run_id, "step": s["step"],
                    "action": action, "src": m,
                    "dst": "" if action == "delete_junk" else dst + m[len(src):],
                    "size_bytes": size, "sha256": digest, "reason": s["reason"],
                    "status": status,
                })
            fh.flush()
            if status != "done":
                return renamed, f"step {s['step']} ({action} {src} -> {dst}): {status}"
    return renamed, None


def stale_references(root: Path, renamed: list[tuple[str, str]]) -> list[str]:
    """Active text files that still mention a moved path (or a renamed basename)."""
    needles: list[str] = []
    for src, dst in renamed:
        needles.append(r"(?<![\w.-])" + re.escape(src) + r"(?![\w-])")
        parts = PurePosixPath(src).parts
        if len(parts) > 1:  # here("a", "b.R") / file.path("a", "b.R") styles
            needles.append(r"""["']\s*[,/]\s*["']""".join(re.escape(x) for x in parts))
        sb, db = PurePosixPath(src).name, PurePosixPath(dst).name
        if sb != db and "." in sb:
            needles.append(r"(?<![\w.-])" + re.escape(sb) + r"(?![\w-])")
        ss, ds = PurePosixPath(src).stem, PurePosixPath(dst).stem
        if src.endswith(".py") and ss != ds:  # python module renamed: imports break
            needles.append(r"\b(?:from|import)\s+(?:[\w.]+\.)?" + re.escape(ss) + r"\b")
    if not needles:
        return []
    pattern = re.compile("|".join(sorted(set(needles), key=len, reverse=True)))
    hits = []
    for dirpath, dirnames, files in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        dirnames[:] = [d for d in dirnames if d not in SKIP_SCAN_DIRS
                       and not ARCHIVE_DIR_RE.match(d)]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if (ext not in TEXT_EXTS and f not in TEXT_NAMES) or f.upper() == "CHANGELOG.MD":
                continue
            p = Path(dirpath) / f
            try:
                if os.stat(p).st_size > 2_000_000:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), start=1):
                found = sorted({m.group(0) for m in pattern.finditer(line)})
                if found:
                    rel = f if rel_dir == "." else f"{rel_dir}/{f}"
                    hits.append(f"{rel}:{n}: mentions " + ", ".join(f"`{x}`" for x in found))
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--log", default=None, help="default: <root>/archive/file_moves.csv")
    ap.add_argument("--raw", action="append", default=[],
                    help="extra raw-data location to protect (repeatable), for raw data that is "
                         "not under a folder named raw/raw_data/...; locations declared at "
                         "`audit_workspace.py open` (_audit/raw_paths.txt) apply automatically")
    ap.add_argument("--apply", action="store_true", help="execute (default is a dry run)")
    ap.add_argument("--allow-raw-moves", action="store_true")
    ap.add_argument("--no-git", action="store_true", help="plain renames even in a git repo")
    ap.add_argument("--hash-max-mb", type=float, default=200)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    log_path = Path(args.log).absolute() if args.log else root / "archive" / "file_moves.csv"
    try:
        log_rel = Path(os.path.realpath(log_path)).relative_to(Path(os.path.realpath(root))).as_posix()
    except ValueError:
        log_rel = None
        if not args.log:
            print("error: archive/file_moves.csv resolves outside the project (is archive/ a link?); "
                  "fix it, or pass --log explicitly.", file=sys.stderr)
            return 2
    if os.path.islink(log_path) or (log_path.exists() and (not log_path.is_file()
                                                           or os.stat(log_path).st_nlink > 1)):
        print("error: the move log is a link, not a file, or hard-linked elsewhere; fix it first.",
              file=sys.stderr)
        return 2
    try:
        raw_locations = rawpaths.declared(root, args.raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        steps, errors = validate(root, read_plan(Path(args.plan)), args.allow_raw_moves, log_rel,
                                 raw_locations)
    except PlanError as exc:
        print("Plan rejected; nothing was changed.\n" + str(exc), file=sys.stderr)
        return 2

    ok = [s for s in steps if not s["error"]]
    n_files = sum(len(expand(root, s["src"], s["kind"])) if s["src"] else 0 for s in ok)
    print(f"{len(ok)} of {len(steps)} steps valid ({n_files} files affected).")
    for s in steps:
        arrow = f"{s['src']} -> {s['dst']}" if s["src"] and s["dst"] else (s["src"] or s["dst"])
        flag = "ERROR " if s["error"] else ""
        print(f"  {s['step']:>3}. {flag}{s['action']:<11} {arrow}   # {s['reason']}")
        if s["error"]:
            print(f"        -> {s['error']}")
    warnings = depth_warnings(root, ok)
    moved_pairs = [(s["src"], s["dst"]) for s in ok if s["action"] in {"move", "rename", "archive"}]
    if not args.apply:
        refs = stale_references(root, moved_pairs)
        if refs:
            print(f"\n{len(refs)} lines in active files mention paths this plan moves; after applying, update:")
            for h in refs[:100]:
                print("  " + h)
            if len(refs) > 100:
                print(f"  ...and {len(refs) - 100} more")
        if warnings:
            print("\nMoved code that will look for files in the wrong place:")
            for w in warnings:
                print("  " + w)
        if errors:
            print(f"\n{len(errors)} step(s) rejected. Fix them before applying; nothing was changed.",
                  file=sys.stderr)
            return 2
        print("\nDry run only. Re-run with --apply to execute.")
        return 0
    if errors:
        print("Plan rejected; nothing was changed.\n" + "\n".join(errors), file=sys.stderr)
        return 2

    use_git = in_git_repo(root) and not args.no_git
    run_id = dt.datetime.now().strftime("reorg-%Y%m%dT%H%M%S")
    renamed, failure = apply(root, ok, log_path, run_id, use_git, args.hash_max_mb)
    if failure:
        print(f"\nINCOMPLETE: {failure}\nSteps before it were applied and logged in {log_path}; "
              "nothing after it ran. Fix the cause, then write a plan for the remaining steps.",
              file=sys.stderr)
    else:
        print(f"\nApplied. Log: {log_path} (run {run_id}).")
    hits = stale_references(root, renamed)
    if hits:
        print(f"\n{len(hits)} lines in active files still mention old paths; update them:")
        for h in hits[:200]:
            print("  " + h)
        if len(hits) > 200:
            print(f"  ...and {len(hits) - 200} more")
    else:
        print("No active code or docs mention the old paths.")
    if warnings:
        print("\nMoved code that will look for files in the wrong place; update its root path:")
        for w in warnings:
            print("  " + w)
    return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
