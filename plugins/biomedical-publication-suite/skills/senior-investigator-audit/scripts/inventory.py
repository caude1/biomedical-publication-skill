#!/usr/bin/env python3
"""Inventory a research project, and prove nothing was lost after reorganizing it.

  scan    Walk the project and write a manifest CSV plus a Markdown summary of
          cleanup signals: legacy/versioned names, duplicates, orphaned code,
          outputs no code mentions, code that points at missing or archived
          files, absolute paths, unseeded randomness, notes left by earlier
          agents, and entry-point candidates.

  verify  Reconcile a "before" manifest against an "after" manifest using the
          move log written by safe_move.py. Every original file must still
          exist, be accounted for by a logged move, or be logged junk. Raw data
          and already-archived files must be byte-identical; other files whose
          content changed are listed for confirmation as intended edits.
          PASS (exit 0), FAIL (exit 1), or UNVERIFIED (exit 3) when some raw
          file has no hash on one side, so its identity is not proven.

Standard library only. The signals are heuristics that point at candidates;
confirm each one before acting on it.

Examples
  python3 inventory.py scan --root . --label before
  python3 inventory.py scan --root . --label after
  python3 inventory.py verify --before _audit/inventory/manifest_before.csv \
      --after _audit/inventory/manifest_after.csv --moves archive/file_moves.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rawpaths  # noqa: E402  one definition of raw data for every script

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Regenerable environments and tool state: never inventoried, never moved.
ENV_DIR_NAMES = {
    "_audit",   # the audit workspace is never part of the project's inventory
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    ".ipynb_checkpoints", ".Rproj.user", ".quarto", ".tectonic_home",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".idea",
    "site-packages", ".Trash", ".cache", ".virtual_documents",
}
ENV_PATH_PREFIXES = ("renv/library", "renv/staging", "renv/local", "renv/python",
                     "renv/sandbox")

JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".localized", "Icon\r"}
JUNK_PREFIXES = ("~$", ".~lock.")
JUNK_EXTS = {".pyc", ".pyo"}

ARCHIVE_DIR_RE = re.compile(
    r"^_*(archives?|archived|old|older|deprecated|legacy|attic|graveyard|trash|"
    r"backups?|bak|obsolete|superseded|retired|unused)$", re.I)
AGENT_DIR_RE = re.compile(
    r"^(_+(cc|gpt|claude|codex|gemini|cursor|copilot|llm[\w-]*|agents?)|"
    r"manuscript-council|\.claude|\.codex|\.cursor|\.gemini)$", re.I)
AGENT_CONFIG_NAMES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules",
                      "copilot-instructions.md"}
AGENT_NOTE_RE = re.compile(
    r"(handoff|hand_off|progress|final_report|agent_log|iteration_log|session|"
    r"delta|open_items|todo|next_steps|status|notes?)", re.I)

DATA_EXTS = {
    ".csv", ".tsv", ".tab", ".dat", ".xlsx", ".xls", ".xlsm", ".parquet",
    ".feather", ".arrow", ".rds", ".rda", ".rdata", ".sav", ".dta", ".sas7bdat",
    ".xpt", ".por", ".h5", ".hdf5", ".h5ad", ".loom", ".npz", ".npy", ".pkl",
    ".pickle", ".joblib", ".fst", ".qs", ".db", ".sqlite", ".sqlite3",
    ".duckdb", ".mat", ".nc", ".vcf", ".bam", ".fastq", ".fq", ".gz", ".zip",
    ".bz2", ".xz", ".7z", ".tar", ".mtx", ".edf", ".bdf", ".nii", ".dcm",
    ".jsonl", ".ndjson",
}
CODE_EXTS = {
    ".r", ".py", ".rmd", ".qmd", ".ipynb", ".sh", ".bash", ".zsh", ".sql",
    ".do", ".ado", ".sas", ".jl", ".m", ".js", ".ts", ".pl", ".smk", ".stan",
    ".cpp", ".c", ".f90", ".nf", ".wdl", ".cwl", ".mk",
}
CODE_NAMES = {"Makefile", "makefile", "GNUmakefile", "Snakefile", "Dockerfile",
              "Justfile", "justfile", "Rakefile"}
ENV_SPEC_NAMES = {"renv.lock", "environment.yml", "environment.yaml",
                  "pyproject.toml", "setup.py", "setup.cfg", "Pipfile",
                  "Pipfile.lock", "poetry.lock", "uv.lock", "DESCRIPTION",
                  "conda-lock.yml", ".Rprofile"}
FIGURE_EXTS = {".png", ".pdf", ".svg", ".jpg", ".jpeg", ".tif", ".tiff", ".eps",
               ".gif", ".bmp", ".webp"}
DOC_EXTS = {".md", ".txt", ".html", ".htm", ".docx", ".doc", ".pptx", ".ppt",
            ".rtf", ".odt", ".tex", ".bib", ".yaml", ".yml", ".json", ".toml",
            ".cfg", ".ini", ".log", ".xml"}
TEXT_SCAN_EXTS = (CODE_EXTS | {".md", ".txt", ".yaml", ".yml", ".json", ".toml",
                               ".cfg", ".ini", ".tex", ".html", ".htm", ".xml"})

OUTPUT_DIR_NAMES = {"results", "result", "outputs", "output", "out", "figures",
                    "figs", "fig", "tables", "plots", "reports", "report"}
MANUSCRIPT_DIR_NAMES = {"manuscript", "manuscripts", "paper", "papers",
                        "submission", "submissions", "publication",
                        "publications", "manuscript_package",
                        "submission_package", "abstract", "abstracts", "ppt",
                        "slides", "poster", "posters", "presentation",
                        "presentations"}
RAW_DIR_NAMES = rawpaths.ALL_RAW_NAMES
DERIVED_DIR_NAMES = {"processed", "interim", "intermediate", "derived", "clean",
                     "cleaned", "cache", "cached", "analysisdata",
                     "analysis_data", "tmp", "temp"}

# Files named by history rather than content (see references/repository.md naming rules).
LEGACY_TOKEN_RE = re.compile(
    r"(?:^|[_\-. ])(v\d+[a-z]?|ver\d+|version\d+|final(?:ized|ize|s)?|old|older|new|"
    r"updated?|revised?|rev\d+|copy|backup|bak|tmp|temp|scratch|rescue|gate|"
    r"delta|prepolish|debug|wip|fixed|redo|retry|draft\d*|orig|test)"
    r"(?=$|[_\-. ])", re.I)
DATE_NAME_RE = re.compile(
    r"(?:^|[_\-. ])((?:19|20)\d{2}[-_.]?(?:0[1-9]|1[0-2])[-_.]?(?:0[1-9]|[12]\d|3[01])"
    r"|(?:0[1-9]|1[0-2])[-_.](?:0[1-9]|[12]\d|3[01])[-_.](?:19|20)?\d{2})"
    r"(?=$|[_\-. ])")
FINDER_DUP_RE = re.compile(r"(\scopy(\s\d+)?|\s\(\d+\))$|^copy of\s", re.I)

ENTRYPOINT_RE = re.compile(
    r"^(pipeline|main|run_all|runall|run|master|make_all|build_all|_targets|"
    r"reproduce|replicate)\.(r|py|qmd|rmd|sh|ipynb)$", re.I)

WRITE_RE = re.compile(
    r"(write\.csv|write_csv|write_tsv|write_delim|write\.table|fwrite|"
    r"write_parquet|write_feather|write_xlsx|write\.xlsx|saveWorkbook|saveRDS|"
    r"save\(|ggsave|pdf\(|png\(|jpeg\(|tiff\(|svg\(|cairo_pdf|dev\.print|"
    r"writeLines|sink\(|cat\([^)]*file\s*=|to_csv|to_parquet|to_excel|"
    r"to_feather|to_pickle|to_json|savefig|\.save\(|np\.save|joblib\.dump|"
    r"pickle\.dump|json\.dump|open\([^)]*['\"]w|gtsave|save_as_docx|"
    r"flextable::save|kableExtra::save_kable|htmlwidgets::saveWidget|"
    r"export\()", re.I)
ABS_PATH_RE = re.compile(
    r"(?<![\w/])(/Users/|/home/|/Volumes/|/mnt/|[A-Za-z]:\\\\|"
    r"~/(Desktop|Documents|Downloads|Library|Dropbox|OneDrive))")
SETWD_RE = re.compile(r"\bsetwd\s*\(|\bos\.chdir\s*\(")
RMLS_RE = re.compile(r"rm\s*\(\s*list\s*=\s*ls\s*\(")
INSTALL_RE = re.compile(r"\binstall\.packages\s*\(|pip install|BiocManager::install")
RANDOM_RE = re.compile(
    r"\b(sample|rnorm|runif|rbinom|rpois|boot|bootstrap|createDataPartition|"
    r"initial_split|vfold_cv|train_test_split|KFold|StratifiedKFold|"
    r"RandomForest\w*|randomForest|ranger|GradientBoosting\w*|xgb\.train|"
    r"XGB\w*|LGBM\w*|np\.random\.\w+|random\.(choice|shuffle|sample)|shuffle|"
    r"permutation|mice|missForest|kmeans|umap|Rtsne|TSNE|cv\.glmnet)\s*\(")
SEED_RE = re.compile(
    r"(set\.seed|np\.random\.seed|random\.seed|random_state\s*=|seed\s*(?::\s*\w+\s*)?=|"
    r"default_rng\(\s*\w|RandomState\(\s*\w|random\.Random\(\s*\w|manual_seed|set_seed|"
    r"with_seed|future\.seed|RNGkind)")
RAW_PATH_RE = re.compile(
    r"data[\\/\"',\s]+raw\b|\braw_(?:dir|path|data|data_dir|folder)\b|[\"']raw[\"']", re.I)
RAW_CONST_RE = re.compile(r"\bRAW(?:_[A-Z0-9_]+)?\b")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+([\w., ]+)|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))")
R_SOURCE_DIR_RE = re.compile(
    r"(?:list\.files|dir|tar_source|sourceDir|source_dir)\s*\(\s*(?:path\s*=\s*)?"
    r"(?:here::here\(|here\(|file\.path\()?\s*[\"']([^\"']+)[\"']")
TAR_SOURCE_BARE_RE = re.compile(r"tar_source\s*\(\s*\)")
RUN_CMD_RE = re.compile(
    r"(?:Rscript(?:\s+--\w+)*|python3?|bash|sh|quarto\s+render|jupyter\s+nbconvert[^\n]*?|"
    r"snakemake\s+-s|make\s+-f)\s+[\"']?([\w./\-]+\.(?:R|r|py|sh|qmd|Rmd|ipynb|smk|mk))")
PLACEHOLDER_NAMES = {".gitkeep", ".keep", ".gitignore", ".placeholder"}

REF_EXTS = sorted({e.lstrip(".") for e in
                   DATA_EXTS | CODE_EXTS | FIGURE_EXTS | DOC_EXTS} | {"rproj"},
                  key=len, reverse=True)
FILE_TOKEN_RE = re.compile(
    r"[\w\-./\\~+@]*?[\w\-+@]\.(?:" + "|".join(re.escape(e) for e in REF_EXTS) +
    r")(?![\w]|\.\w|\s*\()", re.I)

SF_DATALESS = 0x40000000  # macOS: evicted iCloud/File Provider placeholder
MAX_SCAN_BYTES = 2_000_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_dataless(st: os.stat_result) -> bool:
    return bool(getattr(st, "st_flags", 0) & SF_DATALESS)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def ext_of(name: str) -> str:
    lower = name.lower()
    for double in (".tar.gz", ".csv.gz", ".tsv.gz", ".txt.gz", ".vcf.gz"):
        if lower.endswith(double):
            return ".gz"
    return os.path.splitext(lower)[1]


def is_junk(name: str) -> bool:
    return (name in JUNK_NAMES or name.startswith(JUNK_PREFIXES)
            or ext_of(name) in JUNK_EXTS)


def is_env_dir(rel_dir: str, name: str, abs_dir: Path) -> bool:
    if name in ENV_DIR_NAMES:
        return True
    if any(rel_dir == p or rel_dir.startswith(p + "/") for p in ENV_PATH_PREFIXES):
        return True
    return (abs_dir / "pyvenv.cfg").exists()


DATA_ISH = {"data", "inputs", "input", "sources", "dataset", "datasets"}
EXTRA_RAW: list[str] = []          # set from --raw


def in_raw_location(rel: str) -> bool:
    """Raw data by the shared definition (rawpaths.py), whatever the file type."""
    return rawpaths.is_raw(rel, EXTRA_RAW)


def classify(rel: str) -> str:
    parts = rel.split("/")
    name = parts[-1]
    dirs = [p.lower() for p in parts[:-1]]
    ext = ext_of(name)
    if is_junk(name):
        return "junk"
    if any(ARCHIVE_DIR_RE.match(p) for p in parts[:-1]):
        return "archive"
    if in_raw_location(rel):
        return "raw_data"
    if any(AGENT_DIR_RE.match(p) for p in parts[:-1]):
        return "agent_workspace"
    if name in AGENT_CONFIG_NAMES:
        return "agent_config"
    if (name in ENV_SPEC_NAMES or re.match(r"requirements.*\.txt$", name, re.I)
            or name.lower().endswith(".rproj") or rel.startswith("renv/")):
        return "env_spec"
    if ext in CODE_EXTS or name in CODE_NAMES:
        return "code"
    if ext in DATA_EXTS:
        if any(p in DERIVED_DIR_NAMES for p in dirs):
            return "derived_data"
        if any(p in OUTPUT_DIR_NAMES for p in dirs):
            return "output"
        if any(p in MANUSCRIPT_DIR_NAMES for p in dirs):
            return "manuscript"
        return "data_unclassified"
    if any(p in OUTPUT_DIR_NAMES for p in dirs):
        return "output"
    if any(p in MANUSCRIPT_DIR_NAMES for p in dirs):
        return "manuscript"
    if ext in FIGURE_EXTS:
        return "output"
    if ext in DOC_EXTS:
        return "docs"
    return "other"


def legacy_flags(rel: str, category: str) -> list[str]:
    parts = rel.split("/")
    stem = os.path.splitext(parts[-1])[0]
    in_tests = any(p.lower() in {"tests", "test", "testthat"} for p in parts[:-1])
    flags = []
    for m in LEGACY_TOKEN_RE.finditer(stem):
        token = m.group(1).lower()
        if token == "test" and (in_tests or category != "code"):
            continue
        flags.append(f"legacy_name:{token}")
    if DATE_NAME_RE.search(stem):
        flags.append("dated_name")
    if FINDER_DUP_RE.search(stem):
        flags.append("finder_duplicate")
    return sorted(set(flags))


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_SCAN_BYTES:
            return None
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    if b"\x00" in raw[:4096]:
        return None
    return raw.decode("utf-8", errors="replace")


def string_literals(text: str) -> list[str]:
    """Quoted strings in R/Python/shell code, skipping # comments."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "\"'":
            j = i + 1
            buf = []
            while j < n and text[j] != c and text[j] != "\n":
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                buf.append(text[j])
                j += 1
            if 4 <= len(buf) <= 80:
                out.append("".join(buf))
            i = j + 1
            continue
        i += 1
    return out


