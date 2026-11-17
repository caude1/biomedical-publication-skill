#!/usr/bin/env python3
"""Initialize a lean biomedical publication package."""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime, timezone
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


# Additive schema evolution: existing columns remain supported; no implicit migration.
CLAIM_HEADER += ['claim_group_id', 'content_status', 'support_role', 'source_version', 'checked_by', 'checked_at']
LITERATURE_HEADER += ['study_id', 'access_level', 'source_version', 'publication_status', 'status_checked_at', 'status_source', 'verified_at', 'verification_scope', 'metadata_snapshot', 'metadata_sha256', 'metadata_publication_status']
EXTRACTION_HEADER += ['source_version', 'quote_unavailable_reason', 'value_origin', 'derivation_source']
RESULTS_HEADER += ['analysis_status', 'timepoint', 'comparison', 'ci_level', 'ci_method', 'value_origin', 'derivation_source', 'result_state']
REVISION_HEADER = ['item_id', 'source', 'priority', 'section', 'issue_summary', 'planned_action', 'status', 'location_of_change', 'evidence', 'notes']
SCREENING_HEADER = ['record_id', 'source_id', 'study_id', 'stage', 'decision', 'reason', 'reviewer', 'reviewer_type', 'date', 'adjudication']

PUBLICATION_CONTEXT = """working_title:
  value: ""
  source: ""
  notes: ""
short_title:
  value: ""
  source: ""
  notes: ""
study_type:
  value: ""
  source: ""
  notes: "observational, randomized, diagnostic, prediction, systematic review, translational, or other"
reporting_guideline:
  value: ""
  source: ""
  notes: "Select current guideline and extensions from official sources; record version/date"
target_journal:
  value: ""
  source: ""
  notes: ""
article_type:
  value: ""
  source: ""
  notes: ""
submission_stage:
  value: ""
  source: ""
  notes: "scaffold, drafting, author review, revision, or submission"
causal_language_allowed:
  value: false
  source: "default"
  notes: "Set true only when design and estimand justify causal language."
primary_question:
  value: ""
  source: ""
  notes: ""
hypothesis:
  value: ""
  source: ""
  notes: ""
data_source:
  value: ""
  source: ""
  notes: ""
population:
  value: ""
  source: ""
  notes: ""
exposure_or_intervention:
  value: ""
  source: ""
  notes: ""
comparator:
  value: ""
  source: ""
  notes: ""
primary_outcome:
  value: ""
  source: ""
  notes: ""
primary_analysis:
  value: ""
  source: ""
  notes: ""
authoritative_files: []
known_limitations: []
open_author_checks: []
audience:
  value: ""
  source: ""
  notes: "optional"
target_journal_family:
  value: ""
  source: ""
  notes: "optional style calibration only"
spelling_convention:
  value: ""
  source: ""
  notes: "optional"
preferred_person_or_voice:
  value: ""
  source: ""
  notes: "optional; do not infer"
acronym_policy:
  value: ""
  source: ""
  notes: "optional"
protected_terminology: []
style_exemplars: []
"""

STUDY_FACTS = """# Study Facts

## Study Design and Setting

## Data Source and Dates

## Population and Analytic Cohort

## Exposure, Intervention, or Comparator

## Primary Endpoint

## Secondary or Exploratory Endpoints

## Covariates and Adjustment Set

## Primary Analysis

## Key Results

## Key References

## Missing or Uncertain Facts

## Authoritative Files
"""

NARRATIVE_BRIEF = """# Narrative Brief

## Central Thesis

## Context and Gap

## Hypothesis or Objective

## Approach

## Headline Findings, Ranked

## Secondary or Subordinate Findings

## Claim Boundaries

## Section Storyline

## Open Narrative Risks
"""

MANUSCRIPT = """# Manuscript

## Abstract

## Introduction

## Methods

## Results

## Discussion

### Limitations

## Conclusion
"""

DISPLAY_TEXT = """# Display Text

## Figure or Table 1

Title:

Subtitle:

Axis labels:

Panel labels:

Legend keys:

Caption:

Footnotes:
"""

OPEN_ITEMS = """# Open Items

## Blocking

## Author Checks

## Citation Checks

## Journal Checks
"""

SEARCH_LOG = """# Search Log

Use one section per search route. Record the question, source, query, date, result count, and notes about errors, rate limits, or access limits.

## Search 1

- Source:
- Query:
- Date:
- Result count:
- Notes:
"""

ARTIFACT_REGISTER = """# Artifact Register

| Artifact | Purpose | Source | Status | Notes |
|---|---|---|---|---|
"""

JOURNAL_REQUIREMENTS = """# Journal Requirements

- Target journal:
- Article type:
- Abstract structure:
- Official instruction URL and access date:
- Instruction version/article type scope:
- Word limit and counting rules:
- Display limits:
- Reference style:
- Required statements:
- Open journal checks:
"""

