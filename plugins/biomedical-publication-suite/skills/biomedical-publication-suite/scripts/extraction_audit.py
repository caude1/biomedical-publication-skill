#!/usr/bin/env python3
"""Audit extraction provenance and states; source quotes still require human or agent verification."""
from __future__ import annotations
import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_COLUMNS = ["extraction_id", "source_id", "field_group", "field_name", "field_value", "source_locator", "source_quote", "status"]
STATUSES = {"verified", "partial", "not_reported", "not_found", "unclear", "needs_full_text", "conflict"}
NUMERIC_FIELD_RE = re.compile(r"sample|\bn\b|n_|number|event|effect|estimate|rate|risk|odds|hazard|mean|median|proportion|percent|mortality|survival|follow[- ]?up", re.I)

@dataclass
class Finding:
    level: str
    row: int
    message: str


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        headers = list(reader.fieldnames or [])
        if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
            raise ValueError("Absent, blank, or duplicate CSV header.")
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError("CSV row width does not match header.")
        return headers, rows


def present(row: dict[str, str], key: str) -> bool:
    return bool((row.get(key) or "").strip())


def audit(path: Path, *, strict: bool = False, literature_register: Path | None = None) -> list[Finding]:
    findings: list[Finding] = []
    try:
        fieldnames, rows = read_rows(path)
        sources = None
        if literature_register:
            source_headers, source_rows = read_rows(literature_register)
            if "source_id" not in source_headers or "verify_status" not in source_headers:
                findings.append(Finding("ERROR", 1, "Literature register lacks source_id or verify_status column."))
            sources = {}
            for line, source in enumerate(source_rows, 2):
                key = (source.get("source_id") or "").strip()
                if not key or key in sources:
                    findings.append(Finding("ERROR", line, "Literature register has blank or duplicate source_id."))
                else:
                    sources[key] = source
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return [Finding("ERROR", 0, f"Input error: {exc}")]
    missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
    if missing:
        return findings + [Finding("ERROR", 1, "Missing required columns: " + ", ".join(missing))]
    if strict and not rows:
        findings.append(Finding("WARN", 1, "The ledger contains no extraction rows to audit."))
    seen = set()
    for row_number, row in enumerate(rows, 2):
        extraction_id = (row.get("extraction_id") or "").strip()
        if not extraction_id:
            findings.append(Finding("ERROR", row_number, "Blank extraction_id."))
        elif extraction_id in seen:
            findings.append(Finding("ERROR", row_number, f"Duplicate extraction_id: {extraction_id!r}."))
        seen.add(extraction_id)
        for key in ("source_id", "field_group", "field_name"):
            if not present(row, key):
                findings.append(Finding("ERROR", row_number, f"Missing {key}."))
        source_id = (row.get("source_id") or "").strip()
        if sources is not None and source_id:
            if source_id not in sources:
                findings.append(Finding("ERROR", row_number, f"Orphan source_id: {source_id!r}."))
            elif (sources[source_id].get("verify_status") or "").strip().lower() != "verified":
                findings.append(Finding("ERROR", row_number, "Extraction source identity is not verified."))
        status = (row.get("status") or "").strip().lower()
        value = (row.get("field_value") or "").strip()
        if status not in STATUSES:
            findings.append(Finding("ERROR", row_number, f"Invalid or blank status: {status!r}."))
        if status in {"not_reported", "not_found"} and value:
            findings.append(Finding("ERROR", row_number, f"{status} must have empty field_value; preserve absence separately from zero."))
        if status == "not_found" and not value:
            findings.append(Finding("WARN", row_number, "Legacy not_found is ambiguous. Check which source was available before calling the field unreported."))
        if strict and status == "not_reported" and not present(row, "source_locator"):
            findings.append(Finding("WARN", row_number, "Document where absence was checked before reporting that a field was unreported."))
        if status == "verified" and not value:
            findings.append(Finding("ERROR", row_number, "verified extraction has no value."))
        if value:
            if not present(row, "source_locator"):
                findings.append(Finding("ERROR", row_number, "Extracted value lacks source_locator."))
            if not present(row, "source_quote"):
                exception_fields = ("quote_unavailable_reason", "source_version", "notes")
                if all(present(row, key) for key in exception_fields):
                    findings.append(Finding("WARN", row_number, "Source quote unavailable with documented source inspection; manually verify the exact locator, version, and recorded reason."))
                else:
                    findings.append(Finding("ERROR", row_number, "Extracted value lacks source_quote or a documented quote_unavailable_reason, source_version, and inspection notes."))
            origin = (row.get("value_origin") or "").strip().lower()
            if origin and origin not in {"reported", "derived"}:
                findings.append(Finding("ERROR", row_number, f"Invalid value_origin: {origin!r}."))
            if origin == "derived" and not present(row, "derivation_source"):
                findings.append(Finding("ERROR" if strict else "WARN", row_number, "Derived value needs derivation_source locating reproducible code or output; never label it as source-reported."))
        if strict and value and status != "verified":
            findings.append(Finding("ERROR", row_number, "Submission extraction with a value must be verified."))
        is_numeric = bool(value and re.search(r"\d", value) and NUMERIC_FIELD_RE.search(row.get("field_name") or ""))
        if is_numeric:
            for key in ("denominator", "unit", "timepoint", "comparison"):
                if not present(row, key):
                    findings.append(Finding("WARN", row_number, f"Numeric extraction lacks {key}; record a value or an explicit not-applicable rationale."))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="manuscript/extraction_ledger.csv", type=Path)
    parser.add_argument("--literature-register", type=Path)
    parser.add_argument("--strict", "--submission", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    findings = audit(args.input, strict=args.strict, literature_register=args.literature_register)
    errors = sum(f.level == "ERROR" for f in findings)
    warnings = sum(f.level == "WARN" for f in findings)
    report = {"schema_version": 1, "audit": "extraction", "errors": errors, "warnings": warnings,
              "findings": [asdict(f) for f in findings], "scope": "Recorded provenance and states; quotes are not independently validated."}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Extraction audit: {errors} errors, {warnings} warnings")
        for f in findings:
            print(f"- {f.level}: row {f.row}: {f.message}")
    return int(bool(errors or (args.fail_on_warn and warnings)))


if __name__ == "__main__":
    raise SystemExit(main())
