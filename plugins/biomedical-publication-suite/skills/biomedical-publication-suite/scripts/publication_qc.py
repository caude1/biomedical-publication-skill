#!/usr/bin/env python3
"""QC biomedical manuscript packages and publication-facing artifacts."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path


CLAIM_HEADER = [
    "claim_id",
    "artifact",
    "section",
    "claim_text",
    "claim_type",
    "support_type",
    "source_file",
    "source_locator",
    "result_id",
    "source_id",
    "extraction_id",
    "citation_locator",
    "verify_status",
    "status",
    "notes",
]

RESULTS_HEADER = [
    "result_id",
    "outcome_type",
    "outcome_name",
    "population",
    "model_label",
    "estimate_type",
    "estimate",
    "ci_lower",
    "ci_upper",
    "p_value",
    "n_total",
    "n_events",
    "time_at_risk",
    "unit",
    "source_file",
    "source_locator",
    "notes",
]

LITERATURE_HEADER = [
    "source_id",
    "status",
    "screening_status",
    "title",
    "authors",
    "year",
    "journal",
    "pmid",
    "doi",
    "registry_id",
    "publication_type",
    "source_url",
    "discovery_source",
    "discovery_query",
    "verify_status",
    "verification_source",
    "include_decision",
    "exclusion_reason",
    "notes",
]

EXTRACTION_HEADER = [
    "extraction_id",
    "source_id",
    "field_group",
    "field_name",
    "field_value",
    "unit",
    "denominator",
    "timepoint",
    "comparison",
    "source_type",
    "source_locator",
    "source_quote",
    "extractor",
    "confidence",
    "status",
    "notes",
]

CORE_FILES_TIER1 = [
    "publication_context.yaml",
    "study_facts.md",
    "open_items.md",
]

CORE_FILES_TIER2 = [
    *CORE_FILES_TIER1,
    "narrative_brief.md",
    "manuscript.md",
]

PUBLICATION_FILES = [
    "manuscript.md",
    "abstract.md",
    "titles.md",
    "cover_letter.md",
    "response_to_reviewers.md",
]


@dataclass
class Finding:
    level: str
    target: str
    message: str


GLOBAL_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "WARN",
        re.compile(
            r"\b(repo|repository|analysis workflow|project workflow|project narrative|skill|agent log|package directory|"
            r"analysis pipeline|notebook|script|codebase|control surface|claim register|results ledger|"
            r"open items|QC report|manuscript package|analysis spine|author check|quarantined)\b",
            re.I,
        ),
        "Possible internal process language in publication-facing text.",
    ),
    (
        "WARN",
        re.compile(
            r"\b(TBD|pending|placeholder|to be confirmed|authors will confirm|to be added|"
            r"will be inserted|IRB status pending|p-values will be inserted|demographics to be added)\b",
            re.I,
        ),
        "Missing-information language belongs in open_items.md or author notes, not publication text.",
    ),
    (
        "WARN",
        re.compile(
            r"\b(changed from|switched|updated analysis|revised model|demoted|elevated|"
            r"final model|final cohort|frozen cohort|locked cohort|cleanest|clearest|"
            r"we (decided|chose|opted|elected) to)\b",
            re.I,
        ),
        "Possible analysis-history leakage.",
    ),
    (
        "WARN",
        re.compile(
            r"\b(shown with reduced opacity|few patients|limited sample size|small group in this figure|"
            r"interpret cautiously|caution is warranted)\b",
            re.I,
        ),
        "Sparse-data or visual-design commentary should use counts, intervals, thresholds, captions, or footnotes.",
    ),
    (
        "INFO",
        re.compile(
            r"\b(strikingly|remarkably|"
            r"compelling|transformative|groundbreaking|impactful)\b",
            re.I,
        ),
        "Candidate importance-language signal; review whether the result and implication can carry the claim without it.",
    ),
    (
        "INFO",
        re.compile(
            r"\b(delve|intricate|realm|ecosystem|tapestry|holistic|multifaceted|"
            r"rapidly evolving|leverage|unlock|seamless|shed light|deep dive|"
            r"paves the way|adds to the growing body of literature)\b",
            re.I,
        ),
        "Candidate formulaic-language signal; revise only when the wording obscures the actual scientific variables, result, or implication.",
    ),
    (
        "WARN",
        re.compile(
            r"\b(first|next|then|subsequently),?\s+we\b|"
            r"\bwe\s+(then|proceeded to|went on to|were able to|successfully)\b|"
            r"\bthis\s+(analysis|study|figure|section)\s+(shows|demonstrates|was designed|will)\b|"
            r"\b(for completeness|as a sanity check)\b",
            re.I,
        ),
        "Memo voice found; state the current method or result without narrating the work process.",
    ),
]

UNAMBIGUOUS_CAUSAL_RE = re.compile(
    r"\b(?:causes|caused|drives|drove|leads? to|led to|results? in|resulted in|"
    r"rescues|rescued|protects? against|protected against|proves?|proved)\b",
    re.I,
)
FINITE_CAUSAL_ACTION_RE = re.compile(
    r"\b(?:reduce|improve|prevent|increase|decrease|lower|raise|worsen|enhance|"
    r"reduces|improves|prevents|increases|decreases|lowers|raises|worsens|enhances|"
    r"reduced|improved|prevented|increased|decreased|lowered|raised|worsened|enhanced)\s+"
    r"(?!(?:after|before|over|during|among|within|between|from|by|in|with|at|because|due)\b)"
    r"(?![A-Za-z-]+ly\b)(?:the\s+)?[A-Za-z]",
    re.I,
)
CURRENT_STUDY_RE = re.compile(
    r"\b(?:our\s+(?:study|analysis|cohort|registry|data|results|findings)|"
    r"we\s+(?:found|observed|showed|demonstrated|report(?:ed)?)|"
    r"this\s+(?:study|analysis|cohort|registry|investigation|trial)|"
    r"(?:the\s+)?(?:present|current)\s+(?:study|analysis|cohort)|"
    r"in\s+(?:our|this)\s+(?:study|analysis|cohort|registry)|"
    r"these\s+(?:results|findings|data))\b",
    re.I,
)
EXTERNAL_EXPERIMENT_RE = re.compile(
    r"\b(?:a|an|prior|previous|published|earlier)\b[^.!?]{0,60}"
    r"\b(?:randomi[sz]ed|controlled|experimental)\b[^.!?]{0,30}\b(?:trial|study|experiment)s?\b|"
    r"\b(?:randomi[sz]ed|controlled)\s+(?:clinical\s+)?trials?\b|"
    r"\bprior\s+(?:clinical\s+)?trials?\b",
    re.I,
)
STACKED_HEDGE_RE = re.compile(
    r"\b(may|might|could)\s+(?:\w+\s+){0,3}(potentially|possibly|conceivably|suggest|indicate)\b",
    re.I,
)
CONCESSIVE_OPENER_RE = re.compile(
    r"^\s*(although|admittedly|to be sure|it should be (noted|acknowledged)|"
    r"we acknowledge)\b",
    re.I,
)
AMBIGUOUS_CAUSAL_RE = re.compile(r"\b(due to|because of)\b|(?<!-)\bmediated\b", re.I)
BOILERPLATE_LIMITATIONS_RE = re.compile(
    r"our study has several limitations|this study is not without limitations|"
    r"future (research|studies) (is|are) (needed|warranted)|additional studies are warranted|"
    r"to the best of our knowledge",
    re.I,
)
NONSIGNIFICANCE_EQUIVALENCE_RE = re.compile(
    r"\b(?:non[- ]?significant|did not reach statistical significance|P\s*[=>]\s*\.?\d+)\b"
    r"[^.!?]{0,140}\b(?:equivalent|equivalence|similar|similarity|comparable|comparability|"
    r"no effect|no association|no difference|did not differ)\b|"
    r"\b(?:equivalent|equivalence|similar|similarity|comparable|comparability|"
    r"no effect|no association|no difference|did not differ)\b"
    r"[^.!?]{0,140}\b(?:non[- ]?significant|P\s*[=>]\s*\.?\d+)\b",
    re.I,
)
NON_EQUIVALENCE_CAVEAT_RE = re.compile(
    r"\b(?:(?:did|does|do|can|could|should|would|may|might)\s+not|cannot|can't)\s+"
    r"(?:establish|demonstrate|show|prove|support|imply|confirm|justify)\b"
    r"[^.!?]{0,60}\b(?:equivalent|equivalence|similar|similarity|comparable|comparability|"
    r"no effect|no association|no difference|did not differ)\b|"
    r"\b(?:did|does|do)\s+not\s+mean\b[^.!?]{0,60}"
    r"\b(?:equivalent|equivalence|similar|similarity|comparable|comparability|"
    r"no effect|no association|no difference|did not differ)\b|"
    r"\b(?:was|were|is|are)\s+not\s+equivalent\b",
    re.I,
)
EQUIVALENCE_DESIGN_RE = re.compile(
    r"\b(?:equivalence|non[- ]?inferiority)\s+(?:trial|design|margin|analysis|test)\b|"
    r"\bprespecified\s+(?:equivalence|non[- ]?inferiority)\s+margin\b",
    re.I,
)
STYLE_SIGNAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(?:experts believe|experts agree|researchers agree|the literature shows|studies show|it is widely recognized)\b", re.I),
        "Vague attribution found; name and verify the evidence base or narrow the claim.",
    ),
    (
        re.compile(r",\s*(?:highlighting|underscoring|showcasing|demonstrating|reflecting)\b", re.I),
        "Trailing inference clause found; verify that it adds a supported inference rather than empty importance.",
    ),
    (
        re.compile(r"\b(?:not only\b[^.!?]{0,100}\bbut also|not merely\b[^.!?]{0,100}\bbut)\b", re.I),
        "Formulaic contrast found; keep it only when the contrast corrects a real scientific distinction.",
    ),
    (
        re.compile(r"\b(?:paves the way|the future (?:looks|remains) promising|despite these challenges|further research is needed)\b", re.I),
        "Generic conclusion language found; name the supported implication or the specific unanswered question.",
    ),
    (
        re.compile(r"\b(?:certainly|great question|I hope this helps|would you like me to|let me know)\b", re.I),
        "Chatbot residue found in publication-facing text.",
    ),
    (
        re.compile(r"(?:^|[.!?]\s+)This\s+(?:is|was|shows|demonstrates|suggests|indicates)\b", re.I),
        "Potentially vague sentence-initial 'This' found; name the result or concept when more than one referent is plausible.",
    ),
    (
        re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b"),
        "Raw snake_case identifier found; translate internal variable names when this is publication prose.",
    ),
    (
        re.compile(r"\b(?:our findings|these findings|the findings)\s+(?:indicate|demonstrate|show)\s+that\b", re.I),
        "Distanced result framing found; consider naming the study, analysis, exposure, or result directly.",
    ),
]
BRACKET_CITATION_RE = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
DOI_OR_PMID_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+|PMID\s*:?\s*\d+)", re.I)
PANDOC_CITATION_RE = re.compile(r"\[[^\]]*@[A-Za-z0-9_.:\-/]+[^\]]*\]")
LATEX_CITATION_RE = re.compile(r"\\cite[a-zA-Z*]*\{[^{}]+\}")
AUTHOR_YEAR_CITATION_RE = re.compile(
    r"\((?:[A-Z][A-Za-z'’-]+(?:\s+(?:et\s+al\.|(?:&|and)\s+[A-Z][A-Za-z'’-]+))?,?\s+"
    r"\d{4}[a-z]?(?:\s*;\s*)?)+\)|"
    r"\b[A-Z][A-Za-z'’-]+(?:\s+(?:et\s+al\.|(?:&|and)\s+[A-Z][A-Za-z'’-]+))?\s+"
    r"\(\d{4}[a-z]?\)",
)
ESTIMATE_RE = re.compile(
    r"\b(OR|HR|RR|IRR|ARR|aOR|AUC|AUROC|C-statistic|CI|p\s*[<=>]|median|mean|"
    r"n\s*=|\d+(?:\.\d+)?%|\d+/\d+)\b",
    re.I,
)
NUMERIC_EXTRACTION_RE = re.compile(
    r"\b(sample|n_|n\b|number|outcome|event|effect|estimate|rate|risk|odds|hazard|mean|median|"
    r"proportion|percent|percentage|adverse|mortality|survival|follow[- ]?up)\b",
    re.I,
)
SECTION_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def read_text(path: Path) -> str:
    with path.open(encoding="utf-8-sig") as handle:
        try:
            text = handle.read()
        except UnicodeDecodeError as exc:
            raise ValueError(f"{path}: expected UTF-8 text. Export document text before linting.") from exc
    if text.lstrip().startswith("%PDF-") or "\x00" in text:
        raise ValueError(f"{path}: binary or unsupported text encoding. Export UTF-8 text before linting.")
    return text


def substantive_word_count(text: str) -> int:
    """Count prose words after removing headings, comments, and empty placeholders."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^\s{0,3}#{1,6}\s+.*$", " ", text, flags=re.M)
    text = re.sub(r"\[[^\]]*(?:TODO|TBD|placeholder|to be added)[^\]]*\]", " ", text, flags=re.I)
    return len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", text))


