#!/usr/bin/env python3
"""Sanity-check reported results without recalculating analyses or inferring missing statistics."""
from __future__ import annotations
import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
RATIOS = {"or", "rr", "hr", "irr", "odds ratio", "risk ratio", "hazard ratio", "incidence rate ratio", "rate ratio", "relative risk", "aor", "ahr", "airr"}
NONNUMERIC_STATES = {"not_estimable", "not_reported", "suppressed"}
PROPORTIONS = {"proportion", "probability", "sensitivity", "specificity", "auc", "c statistic", "c-statistic", "ppv", "npv"}

# Named estimates that need an estimate, interval or P value beyond the cohort size.
MEASURE_LABEL = re.compile(
    r"\b(?:difference|change|coefficient|slope|beta|β|mean|median|correlation|"
    r"ratio|percent|percentage|proportion|probability|rate|smd|md|rd|arr|nnt|"
    r"or|hr|rr|irr)\b"
)

@dataclass
class Finding:
    level: str
    row: int
    message: str


def number(value: str) -> Decimal | None:
    value = value.strip().replace("−", "-")
    if not NUMBER_RE.fullmatch(value):
        return None
    try:
        n = Decimal(value)
        return n if n.is_finite() else None
    except InvalidOperation:
        return None


def audit(path: Path, *, strict: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
                raise ValueError("Absent, blank, or duplicate CSV header.")
            rows = list(reader)
            if any(None in row or any(v is None for v in row.values()) for row in rows):
                raise ValueError("CSV row width does not match header.")
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return [Finding("ERROR", 0, f"Input error: {exc}")]
    if "result_id" not in headers:
        return [Finding("ERROR", 1, "Missing required column: result_id.")]
    if strict and not rows:
        findings.append(Finding("WARN", 1, "The ledger contains no result rows to audit."))
    seen = set()
    for line, row in enumerate(rows, 2):
        key = (row.get("result_id") or "").strip()
        if not key or key in seen:
            findings.append(Finding("ERROR", line, "Blank or duplicate result_id."))
        seen.add(key)
        if strict:
            for field in ("source_file", "source_locator", "outcome_name", "population"):
                if not (row.get(field) or "").strip():
                    findings.append(Finding("ERROR", line, f"Submission result lacks {field}."))
        if "status" in headers and (row.get("status") or "").strip() not in {"verified", "needs_verification", "conflict", "partial"}:
            findings.append(Finding("ERROR", line, "Invalid or blank result status."))
        if strict and "status" in headers and row.get("status", "").strip() != "verified":
            findings.append(Finding("ERROR", line, "Submission result must be verified."))
        state = (row.get("result_state") or "").strip().lower() or "reported"
        raw_p = (row.get("p_value") or "").strip()
        if state not in NONNUMERIC_STATES | {"reported"}:
            findings.append(Finding("ERROR", line, f"Unrecognized result_state: {state!r}."))
        if state in NONNUMERIC_STATES:
            if any((row.get(field) or "").strip() for field in ("estimate", "ci_lower", "ci_upper", "p_value")):
                findings.append(Finding("ERROR", line, "A nonnumeric result_state conflicts with a filled estimate, interval, or P value."))
            if strict and not (row.get("notes") or "").strip():
                findings.append(Finding("ERROR", line, f"Document the reason or scope for {state} in notes."))
        origin = (row.get("value_origin") or "").strip().lower()
        if origin and origin not in {"reported", "derived"}:
            findings.append(Finding("ERROR", line, f"Unrecognized value_origin: {origin!r}."))
        if origin == "derived" and not (row.get("derivation_source") or "").strip():
            findings.append(Finding("ERROR" if strict else "WARN", line, "Derived result lacks derivation_source locating the calculation."))
        kind = (row.get("estimate_type") or "").strip().lower().replace("_", " ")
        ratio = kind.removeprefix("adjusted ") in RATIOS
        numeric = {}
        for field in ("estimate", "ci_lower", "ci_upper", "n_total", "n_events", "time_at_risk"):
            raw = (row.get(field) or "").strip()
            if not raw:
                continue
            parsed = number(raw)
            bound = raw.lower().replace("−", "-")
            if field == "ci_lower" and bound in {"-inf", "-infinity", "-∞"}:
                parsed = Decimal("-Infinity")
            if (field == "ci_upper" or (field == "estimate" and ratio)) and bound.removeprefix("+") in {"inf", "infinity", "∞"}:
                parsed = Decimal("Infinity")
            if parsed is None:
                findings.append(Finding("ERROR", line, f"{field} has an invalid numeric value: {raw!r}."))
                continue
            numeric[field] = parsed
        if strict and state == "reported" and not raw_p:
            effect_fields = {"estimate", "ci_lower", "ci_upper"}
            named_measure = ratio or kind in PROPORTIONS or MEASURE_LABEL.search(kind)
            if not numeric or (named_measure and effect_fields.isdisjoint(numeric)):
                findings.append(Finding("ERROR", line, "No value for the stated result. If unavailable, record its result_state and explanation."))
        for field in ("n_total", "n_events"):
            if field in numeric and (numeric[field] < 0 or numeric[field] != numeric[field].to_integral_value()):
                findings.append(Finding("ERROR", line, f"{field} must be a nonnegative integer count."))
        if "time_at_risk" in numeric and numeric["time_at_risk"] < 0:
            findings.append(Finding("ERROR", line, "time_at_risk cannot be negative."))
        if "n_total" in numeric and "n_events" in numeric and numeric["n_events"] > numeric["n_total"]:
            if (row.get("event_count_type") or "").strip() != "recurrent_events":
                findings.append(Finding("WARN", line, "n_events exceeds n_total; check denominators or record event_count_type=recurrent_events if supported."))
        lower, upper, estimate = (numeric.get(k) for k in ("ci_lower", "ci_upper", "estimate"))
        if (lower is None) != (upper is None):
            findings.append(Finding("WARN", line, "Only one confidence bound is supplied; verify that a one-sided interval is intended."))
        if lower is not None and upper is not None:
            if lower > upper:
                findings.append(Finding("ERROR", line, "Confidence interval bounds are reversed."))
            elif estimate is not None and not lower <= estimate <= upper:
                findings.append(Finding("WARN", line, "Estimate lies outside its confidence interval; verify interval method, scale, and transcription (some bootstrap intervals can exclude the point estimate)."))
        if ratio:
            if estimate is not None and estimate < 0:
                findings.append(Finding("ERROR", line, "Negative point estimate on the ratio scale; check the measure and any log transformation."))
            elif estimate == 0 or (estimate is not None and estimate.is_infinite()):
                findings.append(Finding("WARN", line, "Ratio estimate is zero or infinite; check boundary events, estimability, and rounding against the source."))
            if any(bound is not None and bound < 0 for bound in (lower, upper)):
                findings.append(Finding("WARN", line, "Negative ratio confidence bound; verify interval method, scale, and transcription."))
        if kind in PROPORTIONS:
            cap = Decimal(100) if (row.get("unit") or "").strip().lower() in {"%", "percent", "percentage"} else Decimal(1)
            if estimate is not None and not 0 <= estimate <= cap:
                findings.append(Finding("ERROR", line, f"Estimate is outside the declared proportion scale 0 to {cap}."))
            if any(bound is not None and not 0 <= bound <= cap for bound in (lower, upper)):
                findings.append(Finding("WARN", line, f"Confidence bound outside 0 to {cap}; check for an unbounded interval method or a scale/transcription error."))
        if raw_p:
            m = re.fullmatch(r"(?:[pP]\s*)?(<=|>=|<|>|=|≤|≥)?\s*(.+)", raw_p)
            operator, raw = m.groups() if m else (None, raw_p)
            p = number(raw)
            if p is None or not 0 <= p <= 1 or (operator == "<" and p == 0) or (operator == ">" and p == 1):
                findings.append(Finding("ERROR", line, "P value or bound must be finite and within [0,1], with a nonempty inequality range."))
            elif p == 0 and operator not in {">", ">=", "≥"}:
                findings.append(Finding("WARN", line, "Reported P=0 is usually rounding; verify original output before changing precision."))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default="manuscript/results_ledger.csv")
    parser.add_argument("--strict", "--submission", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    findings = audit(args.input, strict=args.strict)
    errors = sum(f.level == "ERROR" for f in findings)
    warnings = sum(f.level == "WARN" for f in findings)
    report = {"schema_version": 1, "audit": "results", "errors": errors, "warnings": warnings,
              "findings": [asdict(f) for f in findings], "scope": "Numeric sanity only; no analysis, source-value, or CI/P-value equivalence proof."}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Results audit: {errors} errors, {warnings} warnings")
        for f in findings:
            print(f"- {f.level}: row {f.row}: {f.message}")
    return int(bool(errors or (args.fail_on_warn and warnings)))


if __name__ == "__main__":
    raise SystemExit(main())
