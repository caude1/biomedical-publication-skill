#!/usr/bin/env python3
"""Check reference identity, claim support, and optional evidence pointers; never prove entailment."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class Finding:
    level: str
    target: str
    message: str


def norm(value: str | None) -> str:
    return (value or "").strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        headers = reader.fieldnames or []
        if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
            raise ValueError(f"{path}: absent, blank, or duplicate CSV header")
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError(f"{path}: row width does not match header")
        return headers, rows


def _index(path: Path, key: str, findings: list[Finding], aliases: tuple[str, ...] = ()) -> dict[str, dict[str, str]]:
    headers, rows = read_csv(path)
    id_column = next((name for name in (key, *aliases) if name in headers), None)
    if id_column is None:
        findings.append(Finding("ERROR", str(path), f"Missing required column: {key}."))
        return {}
    indexed = {}
    for line, row in enumerate(rows, 2):
        value = norm(row.get(id_column))
        if not value:
            findings.append(Finding("ERROR", f"{path}:{line}", f"Blank {key}."))
        elif value in indexed:
            findings.append(Finding("ERROR", f"{path}:{line}", f"Duplicate {key}: {value!r}."))
        else:
            indexed[value] = row
    return indexed


def _valid_date(value: str) -> bool:
    try:
        if len(value) == 10:
            return date.fromisoformat(value) <= date.today()
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp <= datetime.now(stamp.tzinfo)
    except ValueError:
        return False


def audit(claim_register: Path, literature_register: Path, *, strict: bool = False,
          extraction_ledger: Path | None = None, results_ledger: Path | None = None) -> list[Finding]:
    findings: list[Finding] = []
    try:
        claims = _index(claim_register, "claim_id", findings)
        if strict and not claims:
            findings.append(Finding("ERROR", str(claim_register), "Submission claim register contains no claims to audit."))
        needs_literature = any(norm(row.get("support_type")).lower() == "external_citation" or norm(row.get("source_id")) for row in claims.values())
        literature = _index(literature_register, "source_id", findings, ("study_id",)) if literature_register.exists() or needs_literature else {}
        extractions = _index(extraction_ledger, "extraction_id", findings) if extraction_ledger else None
        results = _index(results_ledger, "result_id", findings) if results_ledger else None
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return findings + [Finding("ERROR", "input", str(exc))]
    identity_states = {"verified", "unverified", "quarantine", "needs_full_text", "not_indexed", "unavailable", "manual_review", "unresolved", "network_error"}
    for source_id, source in literature.items():
        state = norm(source.get("verify_status") or source.get("source_verify_status")).lower()
        if state not in identity_states:
            findings.append(Finding("ERROR", f"{literature_register}#{source_id}", f"Invalid or blank verify_status: {state!r}."))
    claim_states = {"supported", "needs_verification", "inferred", "author_check", "unsupported_remove_or_weaken", "unsupported", "conflict"}
    content_states = {"supported", "partial", "contradicted", "not_checked", "needs_verification", "unavailable", "not_supported"}
    roles = {"direct", "context", "contrast", "method", "inference", "retraction_notice", "correction_notice"}
    repository_types = {"repo_result", "repo_method", "repo_documentation"}
    support_types = repository_types | {"external_citation", "author_provided", "journal_requirement", "reviewer_comment"}
    for claim_id, row in claims.items():
        target = f"{claim_register}#{claim_id}"
        claim_state = norm(row.get("status")).lower()
        if claim_state and claim_state not in claim_states:
            findings.append(Finding("ERROR", target, f"Invalid claim status: {claim_state!r}."))
        support_type = norm(row.get("support_type")).lower()
        if strict:
            for field in ("claim_text", "support_type", "artifact", "source_locator"):
                if not norm(row.get(field)):
                    findings.append(Finding("ERROR", target, f"Submission claim lacks {field}."))
            if support_type and support_type not in support_types:
                findings.append(Finding("ERROR", target, f"Unknown support_type: {support_type!r}."))
        if strict and claim_state != "supported":
            findings.append(Finding("ERROR", target, "Submission claim must have status=supported; inference belongs in support_role with its evidential basis recorded."))
        source_id = norm(row.get("source_id"))
        is_external = support_type == "external_citation" or bool(source_id)
        if strict and (support_type in repository_types or not is_external) and not norm(row.get("source_file")):
            findings.append(Finding("ERROR", target, "Submission claim lacks source_file for its local evidence."))
        for pointer, index in (("extraction_id", extractions), ("result_id", results)):
            value = norm(row.get(pointer))
            if value and index is not None:
                if value not in index:
                    findings.append(Finding("ERROR", target, f"Orphan {pointer}: {value!r}."))
                elif pointer == "extraction_id":
                    extracted = index[value]
                    if norm(extracted.get("source_id")) != source_id:
                        findings.append(Finding("ERROR", target, "Extraction source_id differs from claim source_id."))
                    if norm(extracted.get("status")).lower() != "verified":
                        findings.append(Finding("ERROR", target, "Referenced extraction is not verified."))
            elif value and strict and index is None:
                findings.append(Finding("ERROR", target, f"Cannot validate {pointer}: supply its ledger."))
        if not is_external:
            continue
        if not source_id:
            findings.append(Finding("ERROR", target, "External citation claim lacks source_id."))
            continue
        source = literature.get(source_id)
        if source is None:
            findings.append(Finding("ERROR", target, f"source_id {source_id!r} is absent from literature register."))
            continue
        if norm(source.get("verify_status") or source.get("source_verify_status")).lower() != "verified":
            findings.append(Finding("ERROR", target, f"source_id {source_id!r} is not identity verified."))
        content_state = norm(row.get("content_status")).lower()
        role = norm(row.get("support_role")).lower()
        if content_state and content_state not in content_states:
            findings.append(Finding("ERROR", target, f"Invalid content_status: {content_state!r}."))
        if role and role not in roles:
            findings.append(Finding("ERROR", target, f"Invalid support_role: {role!r}."))
        if content_state in {"contradicted", "not_supported"}:
            findings.append(Finding("ERROR", target, "Cited content does not support the recorded claim."))
        publication_state = norm(source.get("publication_status")).lower()
        notice_role = role in {"retraction_notice", "correction_notice"}
        if publication_state in {"retracted", "withdrawn"} and not notice_role:
            findings.append(Finding("ERROR", target, f"The {publication_state} source is unsuitable as affirmative evidence."))
        if strict:
            versions = [norm(source.get("source_version")), norm(row.get("source_version"))]
            extraction = (extractions or {}).get(norm(row.get("extraction_id")))
            if extraction:
                versions.append(norm(extraction.get("source_version")))
            if len({" ".join(v.casefold().split()) for v in versions if v}) > 1:
                findings.append(Finding("ERROR", target, "Recorded source versions differ across linked records; reconcile the version and supporting passage."))
            for field in ("checked_by", "checked_at", "support_role"):
                if not norm(row.get(field)):
                    findings.append(Finding("ERROR", target, f"Submission claim lacks {field}."))
            if norm(row.get("checked_at")) and not _valid_date(norm(row.get("checked_at"))):
                findings.append(Finding("ERROR", target, "checked_at must be a nonfuture ISO date or datetime."))
            if content_state != "supported":
                findings.append(Finding("ERROR", target, "Submission claim requires content_status=supported; identity verification alone is insufficient."))
            for field in ("status_source", "status_checked_at", "source_version"):
                if not norm(source.get(field)):
                    findings.append(Finding("ERROR", target, f"Cited source lacks {field}."))
            if publication_state not in {"current", "corrected", "no_notice_found", "retracted", "withdrawn"} and not (publication_state == "expression_of_concern" and notice_role):
                findings.append(Finding("ERROR", target, "Cited publication status is unknown or unsuitable as affirmative evidence."))
            if norm(source.get("status_checked_at")) and not _valid_date(norm(source.get("status_checked_at"))):
                findings.append(Finding("ERROR", target, "status_checked_at must be a nonfuture ISO date or datetime."))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-register", default="manuscript/claim_register.csv")
    parser.add_argument("--literature-register", default="manuscript/literature_register.csv")
    parser.add_argument("--extraction-ledger", type=Path)
    parser.add_argument("--results-ledger", type=Path)
    parser.add_argument("--strict", "--submission", action="store_true", help="Require recorded support, source status, and evidence trace for submission.")
    parser.add_argument("--json", action="store_true", help="Emit a stable machine-readable report to stdout.")
    args = parser.parse_args()
    findings = audit(Path(args.claim_register), Path(args.literature_register), strict=args.strict,
                     extraction_ledger=args.extraction_ledger, results_ledger=args.results_ledger)
    errors = sum(f.level == "ERROR" for f in findings)
    warnings = sum(f.level == "WARN" for f in findings)
    report = {"schema_version": 1, "audit": "citations", "errors": errors, "warnings": warnings,
              "findings": [asdict(f) for f in findings], "scope": "Recorded evidence integrity; claim entailment requires source reading."}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Citation audit: {errors} errors, {warnings} warnings")
        for f in findings:
            print(f"- {f.level}: {f.target}: {f.message}")
    return int(errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