def norm_token(tok: str) -> str:
    tok = tok.replace("\\", "/").strip("'\"`()[]{},;:<>")
    while tok.startswith("./"):
        tok = tok[2:]
    return tok


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

def walk_project(root: Path):
    """Yield (rel_path, abs_path, lstat) for files; collect pruned env dirs."""
    pruned: dict[str, int] = {}
    files = []
    dirs: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        abs_dir = Path(dirpath)
        rel_dir = abs_dir.relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        keep = []
        for d in sorted(dirnames):
            rel_d = f"{rel_dir}/{d}" if rel_dir else d
            if is_env_dir(rel_d, d, abs_dir / d):
                count = sum(len(fs) for _, _, fs in os.walk(abs_dir / d))
                pruned[rel_d] = count
            else:
                keep.append(d)
                dirs.append(rel_d)
        dirnames[:] = keep
        for f in sorted(filenames):
            p = abs_dir / f
            rel = f"{rel_dir}/{f}" if rel_dir else f
            try:
                st = os.lstat(p)
            except OSError:
                continue
            files.append((rel, p, st))
    return files, pruned, dirs


def cmd_scan(args) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "_audit" / "inventory"
    try:
        EXTRA_RAW[:] = rawpaths.declared(root, args.raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    label = args.label
    started = dt.datetime.now(dt.timezone.utc)

    files, pruned, dirs = walk_project(root)
    rows: dict[str, dict] = {}
    for rel, p, st in files:
        symlink = os.path.islink(p)
        cat = classify(rel)
        if symlink and cat not in {"raw_data", "archive"}:
            cat = "symlink"
        rows[rel] = {
            "link_target": os.readlink(p) if symlink else "",
            "path": rel,
            "category": cat,
            "size_bytes": st.st_size,
            "mtime_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc)
                           .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "_mtime": st.st_mtime,
            "ext": ext_of(rel.split("/")[-1]),
            "dataless": int(is_dataless(st)),
            "sha256": "",
            "refs_active": 0,
            "refs_inactive": 0,
            "produced_by": "",
            "flags": [],
        }

    # Index basenames and path suffixes for reference resolution.
    by_base: dict[str, list[str]] = defaultdict(list)
    for rel in rows:
        by_base[rel.split("/")[-1].lower()].append(rel)

    def resolve(token: str) -> list[str]:
        tok = norm_token(token)
        base = tok.split("/")[-1].lower()
        cands = by_base.get(base, [])
        if "/" in tok and len(cands) > 1:
            suffix = re.sub(r"^(?:\.{1,2}/|~/|/)+", "", tok.lower())
            narrowed = [c for c in cands if c.lower().endswith(suffix)]
            if narrowed:
                return narrowed
        return cands

    # Content scan: references, producers, code hygiene. Archived files and
    # earlier agents' workspaces are "inactive": they never make a file live.
    inactive_cats = {"archive", "agent_workspace"}
    referencers_active: dict[str, set[str]] = defaultdict(set)
    referencers_inactive: dict[str, set[str]] = defaultdict(set)
    producers: dict[str, set[str]] = defaultdict(set)
    declared_outputs: set[str] = set()
    missing_by_file: dict[str, set[str]] = defaultdict(set)
    fragments: dict[str, set[str]] = defaultdict(set)
    code_targets: dict[str, set[str]] = defaultdict(set)

    to_scan = []
    for rel, row in rows.items():
        cat = row["category"]
        name = rel.split("/")[-1]
        if cat in {"junk", "symlink"}:
            continue
        if not (row["ext"] in TEXT_SCAN_EXTS or name in CODE_NAMES or cat == "agent_config"):
            continue
        if cat in inactive_cats and not args.scan_archive:
            continue
        if row["dataless"] and args.no_download:
            continue
        to_scan.append(rel)

    def process(rel: str, text: str) -> None:
        row = rows[rel]
        name = rel.split("/")[-1]
        inactive = row["category"] in inactive_cats
        refs = referencers_inactive if inactive else referencers_active
        is_code = row["ext"] in CODE_EXTS or name in CODE_NAMES
        clean = URL_RE.sub(" ", text)
        lines = clean.splitlines()
        write_window = 0
        missing: list[str] = []
        to_archive: list[str] = []
        writes_raw = False
        for line in lines:
            if is_code and WRITE_RE.search(line):
                write_window = 4
            if is_code and not inactive and write_window > 0 and (
                    RAW_PATH_RE.search(line) or RAW_CONST_RE.search(line)):
                writes_raw = True
            for m in FILE_TOKEN_RE.finditer(line):
                tok = m.group(0)
                prev = line[m.start() - 1] if m.start() > 0 else ""
                base = norm_token(tok).split("/")[-1]
                stem = os.path.splitext(base)[0]
                if prev and prev in "%{}$" or len(stem.strip("._-")) <= 1:
                    continue  # template pieces such as "%s.rds" or "{x}.csv"
                if is_code and not inactive and write_window > 0 and base:
                    declared_outputs.add(base.lower())
                targets = [t for t in resolve(tok) if t != rel]
                if not targets:
                    if is_code and not inactive and base and base.lower() not in by_base:
                        missing.append(base)
                    continue
                if is_code and not inactive and all(
                        rows[t]["category"] in inactive_cats for t in targets):
                    to_archive.append(base)
                if is_code and not inactive and write_window > 0 and any(
                        rows[t]["category"] == "raw_data" for t in targets):
                    writes_raw = True
                for t in targets:
                    refs[t].add(rel)
                    if is_code and not inactive:
                        if rows[t]["category"] == "code":
                            code_targets[rel].add(t)
                        if write_window > 0:
                            producers[t].add(rel)
            if write_window > 0:
                write_window -= 1
        if not is_code:
            return
        if not inactive:
            # Literal pieces of names built at runtime: paste0("mdi_table1_", x, ".csv").
            for lit in string_literals(clean):
                lit = lit.strip().lower().replace("\\", "/").split("/")[-1]
                if (4 <= len(lit) <= 80 and re.fullmatch(r"[\w.\-]+", lit)
                        and re.search(r"[_\-]", lit)
                        and len(re.sub(r"[^a-z0-9]", "", lit)) >= 3):
                    fragments[lit].add(rel)
        implied: set[str] = set()
        if row["ext"] == ".py":
            for line in lines:
                m = PY_IMPORT_RE.match(line)
                if not m:
                    continue
                mods = []
                if m.group(1) is not None:
                    base = m.group(1).lstrip(".")
                    if base:
                        mods.append(base)
                    mods += [n.strip() for n in m.group(2).split(",")]
                else:
                    mods += [n.strip() for n in m.group(3).split(",")]
                for mod in mods:
                    seg = [x for x in mod.split(".") if x]
                    if seg:
                        implied.add(seg[-1] + ".py")
                        implied.add("/".join(seg) + ".py")
        dirs_sourced = list(R_SOURCE_DIR_RE.findall(text))
        if TAR_SOURCE_BARE_RE.search(text):
            dirs_sourced.append("R")
        for d in dirs_sourced:
            d = norm_token(d).strip("/")
            for other, orow in rows.items():
                if other != rel and orow["category"] == "code" and (
                        other.startswith(d + "/") or
                        other.startswith(str(Path(rel).parent / d) + "/")):
                    implied.add(other)
        for tok in implied:
            for t in resolve(tok):
                if t != rel:
                    refs[t].add(rel)
                    if not inactive and rows[t]["category"] == "code":
                        code_targets[rel].add(t)
        if inactive:
            return
        if writes_raw:
            row["flags"].append("writes_raw")
        if ABS_PATH_RE.search(text):
            row["flags"].append("abs_path")
        if SETWD_RE.search(text):
            row["flags"].append("setwd_or_chdir")
        if RMLS_RE.search(text):
            row["flags"].append("rm_list_ls")
        if INSTALL_RE.search(text):
            row["flags"].append("installs_packages")
        if RANDOM_RE.search(text) and not SEED_RE.search(text):
            row["flags"].append("random_without_seed")
        if missing:
            missing_by_file[rel].update(missing)
        if to_archive:
            uniq = sorted(set(to_archive))
            row["flags"].append("ref_to_archive:" + "|".join(uniq[:5]))

    # Reading an evicted cloud file downloads it, so read in parallel, in chunks.
    scanned = downloaded = 0
    chunk = 400
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for i in range(0, len(to_scan), chunk):
            part = to_scan[i:i + chunk]
            for rel, text in zip(part, pool.map(lambda r: read_text(root / r), part)):
                if text is None:
                    continue
                scanned += 1
                downloaded += rows[rel]["dataless"]
                process(rel, text)

    for rel, miss in missing_by_file.items():
        truly = sorted(b for b in miss if b.lower() not in declared_outputs)
        ungenerated = sorted(b for b in miss if b.lower() in declared_outputs)
        if truly:
            rows[rel]["flags"].append("missing_ref:" + "|".join(truly[:5]) +
                                      (f"|+{len(truly) - 5}" if len(truly) > 5 else ""))
        if ungenerated:
            rows[rel]["flags"].append("ungenerated:" + "|".join(ungenerated[:5]) +
                                      (f"|+{len(ungenerated) - 5}" if len(ungenerated) > 5 else ""))
    for rel, row in rows.items():
        row["refs_active"] = len(referencers_active.get(rel, ()))
        row["refs_inactive"] = (len(referencers_inactive.get(rel, ()))
                                if args.scan_archive else "")
        row["produced_by"] = "|".join(sorted(producers.get(rel, ()))[:3])

    # Scripts that a README tells people to run are entry points.
    documented: set[str] = set()
    for rel, row in rows.items():
        name = rel.split("/")[-1]
        if not name.lower().startswith("readme") or row["category"] in inactive_cats:
            continue
        text = read_text(root / rel) or ""
        for m in RUN_CMD_RE.finditer(text):
            for t in resolve(m.group(1)):
                if rows[t]["category"] == "code":
                    documented.add(t)

    # Naming, size, role flags.
    skip_name_flags = {"junk", "archive", "symlink", "agent_workspace"}
    code_referenced_by_code = {t for targets in code_targets.values() for t in targets}
    for rel, row in rows.items():
        cat = row["category"]
        name = rel.split("/")[-1]
        stem = os.path.splitext(name)[0]
        if cat not in skip_name_flags:
            row["flags"].extend(legacy_flags(rel, cat))
        if row["size_bytes"] == 0 and cat not in {"junk", "symlink"} \
                and name not in PLACEHOLDER_NAMES:
            row["flags"].append("empty")
        if row["size_bytes"] > args.large_mb * 1_000_000:
            row["flags"].append("large")
        is_named_entry = (cat == "code" and ENTRYPOINT_RE.match(name)) or name in {
            "Makefile", "Snakefile", "_targets.R", "Justfile"}
        is_driver = (cat == "code" and len(code_targets.get(rel, ())) >= 3
                     and rel not in code_referenced_by_code)
        if is_named_entry or is_driver or rel in documented:
            row["flags"].append("entrypoint")
        if cat == "agent_config" or (
                row["ext"] in {".md", ".txt"} and (
                    cat == "agent_workspace" or
                    (cat == "docs" and AGENT_NOTE_RE.search(stem)))):
            row["flags"].append("agent_note")

    def fragment_producers(base: str) -> set[str]:
        b = base.lower()
        hits: set[str] = set()
        for i in range(4, len(b) + 1):
            hits |= fragments.get(b[:i], set())
        for i in range(1, max(1, len(b) - 3)):
            hits |= fragments.get(b[i:], set())
        return hits

    code_referencers = {
        rel: {r for r in refs if rows[r]["category"] == "code"}
        for rel, refs in referencers_active.items()
    }
    for rel, row in rows.items():
        cat = row["category"]
        name = rel.split("/")[-1]
        parts_lower = [p.lower() for p in rel.split("/")[:-1]]
        if cat == "code" and "entrypoint" not in row["flags"]:
            if row["refs_active"] == 0 and not any(
                    p in {"tests", "test", "testthat", "sandbox"} for p in parts_lower):
                row["flags"].append("unreferenced_code")
            if "sandbox" in parts_lower:
                row["flags"].append("sandbox")
        if cat == "output" and row["ext"] not in {".md", ".txt", ".log"} \
                and name not in PLACEHOLDER_NAMES:
            code_refs = code_referencers.get(rel, set())
            if not code_refs:
                dyn = fragment_producers(name)
                if dyn:
                    row["flags"].append("dynamic_name:" + "|".join(sorted(dyn)[:2]))
                    if not row["produced_by"]:
                        row["produced_by"] = "|".join(sorted(dyn)[:3]) + " (name built at runtime)"
                else:
                    row["flags"].append("untraceable_output")
            else:
                prods = producers.get(rel) or code_refs
                newest = max(rows[c]["_mtime"] for c in prods)
                if newest > row["_mtime"] + 60:
                    row["flags"].append("maybe_stale")

    # Hashing.
    def want_hash(row) -> bool:
        if row["category"] in {"junk"}:
            return False
        if row["link_target"] and not (root / row["path"]).is_file():
            return False          # link to a folder or a missing target: the target path is recorded
        # (a link to a file is hashed through the link, so a retargeted link changes the hash)
        # Raw data is hashed at any size: its hash is the proof it never changed.
        if row["category"] != "raw_data" and row["size_bytes"] > args.hash_max_mb * 1_000_000:
            return False
        if row["dataless"] and not args.hash_dataless:
            return False
        return True

    to_hash: set[str] = set()
    mode = args.hash
    if mode in {"all"}:
        to_hash = {r for r, row in rows.items() if want_hash(row)}
    else:
        if mode in {"dupes", "dupes+raw"}:
            by_size: dict[int, list[str]] = defaultdict(list)
            for r, row in rows.items():
                if row["size_bytes"] > 0 and row["category"] not in {"junk", "symlink"}:
                    by_size[row["size_bytes"]].append(r)
            for group in by_size.values():
                if len(group) > 1:
                    to_hash.update(r for r in group if want_hash(rows[r]))
        if mode in {"raw", "dupes+raw"}:
            to_hash.update(r for r, row in rows.items()
                           if row["category"] == "raw_data" and want_hash(row))
    for r in sorted(to_hash):
        try:
            rows[r]["sha256"] = sha256_file(root / r)
        except OSError as exc:
            rows[r]["flags"].append(f"hash_error:{exc.__class__.__name__}")
    for r, row in rows.items():
        if row["category"] == "raw_data" and not row["sha256"]:
            row["flags"].append("raw_unhashed")

    dup_groups: dict[str, list[str]] = defaultdict(list)
    for r, row in rows.items():
        if row["sha256"]:
            dup_groups[row["sha256"]].append(r)
    dup_groups = {h: sorted(g) for h, g in dup_groups.items() if len(g) > 1}
    for h, group in dup_groups.items():
        for r in group:
            rows[r]["flags"].append(f"duplicate_of:{group[0] if group[0] != r else group[1]}")

    # Write manifest.
    manifest = out_dir / f"manifest_{label}.csv"
    fields = ["path", "category", "size_bytes", "mtime_utc", "ext", "dataless",
              "sha256", "link_target", "refs_active", "refs_inactive", "produced_by", "flags"]
    with open(manifest, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for rel in sorted(rows):
            row = dict(rows[rel])
            row["flags"] = ";".join(sorted(set(row["flags"])))
            w.writerow(row)

    history_dirs = []
    for d in dirs:
        parts = d.split("/")
        if any(ARCHIVE_DIR_RE.match(p) for p in parts[:-1]):
            continue
        name = parts[-1]
        if d.endswith("results/temp") or name.lower() in {"sandbox", "tests", "testthat"}:
            continue
        tokens = [m.group(1).lower() for m in LEGACY_TOKEN_RE.finditer(name)]
        if ARCHIVE_DIR_RE.match(name) or AGENT_DIR_RE.match(name):
            continue
        if tokens or DATE_NAME_RE.search(name) or FINDER_DUP_RE.search(name):
            history_dirs.append((d, tokens or ["date/copy"]))
    same_size_unhashed = 0
    by_size_all: dict[int, list[str]] = defaultdict(list)
    for r, row in rows.items():
        if row["size_bytes"] > 0 and row["category"] not in {"junk", "symlink"}:
            by_size_all[row["size_bytes"]].append(r)
    for group in by_size_all.values():
        if len(group) > 1:
            same_size_unhashed += sum(1 for r in group if not rows[r]["sha256"])

    summary = out_dir / f"inventory_{label}.md"
    write_summary(summary, root, rows, pruned, dup_groups, scanned, downloaded,
                  started, args, history_dirs, same_size_unhashed)
    print(f"manifest: {manifest}")
    print(f"summary:  {summary}")
    print(f"files: {len(rows)}  scanned for references: {scanned}  "
          f"(evicted placeholders read: {downloaded})  hashed: {len(to_hash)}")
    return 0


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def write_summary(path, root, rows, pruned, dup_groups, scanned, downloaded,
                  started, args, history_dirs=(), same_size_unhashed=0):
    cap = args.max_list
    lines: list[str] = []
    add = lines.append
    total = sum(r["size_bytes"] for r in rows.values())
    dataless = sum(r["dataless"] for r in rows.values())
    add(f"# Inventory: {root.name} ({args.label})")
    add("")
    add(f"- Root: `{root}`")
    add(f"- Scanned: {started.strftime('%Y-%m-%d %H:%M UTC')}")
    add(f"- Files: {len(rows):,} ({human(total)}); evicted cloud placeholders: {dataless:,}")
    add(f"- Text files scanned for references: {scanned:,}"
        + ("" if args.scan_archive else " (archive and agent workspaces not scanned)"))
    pruned = {d: n for d, n in pruned.items() if n}
    if pruned:
        env = ", ".join(f"`{d}` ({n:,})" for d, n in sorted(pruned.items()))
        add(f"- Excluded environments/tool state: {env}")
    add("")
    add("Signals below are heuristics. Confirm each before acting.")
    add("")

    # Top-level layout.
    add("## Layout")
    add("")
    add("| Top-level | Files | Size | Main categories |")
    add("|---|---:|---:|---|")
    tops: dict[str, list[dict]] = defaultdict(list)
    for rel, row in rows.items():
        top = rel.split("/")[0] + ("/" if "/" in rel else "")
        tops[top].append(row)
    for top in sorted(tops):
        group = tops[top]
        cats = Counter(r["category"] for r in group).most_common(3)
        add(f"| `{top}` | {len(group):,} | {human(sum(r['size_bytes'] for r in group))} | "
            + ", ".join(f"{c} {n}" for c, n in cats) + " |")
    add("")
    add("## Categories")
    add("")
    for cat, n in Counter(r["category"] for r in rows.values()).most_common():
        add(f"- {cat}: {n:,}")
    add("")

    def section(title, predicate, fmt, note=""):
        hits = [r for r in rows.values() if predicate(r)]
        add(f"## {title} ({len(hits):,})")
        add("")
        if note:
            add(note)
            add("")
        for r in sorted(hits, key=lambda x: x["path"])[:cap]:
            add(fmt(r))
        if len(hits) > cap:
            add(f"- ...and {len(hits) - cap:,} more (see manifest)")
        add("")

    def has(prefix):
        return lambda r: any(f.startswith(prefix) for f in r["flags"])

    def flagval(r, prefix):
        return ", ".join(f.split(":", 1)[1] for f in r["flags"]
                         if f.startswith(prefix + ":"))

    section("Entry-point candidates", has("entrypoint"),
            lambda r: f"- `{r['path']}`",
            "If none exists, the reorganization must create one.")
    section("Code that may write into raw data: check before running anything",
            has("writes_raw"), lambda r: f"- `{r['path']}`",
            "A write call near a raw-data path. If the code overwrites data/raw (for example by "
            "refetching a live source), protect the raw files before any rerun.")
    ws: Counter = Counter()
    for r in rows.values():
        if r["category"] == "agent_workspace":
            parts = r["path"].split("/")
            for i, part in enumerate(parts[:-1]):
                if AGENT_DIR_RE.match(part):
                    ws["/".join(parts[:i + 1]) + "/"] += 1
                    break
    if ws:
        add(f"## Earlier agents' workspaces ({len(ws)})")
        add("")
        add("Read their notes for intent and abandoned directions; nothing active should depend on them.")
        add("")
        for d, n in sorted(ws.items()):
            add(f"- `{d}` ({n:,} files)")
        add("")
    section("Notes and configs left by earlier agents", has("agent_note"),
            lambda r: f"- `{r['path']}` ({r['category']}, {r['mtime_utc'][:10]})",
            "Read these during orientation; they explain intent and prior decisions.")
    section("Data files outside data/raw or data/processed",
            lambda r: r["category"] == "data_unclassified",
            lambda r: f"- `{r['path']}` ({human(r['size_bytes'])})",
            "Decide whether each is raw (immutable, goes to data/raw) or derived.")
    section("Raw data", lambda r: r["category"] == "raw_data",
            lambda r: f"- `{r['path']}` ({human(r['size_bytes'])})"
                      + (" sha256 " + r["sha256"][:12] if r["sha256"] else " (unhashed)"))
    section("Code referring to files that do not exist", has("missing_ref"),
            lambda r: f"- `{r['path']}` -> {flagval(r, 'missing_ref')}",
            "Likely broken scripts, renamed inputs, or dynamically built names.")
    section("Outputs the code writes that do not exist yet", has("ungenerated"),
            lambda r: f"- `{r['path']}` -> {flagval(r, 'ungenerated')}",
            "Expected before a first run; after a full rerun, these point at steps that never ran.")
    section("Active code depending on archived files", has("ref_to_archive"),
            lambda r: f"- `{r['path']}` -> {flagval(r, 'ref_to_archive')}")
    section("Code no other file mentions (orphan candidates)", has("unreferenced_code"),
            lambda r: f"- `{r['path']}` (modified {r['mtime_utc'][:10]})",
            "Not called by the entry point or any script. Archive unless it produces a reported result.")
    n_dyn = sum(1 for r in rows.values() if any(f.startswith("dynamic_name") for f in r["flags"]))
    section("Outputs no active code mentions (untraceable candidates)",
            has("untraceable_output"),
            lambda r: f"- `{r['path']}` (modified {r['mtime_utc'][:10]})",
            "If a reported number or figure comes from one of these, find or rebuild its code."
            + (f" A further {n_dyn:,} outputs match name fragments in active code (names built "
               "at runtime); their likely producers are in the manifest's `produced_by`."
               if n_dyn else ""))
    section("Outputs possibly older than the code that writes them", has("maybe_stale"),
            lambda r: f"- `{r['path']}` (written by {r['produced_by'] or 'referencing code'})")
    section("Hard-coded absolute paths", has("abs_path"),
            lambda r: f"- `{r['path']}`")
    section("setwd / chdir / rm(list = ls()) / install calls",
            lambda r: any(f in r["flags"] for f in
                          ("setwd_or_chdir", "rm_list_ls", "installs_packages")),
            lambda r: f"- `{r['path']}`: " + ", ".join(
                f for f in r["flags"] if f in ("setwd_or_chdir", "rm_list_ls",
                                               "installs_packages")))
    section("Randomness without a visible seed", has("random_without_seed"),
            lambda r: f"- `{r['path']}`")
    add(f"## Folders named by history instead of content ({len(history_dirs):,})")
    add("")
    for d, toks in history_dirs[:cap]:
        add(f"- `{d}/`: {', '.join(toks)}")
    if len(history_dirs) > cap:
        add(f"- ...and {len(history_dirs) - cap:,} more")
    add("")
    section("Names that record history instead of content",
            lambda r: any(f.startswith(("legacy_name", "dated_name", "finder_duplicate"))
                          for f in r["flags"]),
            lambda r: f"- `{r['path']}`: " + ", ".join(
                f.replace("legacy_name:", "") for f in r["flags"]
                if f.startswith(("legacy_name", "dated_name", "finder_duplicate"))))
    add(f"## Identical files ({len(dup_groups):,} groups)")
    add("")
    active_groups = [g for g in dup_groups.values()
                     if any(rows[p]["category"] != "archive" for p in g)]
    for g in sorted(active_groups, key=lambda g: (-len(g), g[0]))[:cap]:
        add(f"- {len(g)} copies ({human(rows[g[0]]['size_bytes'])}): "
            + ", ".join(f"`{p}`" for p in g[:6]) + (" ..." if len(g) > 6 else ""))
    archived_only = len(dup_groups) - len(active_groups)
    if archived_only:
        add(f"- plus {archived_only:,} groups entirely inside archive folders")
    if same_size_unhashed:
        add(f"- {same_size_unhashed:,} same-size files were not hashed (evicted "
            f"placeholders or over the size cap); rerun with --hash-dataless to include them")
    add("")
    section("Empty files", has("empty"), lambda r: f"- `{r['path']}`")
    section("Large files", has("large"),
            lambda r: f"- `{r['path']}` ({human(r['size_bytes'])})")
    section("Junk (safe to delete, log it)", lambda r: r["category"] == "junk",
            lambda r: f"- `{r['path']}`")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def load_manifest(path: str) -> dict[str, dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["path"]: r for r in csv.DictReader(fh)}


def load_moves(path: str | None) -> tuple[dict[str, str], set[str]]:
    moved: dict[str, str] = {}
    deleted: set[str] = set()
    if not path or not os.path.exists(path):
        return moved, deleted
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("status", "done") != "done":
                continue
            action = r.get("action", "")
            src, dst = r.get("src", ""), r.get("dst", "")
            if action == "delete_junk":
                deleted.add(src)
            elif action in {"move", "rename", "archive"} and src and dst:
                moved[src] = dst
    return moved, deleted


def follow(path: str, moved: dict[str, str]) -> str:
    seen = set()
    while path in moved and path not in seen:
        seen.add(path)
        path = moved[path]
    return path


def cmd_verify(args) -> int:
    before = load_manifest(args.before)
    after = load_manifest(args.after)
    moved, deleted = load_moves(args.moves)
    fails, unverified, modified, notes = [], [], [], []
    ok_in_place = ok_moved = ok_deleted = 0
    destinations = set()
    for path, b in sorted(before.items()):
        raw = b["category"] == "raw_data"
        archived = b["category"] == "archive"
        if path in deleted:
            if raw or archived:
                fails.append(f"{'raw data' if raw else 'archived file'} was deleted: `{path}`")
            else:
                ok_deleted += 1
            continue
        final = follow(path, moved)
        if final != path:
            destinations.add(final)
        a = after.get(final)
        if a is None:
            if final != path:
                fails.append(f"logged move lost the file: `{path}` -> `{final}` (not in after)")
            elif b["category"] == "junk":
                notes.append(f"junk file gone without a log entry: `{path}`")
            else:
                fails.append(f"missing and not logged: `{path}`")
            continue
        hb, ha = b.get("sha256", ""), a.get("sha256", "")
        same_size = b["size_bytes"] == a["size_bytes"]
        lb, la = b.get("link_target", ""), a.get("link_target", "")
        if (lb or la) and lb != la:
            identical = False            # a symlink now points somewhere else
        elif hb and ha:
            identical = hb == ha
        else:
            identical = None if same_size else False
        label = "raw data" if raw else ("archived file" if archived else "")
        if raw or archived:
            if identical is False:
                fails.append(f"{label} changed: `{path}`" + (f" (now `{final}`)" if final != path else ""))
            elif identical is None:
                unverified.append(f"{label} checked by size only (no hash on one side): `{path}`")
        elif identical is False:
            modified.append(f"`{final}`" + (f" (moved from `{path}`)" if final != path else ""))
        if final == path:
            ok_in_place += 1
        else:
            ok_moved += 1
    new = sorted(p for p in after if p not in before and p not in destinations)
    new_by_top = Counter(p.split("/")[0] for p in new)
    verdict = "FAIL" if fails else ("UNVERIFIED" if unverified else "PASS")

    lines = ["# Reorganization check", ""]
    lines.append(f"- Before: `{args.before}` ({len(before):,} files)")
    lines.append(f"- After: `{args.after}` ({len(after):,} files)")
    lines.append(f"- Move log: `{args.moves}` ({len(moved):,} moves, {len(deleted):,} junk deletions)")
    lines.append(f"- Result: **{verdict}**. {ok_in_place:,} in place, {ok_moved:,} moved as logged, "
                 f"{ok_deleted:,} logged junk deletions, {len(modified):,} with changed content, "
                 f"{len(new):,} new files.")
    if verdict == "UNVERIFIED":
        lines.append("- UNVERIFIED: some raw or archived files lack a hash on one side (often evicted "
                     "cloud files or files over the size cap). Materialize them and rescan with a larger "
                     "--hash-max-mb, or disclose exactly which files; this is not a pass.")
    lines.append("")
    if fails:
        lines += ["## Failures", ""] + [f"- {f}" for f in fails[:500]] + [""]
    if unverified:
        lines += ["## Identity not verified", ""] + [f"- {u}" for u in unverified[:300]] + [""]
    if modified:
        lines += ["## Content changed (confirm each is an intended edit)", ""]
        lines += [f"- {m}" for m in modified[:300]]
        if len(modified) > 300:
            lines.append(f"- ...and {len(modified) - 300} more")
        lines.append("")
    if notes:
        lines += ["## Notes", ""] + [f"- {n}" for n in notes[:300]] + [""]
    if new:
        lines += ["## New files by top-level folder", ""]
        lines += [f"- `{t}`: {n:,}" for t, n in new_by_top.most_common()]
        lines.append("")
    report = "\n".join(lines) + "\n"
    if args.out_md:
        Path(args.out_md).write_text(report, encoding="utf-8")
        print(f"report: {args.out_md}")
    print(report if not args.out_md else report.split("\n## ")[0])
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 3}[verdict]


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="write manifest + summary")
    s.add_argument("--root", default=".")
    s.add_argument("--label", default="before",
                   help="suffix for output names, e.g. before / after")
    s.add_argument("--out-dir", default=None,
                   help="where to write outputs (default: <root>/_audit/inventory)")
    s.add_argument("--hash", default="all",
                   choices=["none", "dupes", "raw", "dupes+raw", "all"],
                   help="which files to sha256 (default: every local file; raw data at any size, "
                        "other files up to --hash-max-mb)")
    s.add_argument("--hash-max-mb", type=float, default=200,
                   help="size cap for hashing non-raw files (raw data is always hashed)")
    s.add_argument("--hash-dataless", action="store_true",
                   help="also hash evicted cloud placeholders (forces download)")
    s.add_argument("--no-download", action="store_true",
                   help="never read evicted placeholders, even small text files")
    s.add_argument("--scan-archive", action="store_true",
                   help="also read text files in archive/ and earlier agents' workspaces")
    s.add_argument("--workers", type=int, default=16,
                   help="parallel readers (evicted cloud files download on read)")
    s.add_argument("--raw", action="append", default=[],
                   help="extra raw-data location to protect (repeatable), for raw data kept "
                        "outside a folder named raw/raw_data/...; locations declared at "
                        "`audit_workspace.py open` (_audit/raw_paths.txt) apply automatically")
    s.add_argument("--large-mb", type=float, default=100)
    s.add_argument("--max-list", type=int, default=40,
                   help="rows per summary section before truncating")
    s.set_defaults(func=cmd_scan)

    v = sub.add_parser("verify", help="reconcile before/after manifests")
    v.add_argument("--before", required=True)
    v.add_argument("--after", required=True)
    v.add_argument("--moves", default=None, help="file_moves.csv from safe_move.py")
    v.add_argument("--out-md", default=None)
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
