#!/usr/bin/env python3
"""Compare a source and revision for protected scientific-content changes.

The checker is deliberately conservative. It inventories mechanical anchors and
semantic-risk markers, reports differences with source locations, and never
rewrites either file. A clean report does not prove semantic equivalence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


NUMBER_TOKEN = r"(?:[+\-\u2212]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+\-\u2212]?\d+)?(?:%|‰)?)"
NUMBER_RE = re.compile(rf"(?<![\w.]){NUMBER_TOKEN}(?!\w|\.\d|[%‰])")

AUTHOR_SURNAME = r"[A-Z][A-Za-z'’-]+"
AUTHOR_GROUP = (
    rf"{AUTHOR_SURNAME}(?:\s+et\s+al\.|"
    rf"\s+(?:&|and)\s+{AUTHOR_SURNAME})?"
)
AUTHOR_YEAR = rf"{AUTHOR_GROUP},?\s+\d{{4}}[a-z]?"

CITATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\[(?:\s*\d+\s*(?:[-–,;]\s*\d+\s*)*)\]"),
    re.compile(r"\[(?:[^\]]*?@[A-Za-z0-9_.:\-/]+[^\]]*?)\]"),
    re.compile(r"\\cite[a-zA-Z*]*\{[^{}]+\}"),
    re.compile(r"\b(?:PMID|PMCID)\s*:?\s*[A-Z]*\d+\b", re.I),
    re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I),
    re.compile(rf"\((?:{AUTHOR_YEAR}(?:\s*;\s*)?)+\)"),
    re.compile(rf"\b{AUTHOR_GROUP}\s+\(\d{{4}}[a-z]?\)"),
)

EQUATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\$\$.*?\$\$", re.S),
    re.compile(r"(?<!\\)\$(?!\$).*?(?<!\\)\$", re.S),
    re.compile(r"\\\[.*?\\\]", re.S),
    re.compile(r"\\\(.*?\\\)", re.S),
)

CROSS_REFERENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:Supplementary\s+(?:Figures?|Tables?)|Figures?|Figs?\.?|Tables?|"
        r"Supplements?|Appendices|Appendix|Equations?|Eqs?\.?)\s+"
        r"[A-Za-z0-9.-]+(?:\s*(?:[-–]|and|to|,)\s*[A-Za-z0-9.-]+)*",
        re.I,
    ),
    re.compile(r"\\(?:ref|eqref|autoref|label)\{[^{}]+\}"),
)

IDENTIFIER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bNCT\d{8}\b", re.I),
    re.compile(r"\bRRID\s*:\s*[A-Za-z0-9_:\-.]+\b", re.I),
    re.compile(r"\b(?:ISRCTN|ACTRN|ChiCTR)[A-Za-z0-9-]+\b", re.I),
    re.compile(r"\b(?:v\d+\.\d+(?:\.\d+)*|\d+\.\d+\.\d+)(?:[-+][A-Za-z0-9.-]+)?\b", re.I),
    re.compile(
        r"\b(?=[A-Za-z0-9-]{4,}\b)(?=[A-Za-z0-9-]*[A-Za-z])"
        r"(?=[A-Za-z0-9-]*\d)[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*\b"
    ),
)

CODE_SPAN_RE = re.compile(r"(?<!`)`(?!`)[^`\n]+(?<!`)`(?!`)")

UNIT_VALUE_RE = re.compile(
    rf"(?<![\w.])({NUMBER_TOKEN})\s*"
    r"(cells/(?:µL|μL|uL|mL|L)|CFU/(?:µL|μL|uL|mL|L)|copies/(?:µL|μL|uL|mL|L)|"
    r"(?:mg|µg|μg|mcg|g)/kg(?:/day|/h)?|(?:mL|L)/min|"
    r"mg/dL|g/dL|mmol/L|µmol/L|μmol/L|umol/L|nmol/L|mol/L|mEq/L|"
    r"ng/mL|pg/mL|µg/mL|μg/mL|mcg/mL|mg/mL|g/L|"
    r"IU|U|mEq|mol|mmol|µmol|μmol|umol|nmol|pmol|M|mM|µM|μM|uM|nM|pM|"
    r"kcal|kJ|mg|kg|g|µg|μg|mcg|mL|µL|μL|uL|L|mmHg|bpm|"
    r"cm|mm|µm|μm|nm|°C|K|ms|s|min|h|hours?|days?|weeks?|months?|years?)"
    r"(?![A-Za-z0-9])",
    re.I,
)

DENOMINATOR_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"\b{NUMBER_TOKEN}\s*/\s*{NUMBER_TOKEN}\b"),
    re.compile(rf"\b{NUMBER_TOKEN}\s+(?:of|out of|per)\s+{NUMBER_TOKEN}\b", re.I),
)

INEQUALITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"(?:<=|>=|≤|≥|<|>)\s*{NUMBER_TOKEN}"),
    re.compile(
        rf"\b(?:at least|at most|more than|less than|fewer than|greater than|"
        rf"no more than|no fewer than)\s+{NUMBER_TOKEN}\b",
        re.I,
    ),
)

STATISTICAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        rf"\b(?:adjusted\s+)?(?:odds ratio|hazard ratio|risk ratio|rate ratio|"
        rf"risk difference|mean difference|OR|HR|RR|IRR|aOR|aHR)\s*[:=]?\s*{NUMBER_TOKEN}",
        re.I,
    ),
    re.compile(
        rf"\b(?:\d+(?:\.\d+)?%\s*)?(?:CI|confidence interval|credible interval)"
        rf"\s*[:,]?\s*(?:from\s+)?{NUMBER_TOKEN}\s*(?:to|[-–])\s*{NUMBER_TOKEN}",
        re.I,
    ),
    re.compile(rf"\bP\s*(?:<=|>=|≤|≥|<|>|=)\s*{NUMBER_TOKEN}", re.I),
)

SEMANTIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "negation": re.compile(
        r"\b(?:no|not|without|neither|nor|never|failed to|did not|does not|cannot|can't|"
        r"isn't|aren't|wasn't|weren't|doesn't|didn't|lack(?:s|ed)? of|absence of)\b",
        re.I,
    ),
    "modality": re.compile(
        r"\b(?:may|might|could|can|likely|unlikely|possibly|perhaps|suggests?|"
        r"is consistent with|appears? to|seems? to)\b",
        re.I,
    ),
    "causal_language": re.compile(
        r"\b(?:causes?|caused|drives?|drove|leads? to|led to|results? in|resulted in|"
        r"prevents?|prevented|improves?|improved|reduces?|reduced|due to|because of|mediates?|mediated|"
        r"determines?|determined|influences?|influenced|induces?|induced|produces?|produced|promotes?|promoted)\b",
        re.I,
    ),
    "association_language": re.compile(
        r"\b(?:associated with|association between|correlates? with|correlated with|"
        r"predicts?|predicted|co-occurred with|was more common|was less common)\b",
        re.I,
    ),
    "scope": re.compile(r"\b(?:all|any|only|always|never|overall|entire|subgroup|subset|among)\b", re.I),
    "analysis_status": re.compile(
        r"\b(?:primary|secondary|exploratory|post[ -]?hoc|prespecified|pre-specified|"
        r"sensitivity|subgroup|safety|adverse|protocol amendment|reviewer requested)\b",
        re.I,
    ),
    "comparison_direction": re.compile(
        r"\b(?:higher|lower|increased?|decreased?|better|worse|superior|inferior|"
        r"noninferior|non-inferior|equivalent|no difference|similar)\b",
        re.I,
    ),
}


@dataclass(frozen=True)
class Occurrence:
    value: str
    line: int
    column: int
    snippet: str


@dataclass
class Difference:
    category: str
    value: str
    source_count: int
    revised_count: int
    source_locations: list[Occurrence]
    revised_locations: list[Occurrence]


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    if text.lstrip().startswith("%PDF-") or "\x00" in text:
        raise ValueError(f"{path}: export UTF-8 publication text before comparing documents.")
    return text


def line_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    previous = text.rfind("\n", 0, offset)
    column = offset + 1 if previous < 0 else offset - previous
    return line, column


def make_occurrence(text: str, value: str, start: int) -> Occurrence:
    line, column = line_column(text, start)
    left = max(0, start - 45)
    right = min(len(text), start + max(len(value), 1) + 70)
    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
    if left:
        snippet = "…" + snippet
    if right < len(text):
        snippet += "…"
    return Occurrence(value=value, line=line, column=column, snippet=snippet)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_number(value: str) -> str:
    return value.replace("−", "-").replace(",", "")


def normalize_citation(value: str) -> str:
    value = normalize_space(value).replace("–", "-")
    value = re.sub(r"\s*([,;{}\[\]-])\s*", r"\1", value)
    if re.match(r"^10\.\d{4,9}/", value, re.I):
        value = value.rstrip(".,;:")
        while value.endswith(")") and value.count(")") > value.count("("):
            value = value[:-1]
    return value


def normalize_general(value: str) -> str:
    return normalize_space(value).replace("−", "-").replace("–", "-")


def normalize_cross_reference(value: str) -> str:
    return normalize_general(value).rstrip(".,;:")


def collect_matches(
    text: str,
    patterns: Iterable[re.Pattern[str]],
    normalizer=normalize_general,
) -> tuple[Counter[str], dict[str, list[Occurrence]], list[tuple[int, int]]]:
    counter: Counter[str] = Counter()
    locations: dict[str, list[Occurrence]] = defaultdict(list)
    spans: list[tuple[int, int]] = []
    seen_spans: set[tuple[int, int]] = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            if match.span() in seen_spans:
                continue
            seen_spans.add(match.span())
            raw = match.group(0)
            value = normalizer(raw)
            counter[value] += 1
            locations[value].append(make_occurrence(text, value, match.start()))
            spans.append(match.span())
    return counter, locations, spans


def mask_spans(text: str, spans: Iterable[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for index in range(max(0, start), min(len(chars), end)):
            if chars[index] != "\n":
                chars[index] = " "
    return "".join(chars)


def collect_single_pattern(
    text: str,
    pattern: re.Pattern[str],
    normalizer=normalize_general,
) -> tuple[Counter[str], dict[str, list[Occurrence]]]:
    counter: Counter[str] = Counter()
    locations: dict[str, list[Occurrence]] = defaultdict(list)
    for match in pattern.finditer(text):
        raw = match.group(0)
        value = normalizer(raw)
        counter[value] += 1
        locations[value].append(make_occurrence(text, value, match.start()))
    return counter, locations


def table_cells(line: str) -> list[str]:
    """Simple pipe tables only. Leave code and escaped delimiters to source review."""
    if "|" not in line or r"\|" in line or "`" in line:
        return []
    return [cell.strip() for cell in line.strip().removeprefix("|").removesuffix("|").split("|")]


def table_number_inventory(text: str) -> tuple[Counter[str], dict[str, list[Occurrence]]]:
    """Bind numeric entries to both labels so moving a value between arms is visible."""
    counter: Counter[str] = Counter()
    locations: dict[str, list[Occurrence]] = defaultdict(list)
    lines = text.splitlines()
    for index in range(1, len(lines)):
        divider = table_cells(lines[index])
        if len(divider) < 2 or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in divider):
            continue
        headers = table_cells(lines[index - 1])
        if len(headers) != len(divider) or not all(headers[1:]) or len(set(headers[1:])) != len(headers[1:]):
            continue
        for row_index in range(index + 1, len(lines)):
            line = lines[row_index]
            if "|" not in line:
                break
            cells = table_cells(line)
            if len(cells) != len(headers) or not cells[0]:
                continue
            start = line.index(cells[0]) + len(cells[0])
            for header, cell in zip(headers[1:], cells[1:]):
                column = line.index(cell, start)
                start = column + len(cell)
                if not re.match(r"(?:[Pp]\s*)?(?:[<>]=?|[≤≥=])?\s*[+−.\d-]", cell):
                    continue
                numbers = []
                for match in NUMBER_RE.finditer(cell):
                    operator = re.search(r"([<>]=?|[=≤≥])\s*$", cell[:match.start()])
                    qualifier = operator.group(1) if operator else ""
                    numbers.append(qualifier + normalize_number(match.group()))
                if numbers:
                    key = " | ".join([normalize_space(cells[0]), normalize_space(header), " ".join(numbers)])
                    counter[key] += 1
                    locations[key].append(Occurrence(key, row_index + 1, column + 1, line.strip()))
    return counter, locations


def inventory(text: str) -> dict[str, tuple[Counter[str], dict[str, list[Occurrence]]]]:
    result: dict[str, tuple[Counter[str], dict[str, list[Occurrence]]]] = {}

    result["labeled_table_numbers"] = table_number_inventory(text)
    citations, citation_locations, citation_spans = collect_matches(text, CITATION_PATTERNS, normalize_citation)
    equations, equation_locations, equation_spans = collect_matches(text, EQUATION_PATTERNS, normalize_general)
    result["citations_and_identifiers"] = (citations, citation_locations)
    result["equations"] = (equations, equation_locations)

    masked = mask_spans(text, [*citation_spans, *equation_spans])
    numbers, number_locations = collect_single_pattern(masked, NUMBER_RE, normalize_number)
    result["numbers"] = (numbers, number_locations)

    unit_values, unit_locations = collect_single_pattern(masked, UNIT_VALUE_RE, normalize_general)
    result["number_unit_pairs"] = (unit_values, unit_locations)

    denominators, denominator_locations, _ = collect_matches(masked, DENOMINATOR_PATTERNS, normalize_general)
    result["denominators"] = (denominators, denominator_locations)

    inequalities, inequality_locations, _ = collect_matches(masked, INEQUALITY_PATTERNS, normalize_general)
    result["inequalities"] = (inequalities, inequality_locations)

    statistics, statistic_locations, _ = collect_matches(masked, STATISTICAL_PATTERNS, normalize_general)
    result["statistical_spans"] = (statistics, statistic_locations)

    crossrefs, crossref_locations, _ = collect_matches(masked, CROSS_REFERENCE_PATTERNS, normalize_cross_reference)
    result["cross_references"] = (crossrefs, crossref_locations)

    identifiers, identifier_locations, _ = collect_matches(masked, IDENTIFIER_PATTERNS, normalize_general)
    result["registry_and_version_identifiers"] = (identifiers, identifier_locations)

    code_spans, code_locations = collect_single_pattern(masked, CODE_SPAN_RE, normalize_general)
    result["inline_code_and_defined_tokens"] = (code_spans, code_locations)
    return result


def semantic_inventory(text: str) -> dict[str, tuple[Counter[str], dict[str, list[Occurrence]]]]:
    result: dict[str, tuple[Counter[str], dict[str, list[Occurrence]]]] = {}
    for category, pattern in SEMANTIC_PATTERNS.items():
        counter: Counter[str] = Counter()
        locations: dict[str, list[Occurrence]] = defaultdict(list)
        for match in pattern.finditer(text):
            value = normalize_space(match.group(0)).lower()
            counter[value] += 1
            locations[value].append(make_occurrence(text, value, match.start()))
        result[category] = (counter, locations)
    return result


def compare_inventories(
    source: dict[str, tuple[Counter[str], dict[str, list[Occurrence]]]],
    revised: dict[str, tuple[Counter[str], dict[str, list[Occurrence]]]],
) -> list[Difference]:
    differences: list[Difference] = []
    for category in sorted(set(source) | set(revised)):
        source_counter, source_locations = source.get(category, (Counter(), {}))
        revised_counter, revised_locations = revised.get(category, (Counter(), {}))
        for value in sorted(set(source_counter) | set(revised_counter)):
            if source_counter[value] == revised_counter[value]:
                continue
            differences.append(
                Difference(
                    category=category,
                    value=value,
                    source_count=source_counter[value],
                    revised_count=revised_counter[value],
                    source_locations=list(source_locations.get(value, []))[:5],
                    revised_locations=list(revised_locations.get(value, []))[:5],
                )
            )
    return differences


def compare_texts(source_text: str, revised_text: str) -> dict[str, object]:
    protected = compare_inventories(inventory(source_text), inventory(revised_text))
    semantic = compare_inventories(semantic_inventory(source_text), semantic_inventory(revised_text))
    return {
        "notice": (
            "Differences require human review. A clean report does not prove semantic equivalence, "
            "citation-scope preservation, terminology identity, number-to-claim or operator attachment, "
            "or scientific correctness."
        ),
        "protected_differences": protected,
        "semantic_risk_differences": semantic,
    }


def serialize_report(report: dict[str, object]) -> dict[str, object]:
    return {
        "notice": report["notice"],
        "protected_differences": [asdict(item) for item in report["protected_differences"]],
        "semantic_risk_differences": [asdict(item) for item in report["semantic_risk_differences"]],
    }


def render_locations(locations: list[Occurrence]) -> str:
    if not locations:
        return "none"
    return ", ".join(f"L{item.line}:C{item.column}" for item in locations)


def render_text(report: dict[str, object], source: Path, revised: Path) -> str:
    protected: list[Difference] = report["protected_differences"]
    semantic: list[Difference] = report["semantic_risk_differences"]
    lines = [
        "Biomedical revision invariant check",
        f"Source: {source}",
        f"Revised: {revised}",
        str(report["notice"]),
        "",
        f"Protected-content differences: {len(protected)}",
    ]
    if not protected:
        lines.append("  None detected.")
    else:
        for item in protected:
            lines.append(
                f"  - [{item.category}] {item.value!r}: source={item.source_count} "
                f"({render_locations(item.source_locations)}), revised={item.revised_count} "
                f"({render_locations(item.revised_locations)})"
            )
    lines.extend(["", f"Semantic-risk marker differences: {len(semantic)}"])
    if not semantic:
        lines.append("  None detected.")
    else:
        for item in semantic:
            lines.append(
                f"  - [{item.category}] {item.value!r}: source={item.source_count} "
                f"({render_locations(item.source_locations)}), revised={item.revised_count} "
                f"({render_locations(item.revised_locations)})"
            )
    return "\n".join(lines).rstrip() + "\n"


def exit_code(report: dict[str, object]) -> int:
    if report["protected_differences"]:
        return 1
    if report["semantic_risk_differences"]:
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Original UTF-8 text/Markdown/LaTeX file.")
    parser.add_argument("--revised", required=True, type=Path, help="Revised UTF-8 text/Markdown/LaTeX file.")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON.")
    args = parser.parse_args()

    try:
        source_text = read_text(args.source)
        revised_text = read_text(args.revised)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    report = compare_texts(source_text, revised_text)
    if args.json:
        json.dump(serialize_report(report), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(report, args.source, args.revised))
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
