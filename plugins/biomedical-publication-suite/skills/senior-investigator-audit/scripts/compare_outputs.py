#!/usr/bin/env python3
"""Compare two sets of analysis outputs numerically.

Use it to prove that a rerun reproduces the baseline (after reorganizing, or
after a clean rebuild) and to show exactly which numbers a bug fix changed.

Pairs files by relative path, then by unique basename, then by an optional
pairs CSV (columns: before,after), and follows renames in a safe_move.py log.
Tables (.csv/.tsv/.txt with a delimiter) are aligned by column name and, when a
key column identifies rows (--key, or a unique first column), by row key; cells
are compared with numeric tolerance, and added or dropped rows and columns are
reported as structure. JSON is compared
recursively; other text exactly; binaries (figures, .rds, .pdf) by sha256,
which usually differs harmlessly because of embedded timestamps.

Verdict and exit status: VERIFIED (0) when everything compared matches within
tolerance; DIFFERENT (1) when anything differs, is missing, or is new in AFTER
(pass --allow-new when new outputs are expected); PARTIAL (2) when nothing differs but some
files could not be compared (binary files whose bytes differ, such as
regenerated figures); NOTHING COMPARED (3) when a folder is missing or empty. A match is evidence about these files
only; it does not validate the analysis that produced them.

Example
  python3 compare_outputs.py _audit/baseline/results _audit/work/results \
      --out-md _audit/runs/rerun_comparison.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

TABLE_EXTS = {".csv", ".tsv", ".tab"}
TEXT_EXTS = {".txt", ".md", ".log", ".tex", ".html", ".htm", ".yaml", ".yml"}
JSON_EXTS = {".json"}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}
NA_STRINGS = {"", "na", "nan", "null", "none", "n/a", ".", "-"}
NUM_RE = re.compile(r"^[+\-−]?(\d+(\.\d*)?|\.\d+)([eE][+\-]?\d+)?%?$")


def files_under(d: Path) -> dict[str, Path]:
    out = {}
    for dirpath, dirnames, fs in os.walk(d):
        dirnames[:] = [x for x in dirnames if not x.startswith(".")]
        for f in fs:
            if f in SKIP_NAMES or f.startswith("~$"):
                continue
            p = Path(dirpath) / f
            out[p.relative_to(d).as_posix()] = p
    return out


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def to_num(s: str):
    t = s.strip().replace(",", "").replace("−", "-")
    if t.lower() in NA_STRINGS:
        return "NA"
    if t.lower() in {"inf", "+inf", "infinity"}:
        return math.inf
    if t.lower() in {"-inf", "-infinity"}:
        return -math.inf
    if NUM_RE.match(t):
        pct = t.endswith("%")
        v = float(t.rstrip("%"))
        return v / 100 if pct else v
    return None


def close(a: float, b: float, rtol: float, atol: float) -> bool:
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= atol + rtol * abs(b)


def read_table(p: Path) -> list[list[str]]:
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    delim = "\t" if p.suffix.lower() in {".tsv", ".tab"} else ","
    if p.suffix.lower() not in {".tsv", ".tab"}:
        try:
            delim = csv.Sniffer().sniff(text[:20000], delimiters=",;\t|").delimiter
        except csv.Error:
            delim = ","
    return [row for row in csv.reader(io.StringIO(text), delimiter=delim)]


def _is_header(row: list[str]) -> bool:
    cells = [c for c in row if c.strip()]
    return bool(cells) and all(to_num(c) is None for c in cells)


def _named(header: list[str]) -> list[str]:
    """Column identifiers that cannot collide: a repeated name gets its occurrence number
    in brackets, and brackets are escaped in real names (a, a, "a [2]" -> a, a [2], a \\[2\\])."""
    seen: dict[str, int] = {}
    out = []
    for h in header:
        h = h.strip()
        seen[h] = seen.get(h, 0) + 1
        esc = h.replace("[", "\\[").replace("]", "\\]")
        out.append(esc if seen[h] == 1 else f"{esc} [{seen[h]}]")
    return out


def _cell_diff(ca: str, cb: str, rtol: float, atol: float):
    """None if equal (within tolerance), else (abs_diff, rel_diff) or ('text', 'text')."""
    if ca == cb or ca.strip() == cb.strip():
        return None
    na, nb = to_num(ca), to_num(cb)
    if na == "NA" and nb == "NA":
        return None
    if isinstance(na, float) and isinstance(nb, float):
        if math.isnan(na) and math.isnan(nb):
            return None
        d = abs(na - nb)
        if close(na, nb, rtol, atol):
            return ("within", d)
        return (d, d / abs(nb) if nb else math.inf)
    return ("text", "text")


def compare_tables(a, b, rtol, atol, sort_rows, key=None):
    res = {"status": "match", "n_diff": 0, "max_abs": 0.0, "max_rel": 0.0, "examples": [],
           "notes": []}
    if not a or not b:
        res["status"] = "match" if a == b else "shape differs"
        return res
    header = _is_header(a[0]) and _is_header(b[0])
    if header:
        ha, hb = _named(a[0]), _named(b[0])
        rows_a, rows_b = a[1:], b[1:]
        for label, rows, width in (("before", rows_a, len(a[0])), ("after", rows_b, len(b[0]))):
            ragged = sum(1 for r in rows if len(r) != width and any(c.strip() for c in r))
            if ragged:
                res["notes"].append(f"columns only in one version: {ragged} {label} row(s) do not "
                                    f"match the header's {width} columns")
        if len(set(a[0])) != len(a[0]) or len(set(b[0])) != len(b[0]):
            res["notes"].append("repeated column names; matched by name and occurrence")
        common = [c for c in ha if c in hb]
        removed = [c for c in ha if c not in hb]
        added = [c for c in hb if c not in ha]
        if removed:
            res["notes"].append("columns only in before: " + ", ".join(removed[:8]))
        if added:
            res["notes"].append("columns only in after: " + ", ".join(added[:8]))
        ia = {c: ha.index(c) for c in common}
        ib = {c: hb.index(c) for c in common}
    else:
        rows_a, rows_b = a, b
        wa = [len(r) for r in a]
        wb = [len(r) for r in b]
        if wa[:len(wb)] != wb[:len(wa)] or max(wa, default=0) != max(wb, default=0):
            res["notes"].append(f"columns only in one version (row widths {max(wa, default=0)} -> "
                                f"{max(wb, default=0)})")
        width = max(max(wa, default=0), max(wb, default=0))
        common = [f"col{j + 1}" for j in range(width)]
        ia = ib = {c: j for j, c in enumerate(common)}

    def val(row, idx):
        return row[idx] if idx < len(row) else ""

    # Row alignment: explicit key, else a unique identifier-like first column, else position.
    key_cols = []
    if header and key:
        key_cols = [k.strip() for k in key.split(",") if k.strip() in common]
        if len(key_cols) != len([k for k in key.split(",") if k.strip()]):
            res["notes"].append(f"key '{key}' not found in both headers; matched rows by position")
            key_cols = []
    if header and not key_cols and common:
        c0 = common[0]
        ka = [val(r, ia[c0]) for r in rows_a]
        kb = [val(r, ib[c0]) for r in rows_b]
        nonnum = sum(1 for x in ka if to_num(x) is None)
        if len(set(ka)) == len(ka) and len(set(kb)) == len(kb) and ka and nonnum >= len(ka) / 2:
            key_cols = [c0]
            res["notes"].append(f"rows matched on `{c0}`")
    pairs = []
    if key_cols:
        def kk(row, idx):
            return tuple(val(row, idx[c]).strip() for c in key_cols)
        dup_a = len(rows_a) - len({kk(r, ia) for r in rows_a})
        dup_b = len(rows_b) - len({kk(r, ib) for r in rows_b})
        if dup_a or dup_b:
            res["notes"].append(f"key `{','.join(key_cols)}` is not unique ({dup_a} duplicate(s) before, "
                                f"{dup_b} after), so rows cannot be matched by key; compared as sorted "
                                f"rows instead (pass a compound --key to match exactly)")
            key_cols = []
            sort_rows = True
    if key_cols:
        def k(row, idx):
            return tuple(val(row, idx[c]).strip() for c in key_cols)
        map_b = {k(r, ib): r for r in rows_b}
        keys_a = [k(r, ia) for r in rows_a]
        only_a = [x for x in keys_a if x not in map_b]
        set_a = set(keys_a)
        only_b = [x for x in map_b if x not in set_a]
        if only_a:
            res["notes"].append(f"{len(only_a)} rows only in before (e.g. {', '.join('/'.join(x) for x in only_a[:3])})")
        if only_b:
            res["notes"].append(f"{len(only_b)} rows only in after (e.g. {', '.join('/'.join(x) for x in only_b[:3])})")
        for r in rows_a:
            kk = k(r, ia)
            if kk in map_b:
                pairs.append(("/".join(kk), r, map_b[kk]))
    else:
        if sort_rows:
            rows_a = sorted(rows_a, key=lambda r: [val(r, ia[c]).strip() for c in common])
            rows_b = sorted(rows_b, key=lambda r: [val(r, ib[c]).strip() for c in common])
        if len(rows_a) != len(rows_b):
            res["notes"].append(f"row count {len(rows_a)} -> {len(rows_b)}")
        pairs = [(f"data row {i + 1}", ra, rb) for i, (ra, rb) in enumerate(zip(rows_a, rows_b))]

    for label, ra, rb in pairs:
        for c in common:
            d = _cell_diff(val(ra, ia[c]), val(rb, ib[c]), rtol, atol)
            if d is None:
                continue
            if d[0] == "within":
                res["max_abs"] = max(res["max_abs"], d[1])
                continue
            if d[0] != "text":
                res["max_abs"] = max(res["max_abs"], d[0])
                res["max_rel"] = max(res["max_rel"], d[1])
            res["n_diff"] += 1
            if len(res["examples"]) < 8:
                res["examples"].append(f"{label}, {c}: `{val(ra, ia[c])}` -> `{val(rb, ib[c])}`")
    structural = any(n.startswith(("columns only", "row count")) or "rows only" in n
                     for n in res["notes"])
    if res["n_diff"]:
        res["status"] = "values differ"
    elif structural:
        res["status"] = "structure differs"
    elif res["max_abs"] > 0:
        res["status"] = "match (within tolerance)"
    return res


def compare_json(x, y, rtol, atol, path="$", out=None):
    out = [] if out is None else out
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y:
                out.append(f"{path}.{k}: only in {'after' if k not in x else 'before'}")
            else:
                compare_json(x[k], y[k], rtol, atol, f"{path}.{k}", out)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            out.append(f"{path}: length {len(x)} -> {len(y)}")
        for i, (u, v) in enumerate(zip(x, y)):
            compare_json(u, v, rtol, atol, f"{path}[{i}]", out)
    elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and \
            not isinstance(x, bool) and not isinstance(y, bool):
        if not close(float(x), float(y), rtol, atol):
            out.append(f"{path}: {x} -> {y}")
    elif x != y:
        out.append(f"{path}: {json.dumps(x)[:60]} -> {json.dumps(y)[:60]}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--pairs", help="CSV with columns before,after (relative paths)")
    ap.add_argument("--moves", help="file_moves.csv from safe_move.py, to follow renames")
    ap.add_argument("--prefix", default="results",
                    help="project-relative path that BEFORE and AFTER both represent "
                         "(used with --moves; default: results)")
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--atol", type=float, default=1e-9)
    ap.add_argument("--sort-rows", action="store_true",
                    help="ignore row order in tables (when rows are matched by position)")
    ap.add_argument("--key", default=None,
                    help="column(s) that identify a row, e.g. nct_id or term,model "
                         "(default: the first column when it is a unique identifier)")
    ap.add_argument("--allow-new", action="store_true",
                    help="files that exist only in AFTER are expected (e.g. outputs of newly added "
                         "analyses): list them without counting them as differences")
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    bdir, adir = Path(args.before), Path(args.after)
    for label, d in (("before", bdir), ("after", adir)):
        if not d.is_dir():
            print(f"error: {label} folder does not exist or is not a folder: {d}", file=sys.stderr)
            return 3
    bf, af = files_under(bdir), files_under(adir)
    pairs: dict[str, str] = {}
    if args.pairs:
        with open(args.pairs, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                pairs[r["before"].strip()] = r["after"].strip()
    moved: dict[str, str] = {}
    if args.moves:
        with open(args.moves, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("status", "done") == "done" and r.get("src") and r.get("dst") \
                        and r.get("action") in {"move", "rename", "archive"}:
                    moved[r["src"]] = r["dst"]
    prefix = args.prefix.strip("/")

    def follow(p: str) -> str:
        seen = set()
        while p in moved and p not in seen:
            seen.add(p)
            p = moved[p]
        return p

    a_by_base = defaultdict(list)
    for rel in af:
        a_by_base[rel.split("/")[-1]].append(rel)
    matched_after = set()
    results = []
    for rel, bp in sorted(bf.items()):
        target = pairs.get(rel)
        how = "pairs file"
        if target is None and moved:
            proj = f"{prefix}/{rel}" if prefix else rel
            final = follow(proj)
            if final != proj:
                if re.match(r"^_*archive", final.split("/")[0], re.I):
                    results.append((rel, final, "archived in reorg", {}, "move log"))
                    continue
                if not prefix:
                    target, how = final, "move log"
                elif final.startswith(prefix + "/"):
                    target, how = final[len(prefix) + 1:], "move log"
        if target is None and rel in af:
            target, how = rel, "same path"
        if target is None:
            cands = a_by_base.get(rel.split("/")[-1], [])
            if len(cands) == 1:
                target, how = cands[0], "same name"
        if target is None or target not in af:
            results.append((rel, None, "missing in after", {}, ""))
            continue
        matched_after.add(target)
        ap_ = af[target]
        ext = bp.suffix.lower()
        try:
            if ext in TABLE_EXTS or (ext == ".txt" and "\t" in bp.read_text(errors="replace")[:2000]):
                r = compare_tables(read_table(bp), read_table(ap_), args.rtol, args.atol,
                                   args.sort_rows, args.key)
                results.append((rel, target, r["status"], r, how))
            elif ext in JSON_EXTS:
                diffs = compare_json(json.loads(bp.read_text()), json.loads(ap_.read_text()),
                                     args.rtol, args.atol)
                results.append((rel, target, "values differ" if diffs else "match",
                                {"examples": diffs[:8], "n_diff": len(diffs)}, how))
            elif ext in TEXT_EXTS:
                same = bp.read_text(errors="replace") == ap_.read_text(errors="replace")
                results.append((rel, target, "match" if same else "text differs", {}, how))
            else:
                same = sha(bp) == sha(ap_)
                results.append((rel, target, "match" if same else "binary differs", {}, how))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            results.append((rel, target, f"error: {exc}", {}, how))
    only_after = sorted(set(af) - matched_after)

    failing = [r for r in results if r[2] not in
               {"match", "match (within tolerance)", "binary differs", "archived in reorg"}]
    unchecked = [r for r in results if r[2] == "binary differs"]
    compared = [r for r in results if r[2] != "archived in reorg"]
    if only_after and not args.allow_new:
        failing = failing + [(p, p, "only in after", {}, "") for p in only_after]
    if not compared and not only_after:
        verdict = "NOTHING COMPARED"
    else:
        verdict = "DIFFERENT" if failing else ("PARTIAL" if unchecked else "VERIFIED")
    lines = ["# Output comparison", "",
             f"- Before: `{bdir}` ({len(bf)} files)",
             f"- After: `{adir}` ({len(af)} files)",
             f"- Tolerance: rtol={args.rtol:g}, atol={args.atol:g}"
             + (", rows unordered" if args.sort_rows else ""),
             f"- Result: **{verdict}** "
             f"({sum(1 for r in results if r[2].startswith('match'))} match, "
             f"{sum(1 for r in results if r[2] == 'binary differs')} binary differ, "
             f"{sum(1 for r in results if r[2] == 'archived in reorg')} archived, "
             f"{len(failing)} need attention, {len(only_after)} only in after)", ""]
    if failing:
        lines += ["## Needs attention", ""]
        for rel, target, status, info, how in failing:
            lines.append(f"- `{rel}` -> `{target or '-'}`: **{status}**"
                         + (f"; {info.get('n_diff', 0)} cells differ, max abs diff "
                            f"{info.get('max_abs', 0):.3g}, max rel diff {info.get('max_rel', 0):.3g}"
                            if info.get("n_diff") and "max_abs" in info else ""))
            for note in info.get("notes", []):
                lines.append(f"  - {note}")
            for ex in info.get("examples", []):
                lines.append(f"  - {ex}")
        lines.append("")
    binaries = [r for r in results if r[2] == "binary differs"]
    if binaries:
        lines += ["## Not checked: binary files whose bytes differ (regenerate and inspect them)", ""]
        lines += [f"- `{r[0]}`" for r in binaries[:100]] + [""]
    if only_after:
        lines += ["## Only in after", ""] + [f"- `{p}`" for p in only_after[:100]] + [""]
    report = "\n".join(lines) + "\n"
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(report, encoding="utf-8")
    print(report)
    return {"VERIFIED": 0, "DIFFERENT": 1, "PARTIAL": 2, "NOTHING COMPARED": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main())
