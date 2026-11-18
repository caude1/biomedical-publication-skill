"""Extract section-aware text blocks from manuscripts (.md/.qmd/.Rmd/.txt/.tex/.docx/.html).

Shared by trace_numbers.py and hedge_lint.py. Standard library only.

Each block is a dict: {"section": "Abstract > Results", "canonical": "results",
"kind": "para" | "table_row" | "heading", "text": str, "index": int}.
"""

from __future__ import annotations

import html
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

CANON = [
    ("limitations", re.compile(r"\blimitations?\b|strengths and limitations", re.I)),
    ("abstract_conclusion", re.compile(r"^(conclusions? and relevance|interpretation)$", re.I)),
    ("key_points", re.compile(r"^key points$|^research in context$|^what (is|this study) ", re.I)),
    ("abstract", re.compile(r"^(abstract|summary|structured abstract)$", re.I)),
    ("introduction", re.compile(r"^(introduction|background)$", re.I)),
    ("methods", re.compile(r"^(methods?|materials and methods|patients and methods|study design|statistical analysis)", re.I)),
    ("results", re.compile(r"^results?$", re.I)),
    ("discussion", re.compile(r"^discussion$", re.I)),
    ("conclusion", re.compile(r"^conclusions?$", re.I)),
    ("references", re.compile(r"^(references|bibliography|works cited)$", re.I)),
    ("supplement", re.compile(r"^(supplement|supplementary|appendix|etable|efigure)", re.I)),
]

_RUNIN = (r"(?:Importance|Objectives?|Background|Aims?|Purpose|Context|Design|Setting|Participants|"
          r"Patients|Exposures?|Interventions?|Main Outcomes? and Measures?|Measurements|Methods?|"
          r"Results?|Findings|Conclusions?(?: and Relevance)?|Interpretation|Meaning|Question|"
          r"Limitations?|Funding)")
RUNIN_LABEL_RE = re.compile(
    rf"^\**({_RUNIN}(?:\s*(?:/|,|and|&)\s*{_RUNIN})*)\**\s*[:.]\**\s+(.*)$")
ABSTRACT_RE = re.compile(r"^\s*(abstract|summary|structured abstract)\s*$", re.I)
ABSTRACT_SUB_RE = re.compile(
    r"^(background|objectives?|aims?|purpose|importance|methods?|design|setting|participants|"
    r"patients|exposures?|interventions?|main outcomes?( and measures?)?|results?|findings|"
    r"conclusions?( and relevance)?|interpretation|meaning|funding)$", re.I)
MAJOR_RE = re.compile(
    r"^(abstract|summary|introduction|background|methods?|materials and methods|results?|"
    r"discussion|conclusions?|references|limitations|key points|acknowledg\w*|"
    r"supplement\w*|appendix)$", re.I)
BOLD_LABEL_RE = re.compile(r"^\s*\*\*([^*]{2,60}?)[:.]?\*\*[:.]?\s+(.*)$")
MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
TEX_HEADING_RE = re.compile(r"\\(section|subsection|subsubsection|paragraph)\*?\{([^}]*)\}")


def canonical(section_titles: list[str]) -> str:
    """Innermost recognizable section wins; abstract sub-labels map specially."""
    in_abstract = any(re.match(r"^(abstract|summary|structured abstract)$", t.strip(), re.I)
                      for t in section_titles)
    for title in reversed(section_titles):
        t = re.sub(r"[*_`#]", "", title).strip()
        for name, rx in CANON:
            if rx.search(t):
                if in_abstract and name in {"conclusion"}:
                    return "abstract_conclusion"
                if in_abstract and name in {"results", "methods", "introduction"}:
                    return "abstract"
                return name
    return "body"


