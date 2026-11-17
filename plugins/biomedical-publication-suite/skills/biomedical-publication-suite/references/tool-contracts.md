# Optional utilities

Use these only when a concrete file/metadata check benefits from deterministic assistance. The boundary is simple: a helper may answer a question that has a mechanical answer (does this identifier resolve, did this number change, is this interval ordered, does this row have a locator). Whether prose is clear, calibrated, well ordered or free of tics is judged by reading ([prose register](prose-register.md)), and no helper output should be used to decide it. The normal workflow is manual source reading, reasoning, editing and cold review. No script or particular file layout is mandatory for publication work. Commands are examples; replace `<skill-dir>` with the directory containing SKILL.md and use actual project paths.

All bundled helpers use Python 3.10+ standard library; no pip package, API key or hosted agent service is required. Only identifier verification accesses the network. Read its [contract](identifier-verification.md) before use. Other helpers work locally and do not send manuscript/data content anywhere.

## Choose a tool for a specific need

| Need | Optional helper | What it cannot establish |
|---|---|---|
| Start reusable records | `init_publication_package.py --repo-root . --profile lean` | Scientific facts; completed work |
| Compare protected file anchors | `revision_invariants.py --source original.md --revised revision.md` | Meaning in prose, group assignments in complex displays, or citation scope |
| Check public DOI/PMID identity | `verify_identifiers.py --input manuscript/literature_register.csv --fail-on-quarantine` | Claim support or complete publication-status review |
| Check citation relationships | `citation_audit.py --claim-register manuscript/claim_register.csv --literature-register manuscript/literature_register.verified.csv` | Truth of a supported flag; entailment or manuscript-wide coverage |
| Check extraction record structure | `extraction_audit.py --input manuscript/extraction_ledger.csv` | Accuracy/authenticity of quotes or values |
| Check numeric sanity | `results_audit.py --input manuscript/results_ledger.csv` | Model validity; exact P/CI compatibility; cross-artifact reconciliation |
| Catch prose/file patterns | `publication_qc.py --file manuscript.md --observational` | Scientific quality, reader understanding, authorship or readiness |

The identifier helper writes a complete reconciled register without changing input. Use that output explicitly downstream or deliberately promote reviewed records, preserving provenance. It does not mark claim support. No-identifier sources and real metadata variants can be checked manually.

## Existing package support

The initializer defaults to five lean files and skips existing files. Optional evidence/review/revision/submission profiles and fields are described in [schemas](schemas.md). `--overwrite` means intentional reinitialization with timestamped backups, not normal revision. It refuses writes through symlinks or outside the chosen project subdirectory.

For a project already using this suite's named layout, `publication_qc.py --repo-root . --package-dir manuscript --stage scaffold|draft|submission` checks expected files/columns and publication text. Scaffold permits blank templates; draft/submission reject very short empty-like core files. These thresholds belong to the helper's package convention; do not lengthen a short legitimate artifact to pass them. Use `--file` or manual checks for other structures. A claim that names a result ID requires the corresponding ledger even when that file is absent. An external claim requires an identifiable literature row. Packages containing only local claims can omit the literature register.

`--require-claim-register` requires at least one claim. `--require-literature-integrity` makes missing source links and undocumented extraction provenance blocking findings. A documented exception for an unavailable quote still prompts manual inspection. For detailed recorded support/status checks use the standalone citation auditor's optional `--strict` (`--submission` alias), with extraction/results paths if linked. Neither helper inspects actual source passages for entailment. `--fail-on-warn` is available when intentionally useful; it is never the default scientific standard.

## Audit outputs and failure behavior

Citation, extraction and results auditors accept `--json` and emit schema_version, audit, errors, warnings, findings and scope to stdout. They never overwrite ledgers. Exit 0 means no implemented blocking finding; 1 means findings (including handled input errors); 2 is invalid CLI usage. Read the reported scope and warnings. Strict mode checks additional recorded support/provenance, not human authorization or scientific certification.

- Citation audit detects duplicate/blank IDs, invalid states, unsupported/contradicted content, unverified identities and orphan source/extraction/result links. A missing literature file is acceptable for wholly local claims. Strict checks also compare recorded source versions. Use a separate row for each evidence link and group related rows with a shared claim group ID.
- Extraction audit checks IDs/status/missingness, source anchors, short quotes or explicit documented exceptions, and declared derived-value provenance. A legacy `not_found` entry with no value prompts a check of source access. A strict audit of a header-only extraction or results ledger reports that it examined no rows.
- Results audit checks counts, interval order, measure scales and P-value syntax. Record an explicitly unbounded lower or upper interval endpoint as `-Inf` or `Inf`. Leave an unreported bound blank. A negative raw ratio estimate is an error. A reported ratio of zero or infinity, an estimate outside its interval, or an approximate probability interval extending beyond the parameter range prompts source review. In strict mode, a numeric result row must contain a reported value. For a named effect such as a ratio, mean difference or regression coefficient, recording only its denominator leaves the effect unreported. A count can be a complete result in its own right. When all effect estimates, intervals and P values are unavailable, use `result_state=not_estimable`, `not_reported`, or `suppressed` with an explanation in `notes`. Counts can still be recorded when available for disclosure. A declared derived result needs a locator for its calculation.
- Revision comparison inventories numeric entries in simple Markdown pipe tables by first-column row label and column heading. Swapped arm values or inequalities can be located even when the document-wide numbers are identical. Moving intact rows or columns preserves those associations. Rows containing inline code or escaped pipes need direct inspection. Reconcile unlabeled or hierarchical tables, prose assignments and citation placement by reading the sources.
- QC reads UTF-8 text. For Word or PDF, extract the publication text first and inspect the rendered original separately. QC prints findings in file mode and writes `qc_report.md` in package mode unless `--no-write-report` is supplied.

Malformed files, absent tools, provider outages and incomplete sources do not prevent careful manual work on supported content. Distinguish a tool error from a scientific contradiction. Never fabricate a quote, statistic, status or declaration to make a check pass.