def normalize_section(name: str) -> str:
    cleaned = name.replace(chr(96), "")
    cleaned = re.sub(r"[*_#]", "", cleaned).strip().lower()
    cleaned = re.sub(r"[^a-z0-9 /-]+", "", cleaned)
    if "abstract" in cleaned:
        return "abstract"
    if "introduction" in cleaned or "background" in cleaned:
        return "introduction"
    if "method" in cleaned:
        return "methods"
    if "result" in cleaned or "finding" in cleaned:
        return "results"
    if "discussion" in cleaned:
        return "discussion"
    if "limitation" in cleaned:
        return "limitations"
    if "conclusion" in cleaned:
        return "conclusion"
    return cleaned or "body"


def split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_HEADER_RE.finditer(text))
    if not matches:
        return [("body", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("body", text[: matches[0].start()]))
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append((normalize_section(match.group(2)), text[start:end]))
    return sections


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]


def has_observational_causal_language(text: str) -> bool:
    """Flag finite causal predicates while sparing common adjectival/associational uses."""
    if UNAMBIGUOUS_CAUSAL_RE.search(text):
        return True
    for match in FINITE_CAUSAL_ACTION_RE.finditer(text):
        verb = match.group(0).split()[0].lower()
        if verb.endswith("s"):
            return True
        prefix = text[max(0, match.start() - 80) : match.start()]
        if re.search(
            r"\b(?:associated with|linked to|correlated with|corresponded to|characterized by|"
            r"has|have|had|showed|demonstrated|experienced|found|observed|estimated|predicted|"
            r"yielded|included|using)\s+"
            r"(?:[A-Za-z-]+ly\s+)?$",
            prefix,
            re.I,
        ):
            continue
        if re.search(r"\b(?:a|an|the|was|were|is|are|be|been|being)\s+$", prefix, re.I):
            continue
        return True
    return False


