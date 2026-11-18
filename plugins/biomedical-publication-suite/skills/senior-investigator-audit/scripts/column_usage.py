#!/usr/bin/env python3
"""List variables that were collected but never used in the analysis code.

Reads the header of every tabular data file (CSV/TSV always; .xlsx with
openpyxl; .parquet/.feather with pyarrow; .rds/.rda/.RData/.dta/.sav/.sas7bdat
through Rscript when R is installed) and searches the active analysis code
for each column name, raw and in snake_case. With --profile, CSV/TSV columns
also get a non-missing count and number of distinct values, so unused
variables that carry real information stand out.

This is a map of places to look, not a to-do list. An unused variable earns
an analysis only if it answers a question that would change the paper.

Example
  python3 column_usage.py --root . --data data --profile \
      --out-md _audit/runs/unused_variables.md --out-csv _audit/runs/column_usage.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

TABLE_EXTS = {".csv", ".tsv", ".tab", ".txt", ".xlsx", ".parquet", ".feather", ".rds",
              ".rda", ".rdata", ".dta", ".sav", ".sas7bdat", ".gz"}
CODE_EXTS = {".r", ".py", ".rmd", ".qmd", ".ipynb", ".sql", ".sh", ".do", ".sas", ".jl",
             ".stan", ".smk"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "renv", "__pycache__", ".Rproj.user",
             ".ipynb_checkpoints", ".quarto", "_audit"}
ARCHIVE_RE = re.compile(r"^_*(archives?|archived|old|deprecated|legacy|attic|backups?|"
                        r"obsolete|superseded|unused)$", re.I)
WRITE_HINT_RE = re.compile(r"write|save|to_csv|to_parquet|to_excel|export|fwrite", re.I)
NA = {"", "na", "n/a", "nan", "null", "none", ".", "-", "missing", "unknown", "-9", "-99",
      "-999", "999", "9999"}

R_HEADER = r"""
args <- commandArgs(trailingOnly = TRUE); f <- args[1]; ext <- tolower(tools::file_ext(f))
nm <- tryCatch({
  if (ext == "rds") { x <- readRDS(f); if (is.data.frame(x)) names(x) else if (is.list(x)) {
      unlist(lapply(names(x), function(k) if (is.data.frame(x[[k]])) paste0(k, "$", names(x[[k]]))))
    } else character() }
  else if (ext %in% c("rda", "rdata")) { e <- new.env(); load(f, envir = e)
    unlist(lapply(ls(e), function(k) { o <- get(k, e); if (is.data.frame(o)) paste0(k, "$", names(o)) })) }
  else if (ext == "dta") names(haven::read_dta(f, n_max = 0))
  else if (ext == "sav") names(haven::read_sav(f, n_max = 0))
  else if (ext == "sas7bdat") names(haven::read_sas(f, n_max = 0))
  else character()
}, error = function(e) character())
cat(nm, sep = "\n")
"""


def is_archived(rel_parts) -> bool:
    return any(ARCHIVE_RE.match(p) for p in rel_parts)


def snake(name: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s = re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").lower()
    return s


def headers(path: Path, profile: bool, max_rows: int):
    """Return (columns, stats) where stats maps column -> (non_missing, distinct)."""
    ext = path.suffix.lower()
    if ext == ".gz":
        inner = Path(path.stem).suffix.lower()
        if inner not in {".csv", ".tsv"}:
            return None, {}
        import gzip
        opener = lambda: io.TextIOWrapper(gzip.open(path), encoding="utf-8", errors="replace")  # noqa: E731
        delim = "\t" if inner == ".tsv" else ","
        return _delimited(opener, delim, profile, max_rows)
    if ext in {".csv", ".tsv", ".tab", ".txt"}:
        opener = lambda: open(path, encoding="utf-8-sig", errors="replace", newline="")  # noqa: E731
        if ext == ".txt":
            with opener() as fh:
                sample = fh.read(20000)
            try:
                delim = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
            except csv.Error:
                return None, {}
        else:
            delim = "\t" if ext in {".tsv", ".tab"} else ","
        return _delimited(opener, delim, profile, max_rows)
    if ext == ".xlsx":
        try:
            import openpyxl
        except ImportError:
            return None, {"_note": "needs openpyxl"}
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:  # noqa: BLE001
            return None, {}
        cols = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(max_row=1, values_only=True):
                cols += [f"{ws.title}${c}" if len(wb.worksheets) > 1 else str(c)
                         for c in row if c is not None]
        return cols, {}
    if ext in {".parquet", ".feather"}:
        try:
            import pyarrow.parquet as pq
            import pyarrow.feather as pf
        except ImportError:
            return _via_r(path) if ext == ".parquet" else (None, {"_note": "needs pyarrow"})
        try:
            if ext == ".parquet":
                return list(pq.read_schema(path).names), {}
            return list(pf.read_table(path).column_names), {}
        except Exception:  # noqa: BLE001
            return None, {}
    if ext in {".rds", ".rda", ".rdata", ".dta", ".sav", ".sas7bdat"}:
        return _via_r(path)
    return None, {}


def _via_r(path: Path):
    rscript = shutil.which("Rscript")
    if not rscript:
        return None, {"_note": "needs Rscript"}
    try:
        r = subprocess.run([rscript, "--vanilla", "-e", R_HEADER, str(path)],
                           capture_output=True, text=True, timeout=300)
    except (subprocess.TimeoutExpired, OSError):
        return None, {}
    cols = [c for c in r.stdout.splitlines() if c.strip()]
    return (cols or None), {}


def _delimited(opener, delim, profile, max_rows):
    with opener() as fh:
        reader = csv.reader(fh, delimiter=delim)
        try:
            header = next(reader)
        except StopIteration:
            return None, {}
        header = [h.strip() for h in header]
        if not profile:
            return header, {}
        nonmiss = [0] * len(header)
        distinct = [set() for _ in header]
        rows = 0
        for row in reader:
            rows += 1
            for j, v in enumerate(row[:len(header)]):
                if v.strip().lower() not in NA:
                    nonmiss[j] += 1
                    if len(distinct[j]) <= 50:
                        distinct[j].add(v)
            if rows >= max_rows:
                break
        stats = {h: (nonmiss[j], len(distinct[j]), rows) for j, h in enumerate(header)}
        return header, stats


def load_code(root: Path, code_dirs: list[str]) -> list[tuple[str, str]]:
    corpus = []
    bases = [root / d for d in code_dirs] if code_dirs else [root]
    for base in bases:
        for dirpath, dirnames, files in os.walk(base):
            rel_parts = Path(dirpath).relative_to(root).parts
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not ARCHIVE_RE.match(d)]
            if is_archived(rel_parts):
                continue
            for f in files:
                if Path(f).suffix.lower() in CODE_EXTS or f in {"Makefile", "Snakefile"}:
                    p = Path(dirpath) / f
                    try:
                        if p.stat().st_size > 3_000_000:
                            continue
                        corpus.append((p.relative_to(root).as_posix(),
                                       p.read_text(encoding="utf-8", errors="replace")))
                    except OSError:
                        continue
    return corpus


UNIT_TOKENS = {"kg", "g", "mg", "ug", "lb", "lbs", "m", "m2", "cm", "cm2", "mm", "ml", "l",
               "dl", "mmol", "umol", "mmhg", "bpm", "pct", "percent", "per", "day", "days", "wk",
               "weeks", "mo", "months", "yr", "yrs", "years", "hr", "hrs", "hours", "min", "sec",
               "kcal", "cal", "n", "num", "count", "raw", "val", "value", "score", "cat", "bin",
               "flag", "ind", "01", "yn"}


def unit_stripped(name: str) -> str | None:
    toks = snake(name).split("_")
    while len(toks) > 1 and toks[-1] in UNIT_TOKENS:
        toks.pop()
    stripped = "_".join(toks)
    return stripped if stripped != snake(name) and len(stripped) >= 3 else None


QUOTED_RE = re.compile(r"[\"']([^\"'\n]{1,80})[\"']")
LIST_ITEM_RE = re.compile(r"^\s*[\"']([^\"'\n]{1,80})[\"']\s*[,)\]]?\s*(#.*)?$")


def is_declaration(line: str, colset: set[str], names: set[str]) -> bool:
    """True when this line mentions the column only to declare or build it, not to analyze it:
    a schema line with four or more quoted column names (field lists, rename maps), a lone
    quoted name inside a vertical list, a dict key while building records ("phase": ...),
    or an assignment target (row["phase"] = ...)."""
    quoted = [q.lower() for q in QUOTED_RE.findall(line)]
    if sum(1 for q in quoted if q in colset) >= 4:
        return True
    m = LIST_ITEM_RE.match(line)
    if m and m.group(1).lower() in names:
        return True
    for nm in names:
        esc = re.escape(nm)
        if re.match(rf"^\s*[\"']{esc}[\"']\s*:", line, re.I):
            return True
        if re.search(rf"\[\s*[\"']{esc}[\"']\s*\]\s*=(?!=)", line, re.I) and \
                len(re.findall(esc, line, re.I)) == 1:
            return True
    return False


def find_hits(col: str, corpus, colset: set[str] | None = None) -> tuple[int, str, int]:
    """Return (analysis hits, first analysis hit, declaration-only hits)."""
    name = col.split("$")[-1]
    variants = {name, snake(name), name.lower()}
    alt = unit_stripped(name)
    if alt:
        variants.add(alt)
    pats = []
    for v in variants:
        if not v:
            continue
        esc = re.escape(v)
        pats.append(rf"[\"'`]{esc}[\"'`]")                     # quoted
        if re.fullmatch(r"[A-Za-z_.][A-Za-z0-9_.]*", v):
            pats.append(rf"(?<![A-Za-z0-9_.$]){esc}(?![A-Za-z0-9_])")  # bare identifier
    pat = re.compile("|".join(pats))
    total, first, declared = 0, "", 0
    for rel, text in corpus:
        for n, line in enumerate(text.splitlines(), start=1):
            if pat.search(line):
                if colset and is_declaration(line, colset, {v.lower() for v in variants}):
                    declared += 1
                    continue
                total += 1
                if not first:
                    first = f"{rel}:{n}"
    return total, first, declared


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--data", action="append", default=[],
                    help="data folder(s) relative to root (default: data)")
    ap.add_argument("--code", action="append", default=[],
                    help="code folder(s) relative to root (default: whole project minus archive)")
    ap.add_argument("--profile", action="store_true", help="non-missing and distinct counts (CSV/TSV)")
    ap.add_argument("--max-rows", type=int, default=200_000)
    ap.add_argument("--out-csv", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    data_dirs = args.data or (["data"] if (root / "data").is_dir() else ["."])
    corpus = load_code(root, args.code)
    rows, notes = [], defaultdict(int)
    for d in data_dirs:
        for dirpath, dirnames, files in os.walk(root / d):
            rel_parts = Path(dirpath).relative_to(root).parts
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and not ARCHIVE_RE.match(x)]
            if is_archived(rel_parts):
                continue
            for f in sorted(files):
                p = Path(dirpath) / f
                if p.suffix.lower() not in TABLE_EXTS:
                    continue
                cols, stats = headers(p, args.profile, args.max_rows)
                rel = p.relative_to(root).as_posix()
                written = any(f in line and WRITE_HINT_RE.search(line)
                              for _, text in corpus for line in text.splitlines()
                              for f in [p.name] if f in text)
                if not cols:
                    if isinstance(stats, dict) and stats.get("_note"):
                        notes[f"{p.suffix.lower()} skipped ({stats['_note']})"] += 1
                    continue
                colset = {c.split("$")[-1].lower() for c in cols} | \
                         {snake(c.split("$")[-1]) for c in cols}
                for c in cols:
                    hits, first, declared = find_hits(c, corpus, colset)
                    nm, nd, nr = stats.get(c, ("", "", "")) if stats else ("", "", "")
                    used = "yes" if hits else ("declared only" if declared else "no")
                    rows.append({"dataset": rel + (" (written by code)" if written else ""),
                                 "column": c, "used": used,
                                 "code_hits": hits, "first_hit": first, "non_missing": nm,
                                 "distinct": (f"{nd}+" if nd == 51 else nd), "rows_read": nr})

    if args.out_csv:
        Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["dataset"])
            w.writeheader()
            w.writerows(rows)

    by_ds = defaultdict(list)
    for r in rows:
        by_ds[r["dataset"]].append(r)
    L = ["# Variables collected but not used", "",
         f"- Code searched: {len(corpus)} files (archive excluded)",
         f"- Datasets: {len(by_ds)}; columns: {len(rows)}; unused: "
         f"{sum(1 for r in rows if r['used'] != 'yes')}"]
    if notes:
        L.append("- " + "; ".join(f"{k}: {v}" for k, v in notes.items()))
    L += ["", "A place to look, not a to-do list: an unused variable earns an analysis only "
          "if it answers a question that would change the paper.", ""]
    for ds, items in by_ds.items():
        unused = [r for r in items if r["used"] != "yes"]
        L.append(f"## `{ds}`: {len(unused)} of {len(items)} columns unused")
        L.append("")
        if ds.endswith("(written by code)"):
            L.append("This dataset is an output of the analysis code, so unused columns here may "
                     "simply be carried through; check the source it was built from.")
            L.append("")
        if unused:
            if args.profile and unused[0]["non_missing"] != "":
                unused.sort(key=lambda r: -(r["non_missing"] or 0))
                L += [f"- `{r['column']}` (non-missing {r['non_missing']}/{r['rows_read']}, "
                      f"distinct {r['distinct']})"
                      + (" (named in a field list only)" if r["used"] == "declared only" else "")
                      for r in unused[:80]]
            else:
                L += [f"- `{r['column']}`"
                      + (" (named in a field list only)" if r["used"] == "declared only" else "")
                      for r in unused[:80]]
            if len(unused) > 80:
                L.append(f"- ...and {len(unused) - 80} more")
        L.append("")
    report = "\n".join(L) + "\n"
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(report, encoding="utf-8")
        print(f"report: {args.out_md}")
    print("\n".join(L[:4]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
