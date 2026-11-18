#!/usr/bin/env python3
"""Trace every number in a manuscript back to the analysis outputs.

For each number in the documents (abstract, manuscript, tables in .md/.qmd/
.Rmd/.tex/.docx), search the output files (.csv/.tsv/.txt/.md/.json/.log/
.html/.xlsx) for a value that rounds to it at the precision reported. Also
tries common reporting transforms: proportion -> percent (x100), ratio ->
percent change ((x-1)x100 or (1-x)x100), log-scale coefficient -> ratio
(exp), and log-scale coefficient -> percent change ((exp(x)-1)x100). A match found only through a transform is reported as "derived" so the
arithmetic can be checked.

The most useful output is the UNMATCHED list: numbers that appear in the
paper but in no output file. Each is a typo, a stale value from an earlier
run, a hand-typed number, or a result the code never saved. All four need
fixing. A number "found" in an output is only a candidate source: the same
value can sit in an unrelated table, and low-precision numbers match by
coincidence. Confirm each claim-bearing number against its specific cell
(population, model, endpoint, run). "n/N (x%)" statements are also checked
for arithmetic: "consistent" or "mismatch".

Example
  python3 trace_numbers.py --doc manuscript/manuscript.md --outputs results \
      --out-csv _audit/runs/number_trace.csv --out-md _audit/runs/number_trace.md
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from doctext import extract_blocks  # noqa: E402

NUM_RE = re.compile(
    r"(?P<prefix>[<>≤≥~≈]\s*|=\s*)?"
    r"(?<![\w.])(?<![A-Za-z][-‐])"
    r"(?P<sign>[-−–]?)"
    r"(?P<num>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
    r"(?P<pct>\s?%)?"
    r"(?![\w]|\.\d)")
FLAT_CITATION_RE = re.compile(r"(?<=[A-Za-z)\]][.,;:])\d{1,3}(?:[,\u2013\-]\d{1,3})*(?=[\s)]|$)")
COUNT_RATIO_RE = re.compile(r"(\d[\d,]*)\s*/\s*(\d[\d,]*)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)")
CITATION_RE = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]|\^\d+(?:[-–,]\d+)*\^|<sup>[\d,\-–]+</sup>")
LABEL_RE = re.compile(
    r"\b(?:e?Tables?|e?Figures?|Figs?\.|Supplement(?:ary|al)?\s+(?:Tables?|Figures?)|"
    r"Appendix|Sections?|Models?|Steps?|Phases?|Stages?|Grades?|Types?|Class(?:es)?|"
    r"Arms?|Aims?|Hypothes[ie]s|Panels?|Items?|Chapters?|Version|Wave|Round|Visit)\s+"
    r"S?\d+[A-Za-z]?(?:\s*(?:and|,|-|–)\s*S?\d+[A-Za-z]?)*", re.I)
DATE_RE = re.compile(r"\b(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b|"
                     r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
CI_LEVEL_RE = re.compile(r"^\s*(?:CI|confidence|credible|prediction|uncertainty|HPD)", re.I)
MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$|\\\(.*?\\\)|\\\[.*?\\\]", re.S)
PER_UNIT_RE = re.compile(r"\bper\s*$", re.I)
UNIT_BASES = {Decimal(10) ** k for k in range(1, 7)}
URL_RE = re.compile(r"https?://\S+|doi:\s*\S+|\b10\.\d{4,9}/\S+", re.I)

OUTPUT_TEXT_EXTS = {".txt", ".md", ".log", ".json", ".html", ".htm", ".tex", ".yaml", ".yml"}
OUTPUT_TABLE_EXTS = {".csv", ".tsv", ".tab"}
UNREADABLE_EXTS = {".rds", ".rda", ".rdata", ".parquet", ".feather", ".pkl", ".pickle",
                   ".sav", ".dta", ".h5", ".hdf5", ".npz", ".npy", ".qs", ".fst"}
TRANSFORMS = {
    "id": lambda v: v,
    "x100": lambda v: v * 100,
    "pct_change": lambda v: (v - 1) * 100 if 0 < v < 20 else None,
    "pct_decrease": lambda v: (1 - v) * 100 if 0 < v < 2 else None,
    "exp": lambda v: math.exp(v) if -10 < v < 10 else None,
    "exp_pct_change": lambda v: (math.exp(v) - 1) * 100 if -5 < v < 5 else None,
}
PRIMARY = {"id", "x100"}


def parse_number(m) -> tuple[Decimal, int, bool, str, str] | None:
    num = m.group("num").replace(",", "")
    sign = m.group("sign") or ""
    start = m.start("sign") if sign else m.start("num")
    before = m.string[max(0, start - 1):start]
    if sign in {"-", "–"} and before and (before in "%)0123456789" or before.isalpha()):
        sign = ""  # a range dash, not a minus sign
    try:
        val = Decimal(num)
    except InvalidOperation:
        return None
    if sign:
        val = -val
    decimals = len(num.split(".")[1]) if "." in num else 0
    prefix = (m.group("prefix") or "").strip()
    return val, decimals, bool(m.group("pct")), prefix, sign


def sig_digits(num_text: str) -> int:
    digits = num_text.replace(",", "").replace(".", "").lstrip("-−–").lstrip("0")
    return len(digits)


def doc_numbers(path: Path, keep_years: bool):
    out = []
    blocks = extract_blocks(path)
    has_sections = any(b["section"] for b in blocks)
    for b in blocks:
        if b["kind"] == "heading" or b["canonical"] == "references":
            continue
        if has_sections and not b["section"]:
            continue  # title page: word counts, affiliations
        text = MATH_RE.sub(" ", URL_RE.sub(" ", b["text"]))
        text = CITATION_RE.sub(" ", text)
        text = FLAT_CITATION_RE.sub(" ", text)
        ratios = {}
        for rm in COUNT_RATIO_RE.finditer(text):
            try:
                a = Decimal(rm.group(1).replace(",", ""))
                n = Decimal(rm.group(2).replace(",", ""))
                pct = Decimal(rm.group(3))
            except InvalidOperation:
                continue
            if n == 0:
                continue
            d = len(rm.group(3).split(".")[1]) if "." in rm.group(3) else 0
            exact = a * 100 / n
            ok = abs(exact - pct) <= Decimal(5) / (Decimal(10) ** (d + 1)) + Decimal("1e-9")
            ratios[rm.start(3)] = (ok, f"{rm.group(1)}/{rm.group(2)} = {exact:.{d + 2}f}%")
        text = LABEL_RE.sub(" ", text)
        text = DATE_RE.sub(" ", text)
        for m in NUM_RE.finditer(text):
            parsed = parse_number(m)
            if parsed is None:
                continue
            val, dec, pct, prefix, sign = parsed
            raw = (sign + m.group("num") + (m.group("pct") or "")).strip()
            if prefix:
                raw = f"{prefix} {raw}" if prefix in {"<", ">", "≤", "≥", "~", "≈"} else raw
            after = text[m.end():m.end() + 14]
            ctx = text[max(0, m.start() - 70):m.end() + 50].replace("\n", " ")
            status = ""
            if prefix in {"<", ">", "≤", "≥"}:
                status = "threshold"
            elif pct and CI_LEVEL_RE.match(after) and val in (Decimal(90), Decimal(95), Decimal(99)):
                status = "skipped"
            elif dec == 0 and not pct and 1900 <= abs(val) <= 2100 and not keep_years:
                status = "skipped"
            elif PER_UNIT_RE.search(text[max(0, m.start() - 12):m.start()]) and \
                    val in UNIT_BASES:
                status = "skipped"  # "per 100,000": a rate unit, not a result
            elif dec == 0 and not pct and abs(val) < 10:
                status = "low_info"
            if not status and pct and m.start("num") in ratios:
                ok, note = ratios[m.start("num")]
                status = "consistent" if ok else "mismatch"
                ratio_note = note
            else:
                ratio_note = ""
            out.append({"doc": str(path), "section": b["section"] or "(untitled)",
                         "canonical": b["canonical"], "kind": b["kind"], "number": raw,
                         "value": val, "decimals": dec, "percent": pct,
                         "approx": prefix in {"~", "≈"}, "status": status,
                         "sig": sig_digits(m.group("num")), "context": ctx.strip(),
                         "transform": "count_ratio" if ratio_note else "",
                         "candidates": ratio_note, "n_candidates": 1 if ratio_note else ""})
    return out


def iter_output_values(root: Path, max_mb: float, notes: Counter):
    """Yield (float_value, location) from output files under root."""
    files = [root] if root.is_file() else sorted(
        p for p in root.rglob("*") if p.is_file() and not any(
            part.startswith(".") for part in p.relative_to(root).parts))
    for p in files:
        ext = p.suffix.lower()
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if ext in UNREADABLE_EXTS:
            notes[f"not searched (binary {ext})"] += 1
            continue
        if size > max_mb * 1_000_000:
            notes["not searched (too large)"] += 1
            continue
        try:
            rel = os.path.relpath(p, Path.cwd())
        except ValueError:
            rel = p.as_posix()
        if rel.startswith("../../"):
            rel = p.as_posix()
        if ext in OUTPUT_TABLE_EXTS:
            try:
                text = p.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            delim = "\t" if ext in {".tsv", ".tab"} else ","
            rows = list(csv.reader(io.StringIO(text), delimiter=delim))
            header = rows[0] if rows else []
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    for m in NUM_RE.finditer(cell):
                        parsed = parse_number(m)
                        if parsed:
                            col = header[j] if (i > 0 and j < len(header)) else f"c{j + 1}"
                            yield float(parsed[0]), f"{rel}:r{i + 1}:{col}"
            notes["tables searched"] += 1
        elif ext == ".xlsx":
            try:
                import openpyxl  # optional
            except ImportError:
                notes["not searched (.xlsx needs openpyxl)"] += 1
                continue
            try:
                wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
            except Exception:  # noqa: BLE001
                notes["not searched (unreadable .xlsx)"] += 1
                continue
            for ws in wb.worksheets:
                for row in ws.iter_rows():
                    for c in row:
                        v = c.value
                        coord = getattr(c, "coordinate", "?")
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            yield float(v), f"{rel}!{ws.title}!{coord}"
                        elif isinstance(v, str):
                            for m in NUM_RE.finditer(v):
                                parsed = parse_number(m)
                                if parsed:
                                    yield float(parsed[0]), f"{rel}!{ws.title}!{coord}"
            notes["workbooks searched"] += 1
        elif ext in OUTPUT_TEXT_EXTS or ext == "":
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "\x00" in text[:2000]:
                continue
            for n, line in enumerate(text.splitlines(), start=1):
                for m in NUM_RE.finditer(line):
                    parsed = parse_number(m)
                    if parsed:
                        yield float(parsed[0]), f"{rel}:{n}"
            notes["text files searched"] += 1
        else:
            notes[f"not searched ({ext or 'no extension'})"] += 1


def keys_for(v: float, d: int) -> set[int]:
    t = v * (10 ** d)
    if math.isnan(t) or math.isinf(t) or abs(t) > 1e15:
        return set()
    lo, hi = math.floor(t + 0.5), math.ceil(t - 0.5)
    ks = {lo, hi}
    # tolerate float noise at ties (e.g. 0.125 stored as 0.12499999)
    if abs((t % 1) - 0.5) < 1e-6:
        ks |= {math.floor(t), math.ceil(t)}
    return ks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", action="append", required=True, help="manuscript file (repeatable)")
    ap.add_argument("--outputs", action="append", required=True,
                    help="output folder or file to search (repeatable)")
    ap.add_argument("--out-csv", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--keep-years", action="store_true")
    ap.add_argument("--max-mb", type=float, default=25)
    ap.add_argument("--max-candidates", type=int, default=4)
    args = ap.parse_args(argv)

    numbers = []
    for d in args.doc:
        numbers += doc_numbers(Path(d), args.keep_years)
    to_search = [n for n in numbers if not n["status"]]
    for n in to_search:
        n["target"] = int((n["value"] * (Decimal(10) ** n["decimals"])).to_integral_value())
    wanted: dict[int, set[int]] = defaultdict(set)
    for n in to_search:
        wanted[n["decimals"]].update({n["target"], -n["target"]})
    decs = sorted(wanted)

    index: dict[tuple[str, int], dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    counts: Counter = Counter()
    notes: Counter = Counter()
    n_values = 0
    for root in args.outputs:
        for v, loc in iter_output_values(Path(root), args.max_mb, notes):
            n_values += 1
            for tname, fn in TRANSFORMS.items():
                try:
                    tv = fn(v)
                except OverflowError:
                    tv = None
                if tv is None:
                    continue
                for d in decs:
                    targets = wanted[d]
                    for k in keys_for(tv, d):
                        if k in targets:
                            counts[(tname, d, k)] += 1
                            bucket = index[(tname, d)][k]
                            if len(bucket) < args.max_candidates and loc not in bucket:
                                bucket.append(loc)

    for n in to_search:
        d = n["decimals"]
        target = n["target"]
        order = (["id", "x100", "pct_change", "pct_decrease", "exp_pct_change"] if n["percent"]
                 else ["id", "exp", "x100"])
        n["status"], n["transform"], n["n_candidates"], n["candidates"] = "unmatched", "", 0, ""
        for tname in order:
            hits = counts.get((tname, d, target), 0)
            if not hits and target != 0:
                hits_abs = counts.get((tname, d, -target), 0)
                if hits_abs and tname == "id":
                    n.update(status="derived", transform="sign_flip", n_candidates=hits_abs,
                             candidates="; ".join(index[(tname, d)][-target]))
                    break
            if hits:
                n["status"] = "found" if tname in PRIMARY else "derived"
                n["transform"] = tname
                n["n_candidates"] = hits
                n["candidates"] = "; ".join(index[(tname, d)][target])
                break
    for n in numbers:
        n.setdefault("transform", "")
        n.setdefault("n_candidates", "")
        n.setdefault("candidates", "")

    if args.out_csv:
        Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_csv, "w", newline="", encoding="utf-8") as fh:
            fields = ["doc", "section", "kind", "number", "value", "decimals", "percent",
                      "status", "transform", "n_candidates", "candidates", "context"]
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for n in numbers:
                w.writerow({**n, "value": str(n["value"])})

    st = Counter(n["status"] or "unsearched" for n in numbers)
    lines = ["# Number trace", "",
             f"- Documents: {', '.join(f'`{d}`' for d in args.doc)}",
             f"- Outputs searched: {', '.join(f'`{o}`' for o in args.outputs)} "
             f"({n_values:,} numeric values; " + ", ".join(f"{k}: {v}" for k, v in sorted(notes.items())) + ")",
             f"- Numbers in documents: {len(numbers):,}. "
             + ", ".join(f"{k} {v:,}" for k, v in st.most_common()), "",
             "Unmatched numbers appear in the paper but in no output file. Resolve every one "
             "in the abstract, results, tables, and figures: correct it from the output, or "
             "make the code save the result it came from. \"Found\" means the value appears "
             "somewhere in the outputs: a candidate source, not verified provenance. "
             "\"Consistent\" means an n/N (x%) statement computes correctly within the text.", ""]
    for title, pred in [
        ("Arithmetic mismatches (n/N (x%) in the text does not compute)",
         lambda n: n["status"] == "mismatch"),
        ("Unmatched", lambda n: n["status"] == "unmatched" and n["sig"] >= 2),
        ("Unmatched, low precision (one significant digit)",
         lambda n: n["status"] == "unmatched" and n["sig"] < 2),
        ("Derived (matched only through a transform; check the arithmetic)",
         lambda n: n["status"] == "derived"),
        ("Thresholds (e.g. P < .001; check the underlying value)",
         lambda n: n["status"] == "threshold"),
    ]:
        rows = [n for n in numbers if pred(n)]
        lines += [f"## {title} ({len(rows)})", ""]
        by_sec = defaultdict(list)
        for n in rows:
            by_sec[n["section"]].append(n)
        for sec, items in by_sec.items():
            lines.append(f"**{sec}**")
            for n in items[:60]:
                extra = (f" [{n['transform']}: {n['candidates']}]"
                         if n["status"] in {"derived", "mismatch"} else "")
                lines.append(f"- `{n['number']}`{extra}: ...{n['context']}...")
            if len(items) > 60:
                lines.append(f"- ...and {len(items) - 60} more")
            lines.append("")
    weak = [n for n in numbers if n["status"] == "found" and n["sig"] <= 2
            and (n["n_candidates"] or 0) > 10]
    weak_dec = [n for n in weak if n["decimals"] > 0 or n["percent"]]
    weak_int = [n for n in weak if not (n["decimals"] > 0 or n["percent"])]
    if weak:
        lines += [f"## Found, but weakly ({len(weak)})", "",
                  "Low-precision numbers that appear in many output values; finding them proves little. "
                  "Confirm each claim-bearing one against its specific source.", ""]
        seen = set()
        for n in weak_dec:
            if n["number"] in seen:
                continue
            seen.add(n["number"])
            lines.append(f"- `{n['number']}` ({n['section']}): {n['n_candidates']} candidates")
            if len(seen) >= 30:
                break
        if weak_int:
            ints = sorted({n["number"] for n in weak_int}, key=lambda x: float(x.replace(",", "")))
            lines.append(f"- Small integer counts ({len(weak_int)} mentions): "
                         + ", ".join(f"`{x}`" for x in ints[:25])
                         + (" ..." if len(ints) > 25 else "")
                         + ". Check counts against the table or flow diagram they come from.")
        lines.append("")
    report = "\n".join(lines) + "\n"
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(report, encoding="utf-8")
        print(f"report: {args.out_md}")
    print("\n".join(lines[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