def observational_causal_level(text: str, section_name: str) -> str | None:
    """Classify causal wording for an observational manuscript by sentence and section."""
    level: str | None = None
    own_study_sections = {"abstract", "results", "conclusion", "body"}
    for sentence in split_sentences(text):
        if not has_observational_causal_language(sentence):
            continue
        if CURRENT_STUDY_RE.search(sentence):
            return "ERROR"
        if EXTERNAL_EXPERIMENT_RE.search(sentence):
            continue
        if section_name in own_study_sections:
            return "ERROR"
        level = "WARN"
    return level


def context_forbids_causal(context_path: Path) -> bool:
    if not context_path.exists():
        return False
    text = read_text(context_path)
    direct = re.search(r"causal_language_allowed\s*:\s*(false|no)\b", text, re.I)
    nested = re.search(
        r"causal_language_allowed\s*:\s*\n(?:\s+[^\n]*\n){0,6}\s+value\s*:\s*(false|no)\b",
        text,
        re.I,
    )
    return bool(direct or nested)


def citation_group_count(group: str) -> int:
    total = 0
    for piece in re.split(r"\s*,\s*", group):
        if "-" in piece:
            left, right = [p.strip() for p in piece.split("-", 1)]
            if left.isdigit() and right.isdigit():
                total += max(1, int(right) - int(left) + 1)
            else:
                total += 1
        elif piece.strip().isdigit():
            total += 1
    return total