def _blocks_from_lines(lines: list[str], is_tex: bool = False) -> list[dict]:
    blocks: list[dict] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    in_code = False
    idx = 0

    def section_titles():
        return [t for _, t in stack]

    def flush():
        nonlocal buf, idx
        if not buf:
            return
        text = " ".join(x.strip() for x in buf).strip()
        buf = []
        if not text:
            return
        titles = section_titles()
        m = BOLD_LABEL_RE.match(text)
        if m and not is_tex:
            label, rest = m.group(1).strip(), m.group(2).strip()
            titles = titles + [label]
            text = rest
        elif canonical(titles) in {"abstract", "key_points"}:
            r = RUNIN_LABEL_RE.match(text)
            if r:
                titles = titles + [r.group(1).strip()]
                text = r.group(2).strip()
        idx += 1
        blocks.append({"section": " > ".join(titles), "canonical": canonical(titles),
                       "kind": "para", "text": text, "index": idx})

    # YAML front matter
    start = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, min(len(lines), 400)):
            if lines[j].strip() in {"---", "..."}:
                start = j + 1
                break
    for raw in lines[start:]:
        line = raw.rstrip("\n")
        if line.strip().startswith(("```", "~~~")):
            flush()
            in_code = not in_code
            continue
        if in_code:
            continue
        if is_tex:
            line = re.sub(r"(?<!\\)%.*$", "", line)
            m = TEX_HEADING_RE.search(line)
            if m:
                flush()
                level = {"section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4}[m.group(1)]
                stack = [(lv, t) for lv, t in stack if lv < level] + [(level, m.group(2))]
                continue
            if re.match(r"\\begin\{abstract\}", line.strip()):
                flush()
                stack = [(1, "Abstract")]
                continue
        else:
            m = MD_HEADING_RE.match(line)
            if m:
                flush()
                level = len(m.group(1))
                stack = [(lv, t) for lv, t in stack if lv < level] + [(level, m.group(2))]
                continue
            if line.lstrip().startswith("|"):
                flush()
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    continue
                idx += 1
                titles = section_titles()
                blocks.append({"section": " > ".join(titles), "canonical": canonical(titles),
                               "kind": "table_row", "text": " | ".join(cells), "index": idx})
                continue
        if not line.strip():
            flush()
            continue
        buf.append(line)
    flush()
    return blocks


def _docx_blocks(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    blocks: list[dict] = []
    stack: list[tuple[int, str]] = []
    idx = 0
    abs_words = 0

    def ptext(p) -> str:
        out = []
        for node in p.iter():
            if node.tag == f"{W}t" and node.text:
                out.append(node.text)
            elif node.tag == f"{W}tab":
                out.append("\t")
            elif node.tag in {f"{W}br", f"{W}cr"}:
                out.append(" ")
        return "".join(out)

    def all_bold(p) -> bool:
        runs = [r for r in p.iter(f"{W}r")
                if "".join(t.text or "" for t in r.iter(f"{W}t")).strip()]
        if not runs:
            return False
        for r in runs:
            rpr = r.find(f"{W}rPr")
            b = rpr.find(f"{W}b") if rpr is not None else None
            if b is None or b.get(f"{W}val", "true").lower() in {"0", "false", "off"}:
                return False
        return True

    def style(p) -> str:
        ppr = p.find(f"{W}pPr")
        if ppr is None:
            return ""
        ps = ppr.find(f"{W}pStyle")
        return ps.get(f"{W}val", "") if ps is not None else ""

    for child in list(body) if body is not None else []:
        if child.tag == f"{W}p":
            text = ptext(child).strip()
            if not text:
                continue
            st = style(child)
            m = re.match(r"(?i)heading\s*(\d)", st)
            if m or st.lower() in {"title"}:
                level = int(m.group(1)) if m else 0
                stack = [(lv, t) for lv, t in stack if lv < level] + [(level, text)]
                continue
            # Agent-written .docx files often mark headings only with bold text.
            if len(text) <= 100 and not text.endswith((".", ":", ";", ",")) and all_bold(child):
                letters = [c for c in text if c.isalpha()]
                all_caps = bool(letters) and all(c.isupper() for c in letters)
                in_abstract = bool(stack) and ABSTRACT_RE.match(stack[0][1] or "")
                if ABSTRACT_RE.match(text):
                    level, abs_words = 1, 0
                elif in_abstract and not all_caps and ABSTRACT_SUB_RE.match(text) and abs_words < 350:
                    level = 2
                elif all_caps or MAJOR_RE.match(text):
                    level = 1
                else:
                    level = 2
                stack = [(lv, t) for lv, t in stack if lv < level] + [(level, text)]
                continue
            if stack and ABSTRACT_RE.match(stack[0][1] or ""):
                abs_words += len(text.split())
            titles = [t for _, t in stack]
            # "Results: text..." style run-in labels in abstracts
            lab = RUNIN_LABEL_RE.match(text)
            if lab and canonical(titles) in {"abstract", "key_points"}:
                titles = titles + [lab.group(1)]
                text = lab.group(2)
            idx += 1
            blocks.append({"section": " > ".join(titles), "canonical": canonical(titles),
                           "kind": "para", "text": text, "index": idx})
        elif child.tag == f"{W}tbl":
            titles = [t for _, t in stack]
            for tr in child.iter(f"{W}tr"):
                cells = []
                for tc in tr.iter(f"{W}tc"):
                    cells.append(" ".join(ptext(p).strip() for p in tc.iter(f"{W}p")).strip())
                idx += 1
                blocks.append({"section": " > ".join(titles), "canonical": canonical(titles),
                               "kind": "table_row", "text": " | ".join(cells), "index": idx})
    return blocks


def _html_blocks(text: str) -> list[dict]:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?is)<h([1-6])[^>]*>(.*?)</h\1>",
                  lambda m: "\n\n" + "#" * int(m.group(1)) + " " + re.sub("<[^>]+>", "", m.group(2)) + "\n\n",
                  text)
    text = re.sub(r"(?is)</(p|div|li|tr|br)\s*>|<br\s*/?>", "\n\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return _blocks_from_lines(text.splitlines())


def _table_blocks(p: Path) -> list[dict]:
    """Treat each row of a CSV/TSV table (e.g. manuscript/tables/*.csv) as a block."""
    import csv
    import io
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    delim = "\t" if p.suffix.lower() in {".tsv", ".tab"} else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    blocks = []
    for i, row in enumerate(rows, start=1):
        blocks.append({"section": p.name, "canonical": "table", "kind": "table_row",
                       "text": " | ".join(c.strip() for c in row), "index": i})
    return blocks


def _strip_title(blocks: list[dict]) -> list[dict]:
    """Drop a document title that heads every section path ("Title > Methods" -> "Methods")."""
    paths = [b["section"] for b in blocks if b["section"]]
    if not paths:
        return blocks
    first = paths[0].split(" > ")[0]
    if all(sp == first or sp.startswith(first + " > ") for sp in paths) and \
            any(sp.startswith(first + " > ") for sp in paths):
        for b in blocks:
            if b["section"] == first:
                b["section"] = ""
            elif b["section"].startswith(first + " > "):
                b["section"] = b["section"][len(first) + 3:]
    return blocks


def extract_blocks(path: str | Path) -> list[dict]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in {".csv", ".tsv", ".tab"}:
        return _table_blocks(p)
    if ext == ".docx":
        return _strip_title(_docx_blocks(p))
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    if ext in {".html", ".htm"}:
        return _strip_title(_html_blocks(text))
    return _strip_title(_blocks_from_lines(text.splitlines(), is_tex=(ext == ".tex")))


SENT_SPLIT_RE = re.compile(
    r"(?<=[.!?])"
    r"(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bet al\.)(?<!\bvs\.)(?<!\bFig\.)(?<!\bNo\.)"
    r"(?<!\bapprox\.)(?<!\bca\.)(?<!\bcf\.)(?<!\bSt\.)(?<!\bDr\.)(?<!\b[A-Z]\.)"
    r"(?:\[[\d,\s\-\u2013]+\])?[\"'\u201d\u2019)\]]?\s+(?=[\"'\u201c\u2018(\[]?[A-Z0-9])"
    # superscript citations flattened into text: "...behavior.1,9 Sex differences"
    r"|(?<=[A-Za-z)\]][.!?])\d{1,3}(?:[,\u2013\-]\d{1,3})*\s+(?=[A-Z])")


def sentences(text: str) -> list[str]:
    parts = SENT_SPLIT_RE.split(text.strip())
    return [s.strip() for s in parts if s and s.strip()]