REPORTING_CHECKLIST = """# Reporting Checklist

## Governing Framework

| Guideline/version | Item | Requirement | Manuscript location | Status | Rationale/evidence |
|---|---|---|---|---|---|
"""

SUBMISSION_READINESS = """# Submission Readiness

## Overall Status

## Blocking Issues

## Nonblocking Issues

## Author Checks

## Journal Checks

## QC Summary
"""


def write_text(path: Path, content: str, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_csv(path: Path, header: list[str], overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow(header)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository or project root.")
    parser.add_argument("--package-dir", default="manuscript", help="Publication package directory.")
    parser.add_argument(
        "--tier",
        choices=("1", "2"),
        default="2",
        help="Backward-compatible alias: tier 1 creates minimal control files; tier 2 creates the lean manuscript drafting package.",
    )
    parser.add_argument(
        "--profile",
        choices=("lean", "evidence", "review", "revision", "submission"),
        default="lean",
        help="Select a lean draft, evidence-only, formal review, revision, or submission scaffold.",
    )
    parser.add_argument(
        "--include-display-text",
        action="store_true",
        help="Create display_text.md when drafting or QCing figure/table text.",
    )
    parser.add_argument(
        "--include-literature",
        action="store_true",
        help="Create the lean literature evidence package files.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing scaffold files after copying timestamped backups; use only for intentional reinitialization.")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    package = (root / args.package_dir).resolve()
    if not package.is_relative_to(root) or package == root:
        parser.error('--package-dir must be a subdirectory inside --repo-root')
    package.mkdir(parents=True, exist_ok=True)

    templates = {
        "publication_context.yaml": PUBLICATION_CONTEXT,
        "study_facts.md": STUDY_FACTS,
        "open_items.md": OPEN_ITEMS,
    }
    if args.tier == "2" and args.profile not in {"evidence", "review"}:
        templates.update(
            {
                "narrative_brief.md": NARRATIVE_BRIEF,
                "manuscript.md": MANUSCRIPT,
            }
        )
    if args.include_display_text:
        templates["display_text.md"] = DISPLAY_TEXT
    if args.include_literature or args.profile in {"evidence", "review"}:
        templates["search_log.md"] = SEARCH_LOG
    if args.profile == "submission":
        templates.update(
            {
                "artifact_register.md": ARTIFACT_REGISTER,
                "journal_requirements.md": JOURNAL_REQUIREMENTS,
                "reporting_checklist.md": REPORTING_CHECKLIST,
                "submission_readiness.md": SUBMISSION_READINESS,
            }
        )

    if args.profile in {"evidence", "review"}:
        templates = {"search_log.md": SEARCH_LOG, "open_items.md": OPEN_ITEMS}
    if args.profile == "review":
        templates["review_protocol.md"] = "# Review Protocol\n\n## Question and eligibility\n\n## Search and selection methods\n\n## Extraction, appraisal and synthesis\n\n## Registration and amendments\n"
    if args.profile == "revision":
        templates["response_to_reviewers.md"] = "# Response to Reviewers\n"
    created: list[str] = []
    skipped: list[str] = []
    for rel in list(templates) + ['claim_register.csv', 'results_ledger.csv', 'literature_register.csv', 'extraction_ledger.csv', 'revision_matrix.csv', 'screening_ledger.csv']:
        if (package / rel).is_symlink():
            parser.error(f'refusing to write through symlink: {package / rel}')
    if args.overwrite:
        backup = package / '.scaffold-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        for rel in list(templates) + ['claim_register.csv', 'results_ledger.csv', 'literature_register.csv', 'extraction_ledger.csv', 'revision_matrix.csv', 'screening_ledger.csv']:
            if (package / rel).is_file():
                backup.mkdir(parents=True, exist_ok=True)
                shutil.copy2(package / rel, backup / rel)
    for rel, text in templates.items():
        if write_text(package / rel, text, args.overwrite):
            created.append(rel)
        else:
            skipped.append(rel)

    csv_files: dict[str, list[str]] = {}
    if args.profile == "submission":
        csv_files["claim_register.csv"] = CLAIM_HEADER
        csv_files["results_ledger.csv"] = RESULTS_HEADER
    if args.include_literature or args.profile in {"evidence", "review"}:
        csv_files["literature_register.csv"] = LITERATURE_HEADER
        csv_files["extraction_ledger.csv"] = EXTRACTION_HEADER

    if args.profile == "revision":
        csv_files['revision_matrix.csv'] = REVISION_HEADER
    if args.profile == "review":
        csv_files['screening_ledger.csv'] = SCREENING_HEADER
    for rel, header in csv_files.items():
        if write_csv(package / rel, header, args.overwrite):
            created.append(rel)
        else:
            skipped.append(rel)

    print(f"Publication package: {package}")
    print(f"Profile: {args.profile}")
    if created:
        print("Created:")
        for item in created:
            print(f"  - {item}")
    if skipped:
        print("Skipped existing files:")
        for item in skipped:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