def check_citation_bloat(text: str, target: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in BRACKET_CITATION_RE.finditer(text):
        if citation_group_count(match.group(1)) >= 4:
            findings.append(
                Finding(
                    "INFO",
                    target,
                    "Citation cluster with four or more references found; verify each citation earns its place.",
                )
            )
    for sentence in split_sentences(text):
        if len(BRACKET_CITATION_RE.findall(sentence)) >= 2:
            findings.append(
                Finding(
                    "INFO",
                    target,
                    "Sentence contains multiple citation groups; consider consolidating or assigning claims more precisely.",
                )
            )
            break
    return findings


def lint_publication_text(text: str, target: str, observational: bool) -> list[Finding]:
    findings: list[Finding] = []
    response_document = "response_to_reviewers" in target.lower()
    for level, pattern, message in GLOBAL_PATTERNS:
        if response_document and message == "Possible analysis-history leakage.":
            continue
        if pattern.search(text):
            findings.append(Finding(level, target, message))
    if STACKED_HEDGE_RE.search(text):
        findings.append(
            Finding(
                "WARN",
                target,
                "Stacked hedging found; keep uncertainty precise and localized.",
            )
        )
    if BOILERPLATE_LIMITATIONS_RE.search(text):
        findings.append(
            Finding(
                "WARN",
                target,
                "Boilerplate limitations language found; name actual limitations and likely bias direction.",
            )
        )
    nonsignificance_misuse = any(
        NONSIGNIFICANCE_EQUIVALENCE_RE.search(sentence)
        and not NON_EQUIVALENCE_CAVEAT_RE.search(sentence)
        for sentence in split_sentences(text)
    )
    if nonsignificance_misuse:
        equivalence_design_present = bool(EQUIVALENCE_DESIGN_RE.search(text))
        findings.append(
            Finding(
                "WARN" if equivalence_design_present else "ERROR",
                target,
                (
                    "Equivalence or noninferiority language appears with nonsignificance in a named equivalence/noninferiority design; verify the prespecified margin, analysis, and confidence interval before retaining the conclusion."
                    if equivalence_design_present
                    else "Nonsignificance is being used to claim equivalence, similarity, comparability, no effect, no association, or no difference; report the estimate and uncertainty unless an appropriate equivalence or noninferiority design supports the claim."
                ),
            )
        )
    for pattern, message in STYLE_SIGNAL_PATTERNS:
        if pattern.search(text):
            findings.append(Finding("INFO", target, message))
    findings.extend(check_citation_bloat(text, target))

    for section_name, body in split_sections(text):
        section_target = f"{target} [{section_name}]"
        causal_level = None
        if observational and section_name not in {"methods", "limitations", "references"}:
            causal_level = observational_causal_level(body, section_name)
        if causal_level:
            findings.append(
                Finding(
                    causal_level,
                    section_target,
                    (
                        "Causal language describing the current study was found while observational/nonexperimental language discipline is active."
                        if causal_level == "ERROR"
                        else "Causal language in an Introduction or Discussion sentence could describe external experimental evidence or could overstate observational evidence; verify the cited design and attribution."
                    ),
                )
            )
        if section_name in {"abstract", "results"}:
            for sentence in split_sentences(body):
                if CONCESSIVE_OPENER_RE.search(sentence):
                    findings.append(
                        Finding(
                            "WARN",
                            section_target,
                            "Concessive sentence opener found in a high-momentum section; avoid leading with caveats.",
                        )
                    )
                    break
        if observational and section_name not in {"methods", "limitations", "references"}:
            if AMBIGUOUS_CAUSAL_RE.search(body):
                findings.append(
                    Finding(
                        "WARN",
                        section_target,
                        "Potentially causal phrasing found; keep it only when it is literal endpoint language, field-standard terminology, or otherwise design-appropriate.",
                    )
                )
        if section_name == "results":
            early = [s for s in split_sentences(body) if len(s.split()) >= 6][:2]
            if early and not any(ESTIMATE_RE.search(s) for s in early):
                findings.append(
                    Finding(
                        "INFO",
                        section_target,
                        "Opening Results sentences contain no counts, estimates, or intervals; verify the section leads with findings.",
                    )
                )
    return findings


def check_citations(text: str, target: str, require_citations: bool) -> list[Finding]:
    findings: list[Finding] = []
    has_citation = any(
        pattern.search(text)
        for pattern in (
            BRACKET_CITATION_RE,
            DOI_OR_PMID_RE,
            PANDOC_CITATION_RE,
            LATEX_CITATION_RE,
            AUTHOR_YEAR_CITATION_RE,
        )
    )
    if require_citations and not has_citation:
        findings.append(
            Finding(
                "ERROR",
                target,
                "No recognized numeric, author-year, Pandoc, or LaTeX citation marker, DOI, or PMID found while citation enforcement is active.",
            )
        )
    return findings


def read_register(path: Path, required: list[str], findings: list[Finding]) -> list[dict[str, str]]:
    """Read each optional register once and reject malformed links before inspecting values."""
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            header = reader.fieldnames or []
            if len(header) != len(set(header)) or not all(h.strip() for h in header) or not set(required).issubset(header):
                raise ValueError(f"Missing, blank or duplicate CSV columns. Required: {','.join(required)}")
            rows = list(reader)
            if any(None in row or None in row.values() for row in rows):
                raise ValueError("CSV row width does not match header.")
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        findings.append(Finding("ERROR", str(path), str(exc)))
        return []
    seen = set()
    for index, row in enumerate(rows, 2):
        key = row[required[0]].strip()
        if not key or key in seen:
            findings.append(Finding("ERROR", f"{path}:{index}", f"Blank or duplicate {required[0]}."))
        seen.add(key)
    return rows


def check_registers(package: Path, require_claims: bool, blocking: bool) -> list[Finding]:
    level = "ERROR" if blocking else "WARN"
    findings: list[Finding] = []
    claim_path = package / "claim_register.csv"
    literature_path = package / "literature_register.csv"
    extraction_path = package / "extraction_ledger.csv"
    claims = read_register(claim_path, CLAIM_HEADER, findings)
    results = read_register(package / "results_ledger.csv", RESULTS_HEADER, findings)
    literature = read_register(literature_path, LITERATURE_HEADER, findings)
    extractions = read_register(extraction_path, EXTRACTION_HEADER, findings)
    result_ids = {row["result_id"].strip() for row in results}
    verified_sources = {row["source_id"].strip() for row in literature if row["verify_status"].strip().lower() == "verified"}

    if require_claims and not claims:
        findings.append(Finding("ERROR", str(claim_path), "A nonempty claim register is required."))
    for idx, row in enumerate(claims, 2):
        target = f"{claim_path}:{idx}"
        status = row["status"].strip().lower()
        support = row["support_type"].strip().lower()
        source_id = row["source_id"].strip()
        result_id = row["result_id"].strip()
        has_source = (
            row["source_file"].strip()
            or (support == "external_citation" and source_id)
            or (support == "repo_result" and result_id)
        )
        if status in {"supported", "inferred"} and (not support or not has_source):
            severity = "ERROR" if status == "supported" and support.startswith("repo_") else "WARN"
            findings.append(Finding(severity, target, "Claim lacks a support type or a source appropriate to that type."))
        if status in {"unsupported_remove_or_weaken", "unsupported", "conflict"}:
            findings.append(Finding("ERROR", target, f"Claim is marked {status}; reconcile its evidence before publication."))
        if result_id and result_id not in result_ids:
            findings.append(Finding("ERROR", target, f"result_id {result_id!r} does not resolve in results_ledger.csv."))
        if support == "external_citation" or source_id:
            if not source_id:
                findings.append(Finding(level, target, "External citation claim lacks source_id."))
            elif source_id not in verified_sources:
                findings.append(Finding(level, target, "External citation claim does not point to a verified literature source."))

    for idx, row in enumerate(literature, 2):
        included = row["status"].strip().lower() in {"verified", "included"} or row["include_decision"].strip().lower() == "include"
        if included and row["verify_status"].strip().lower() != "verified":
            findings.append(Finding(level, f"{literature_path}:{idx}", "Included literature record lacks verified identity."))

    for idx, row in enumerate(extractions, 2):
        target = f"{extraction_path}:{idx}"
        value = row["field_value"].strip()
        if not value:
            continue
        if row["source_id"].strip() not in verified_sources:
            findings.append(Finding(level, target, "Extraction does not point to a verified literature source."))
        if not row["source_locator"].strip():
            findings.append(Finding(level, target, "Extracted value lacks source_locator."))
        if not row["source_quote"].strip():
            exception = all(row.get(key, "").strip() for key in ("quote_unavailable_reason", "source_version", "notes"))
            if exception:
                findings.append(Finding("WARN", target, "Source quote unavailable; manually check the documented source inspection."))
            else:
                findings.append(Finding(level, target, "Extracted value lacks a source quote or documented exception."))
        if re.search(r"\d", value) and NUMERIC_EXTRACTION_RE.search(row["field_name"]):
            missing = [name for name in ("denominator", "unit", "timepoint", "comparison") if not row[name].strip()]
            if missing:
                findings.append(Finding("WARN", target, "Numeric extraction is missing: " + ", ".join(missing)))
    return findings


def extract_part1_narrative(text: str) -> str:
    part1 = re.search(r"part\s*1\s*[-:]\s*(scientific|manuscript|external|project)\s+narrative", text, re.I)
    part2 = re.search(r"part\s*2\s*[-:]\s*editorial rationale", text, re.I)
    if part1 and part2 and part2.start() > part1.end():
        return text[part1.end() : part2.start()]
    if part1:
        return text[part1.end() :]
    return ""


def check_narrative_audit(path: Path, observational: bool) -> list[Finding]:
    if not path.exists():
        return []
    text = read_text(path)
    findings: list[Finding] = []
    if not re.search(r"Part\s*1\s*[-:]\s*(Scientific|Manuscript|External)\s+Narrative", text, re.I):
        findings.append(
            Finding(
                "WARN",
                str(path),
                "Narrative audit should use Part 1 - Scientific Narrative, Manuscript Narrative, or External Narrative.",
            )
        )
    if not re.search(r"Part\s*2\s*[-:]\s*Editorial Rationale", text, re.I):
        findings.append(
            Finding(
                "WARN",
                str(path),
                "Narrative audit should include Part 2 - Editorial Rationale.",
            )
        )
    part1 = extract_part1_narrative(text)
    if part1:
        findings.extend(lint_publication_text(part1, f"{path} [Part 1]", observational))
    return findings


def display_label_fields(text: str) -> list[tuple[int, str, str]]:
    """Return display fields whether values are inline or on following lines."""
    lines = text.splitlines()
    label_prefixes = ("title", "subtitle", "axis", "panel", "legend", "row label", "column header")
    fields: list[tuple[int, str, str]] = []
    for zero_index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = [part.strip() for part in stripped.split(":", 1)]
        key_norm = key.lower().strip("-* ")
        if not any(key_norm.startswith(prefix) for prefix in label_prefixes):
            continue
        if not value:
            cursor = zero_index + 1
            while cursor < len(lines) and not lines[cursor].strip():
                cursor += 1
            chunks: list[str] = []
            while cursor < len(lines):
                candidate = lines[cursor].strip()
                if not candidate or candidate.startswith("#"):
                    break
                if ":" in candidate:
                    candidate_key = candidate.split(":", 1)[0].lower().strip("-* ")
                    if any(candidate_key.startswith(prefix) for prefix in label_prefixes):
                        break
                chunks.append(candidate.lstrip("-* "))
                cursor += 1
            value = " ".join(chunks)
        fields.append((zero_index + 1, key_norm, value))
    return fields


def check_display_text(path: Path) -> list[Finding]:
    if not path.exists():
        return []
    text = read_text(path)
    findings: list[Finding] = []
    for idx, key_norm, value in display_label_fields(text):
        if key_norm.startswith("title") and len(value.split()) > 15:
            findings.append(
                Finding(
                    "WARN",
                    f"{path}:{idx}",
                    "Figure or table title is long; titles should identify, not explain.",
                )
            )
        if re.search(r"\b(because|due to|in order to|this shows|this demonstrates|we)\b", value, re.I):
            findings.append(
                Finding(
                    "WARN",
                    f"{path}:{idx}",
                    "Label-prose collapse found; move explanations to captions, footnotes, Results, or Notes.",
                )
            )
        if re.search(r"\b(limited|preliminary|caution|few patients|small sample|interpret cautiously)\b", value, re.I):
            findings.append(
                Finding(
                    "WARN",
                    f"{path}:{idx}",
                    "Caveat appears in a label field; use counts, intervals, thresholds, captions, or footnotes.",
                )
            )
    return findings


def package_findings(args: argparse.Namespace) -> list[Finding]:
    root = Path(args.repo_root).resolve()
    package = root / args.package_dir
    findings: list[Finding] = []

    if not package.exists():
        return [Finding("ERROR", str(package), "Publication package directory does not exist.")]

    core_files = CORE_FILES_TIER1 if args.tier == "1" else CORE_FILES_TIER2
    for rel in core_files:
        if not (package / rel).exists():
            findings.append(Finding("ERROR", str(package / rel), "Required core file is missing."))

    if args.stage != "scaffold" and args.tier == "2":
        content_requirements = {
            "narrative_brief.md": 20,
            "manuscript.md": 80,
        }
        for rel, minimum in content_requirements.items():
            path = package / rel
            if path.exists() and substantive_word_count(read_text(path)) < minimum:
                findings.append(
                    Finding(
                        "ERROR",
                        str(path),
                        f"{args.stage.capitalize()}-stage package requires substantive content; fewer than {minimum} prose words were found.",
                    )
                )

    observational = args.observational or context_forbids_causal(package / "publication_context.yaml")

    for rel in PUBLICATION_FILES:
        path = package / rel
        if path.exists():
            text = read_text(path)
            findings.extend(lint_publication_text(text, str(path), observational))
            findings.extend(check_citations(text, str(path), args.require_citations and rel == "manuscript.md"))

    findings.extend(check_display_text(package / "display_text.md"))
    findings.extend(check_registers(package, args.require_claim_register, args.require_literature_integrity))
    findings.extend(check_narrative_audit(package / "narrative_audit.md", observational))

    return findings


def format_report(findings: list[Finding]) -> str:
    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]
    infos = [f for f in findings if f.level == "INFO"]
    lines = [
        "# Publication QC Report",
        "",
        "This report is a mechanical tripwire, not an editor or AI-authorship detector. Findings flag patterns that may merit review; they are not edits or proof of authorship. The senior-editor read, evidence-preservation audit, and manuscript voice audit govern final wording. Do not reword sound, field-standard, or design-appropriate prose only to clear a warning.",
        "",
        f"Errors: {len(errors)}",
        f"Warnings: {len(warnings)}",
        f"Info: {len(infos)}",
        "",
    ]
    if not findings:
        lines.append("No findings.")
    else:
        for item in findings:
            lines.append(f"- {item.level}: {item.target}: {item.message}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository or project root.")
    parser.add_argument("--package-dir", default="manuscript", help="Publication package directory.")
    parser.add_argument("--tier", choices=("1", "2"), default="2", help="Package tier to validate.")
    parser.add_argument(
        "--stage",
        choices=("scaffold", "draft", "submission"),
        default="draft",
        help="Validation stage. Scaffold checks structure only; draft and submission require substantive core prose.",
    )
    parser.add_argument("--file", help="Single publication-facing artifact to lint.")
    parser.add_argument("--observational", action="store_true", help="Forbid causal language.")
    parser.add_argument(
        "--strict-confidence",
        action="store_true",
        help="Deprecated compatibility flag; confidence checks are now section-aware by default.",
    )
    parser.add_argument("--require-claim-register", action="store_true", help="Require nonempty claim register.")
    parser.add_argument("--require-citations", action="store_true", help="Require citation markers in manuscript or file.")
    parser.add_argument(
        "--require-literature-integrity",
        action="store_true",
        help="Treat unverified literature citations and ungrounded extraction rows as blocking errors.",
    )
    parser.add_argument("--fail-on-warn", action="store_true", help="Exit nonzero when warnings are present.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not update qc_report.md in package mode.")
    args = parser.parse_args()

    try:
        if args.file:
            path = Path(args.file).resolve()
            text = read_text(path)
            if not text.strip():
                raise ValueError(f"{path}: no publication text to inspect.")
            findings = lint_publication_text(text, str(path), args.observational)
            findings.extend(check_citations(text, str(path), args.require_citations))
        else:
            findings = package_findings(args)
    except (OSError, ValueError) as exc:
        findings = [Finding("ERROR", "input", str(exc))]

    if not args.file and not args.no_write_report:
        package = Path(args.repo_root).resolve() / args.package_dir
        report_path = package / "qc_report.md"
        if package.is_dir():
            try:
                if report_path.is_symlink():
                    raise ValueError("Report path is a symlink. Choose a regular file or use --no-write-report.")
                report_path.write_text(format_report(findings), encoding="utf-8")
            except (OSError, ValueError) as exc:
                findings.append(Finding("ERROR", str(report_path), str(exc)))
    print(format_report(findings))

    has_error = any(item.level == "ERROR" for item in findings)
    has_warn = any(item.level == "WARN" for item in findings)
    if has_error or (args.fail_on_warn and has_warn):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
