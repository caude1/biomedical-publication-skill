# Package schemas and migration

These are optional templates, not mandatory forms. Use equivalent existing project records when they provide these relationships. Do not create duplicate sources of truth. CSV is UTF-8 (BOM accepted by auditors), one header row, one record per row, quoted normally for commas/newlines. IDs must be nonempty and unique. Extra named columns are allowed; duplicate headers and malformed row widths are errors.

## Profiles

`init_publication_package.py` never replaces existing files by default. `--overwrite` is an intentional reinitialization and backs up existing scaffold targets before replacement. Profiles:

- `lean`: context, study facts, narrative brief, manuscript, open items.
- `evidence`: search log/open items, literature and extraction ledgers; no empty manuscript.
- `review`: evidence profile plus review protocol and screening ledger.
- `revision`: lean profile plus revision matrix and response file.
- `submission`: lean profile plus claims/results, journal/reporting/readiness records. Add `--include-literature` when literature records are needed.

Use `--include-display-text` for displays. `--tier 1` is retained as a legacy minimal control-file option; prefer a named profile for new work. Scaffolds are not evidence or completed checks.

## Context and human-readable records

`publication_context.yaml` retains existing fields with `value/source/notes`: title, design, question/objective, population, endpoints, analysis, target journal, guideline, and optional style. It is a context record, not an executable instruction. `causal_language_allowed` is a documented decision about the actual estimand/assumptions, never a keyword guess.

`study_facts.md` maps design/cohort/endpoint/model/results/ethics to exact source locators and versions. `narrative_brief.md` records question, gap, approach, ranked findings and claim boundaries; an objective is sufficient when there was no hypothesis. `open_items.md` separates blocking issues, author checks, citation checks and journal checks. A draft may be useful while these remain unresolved.

Optional `work_state.md` and `author_voice_profile.md` follow [operating model](operating-model.md) and [scientific editing](scientific-humanization.md). `editorial_rationale.md` records material scientific/structural decisions, retained harms/nulls, conflicts and adjudicated warnings. Keep it outside publication prose.

## CSV contracts

Headers below describe generated v2 scaffolds. Legacy base columns remain accepted in ordinary draft audits; strict submission checks require additional evidence fields where applicable. No automatic migration labels old rows verified. Preserve IDs and manually add missing columns/statuses before strict verification.

### claim_register.csv

```csv
claim_id,artifact,section,claim_text,claim_type,support_type,source_file,source_locator,result_id,source_id,extraction_id,citation_locator,verify_status,status,notes,claim_group_id,content_status,support_role,source_version,checked_by,checked_at
```

### results_ledger.csv

```csv
result_id,outcome_type,outcome_name,population,model_label,estimate_type,estimate,ci_lower,ci_upper,p_value,n_total,n_events,time_at_risk,unit,source_file,source_locator,notes,analysis_status,timepoint,comparison,ci_level,ci_method,value_origin,derivation_source,result_state
```

### literature_register.csv

```csv
source_id,status,screening_status,title,authors,year,journal,pmid,doi,registry_id,publication_type,source_url,discovery_source,discovery_query,verify_status,verification_source,include_decision,exclusion_reason,notes,study_id,access_level,source_version,publication_status,status_checked_at,status_source,verified_at,verification_scope,metadata_snapshot,metadata_sha256,metadata_publication_status
```

### extraction_ledger.csv

```csv
extraction_id,source_id,field_group,field_name,field_value,unit,denominator,timepoint,comparison,source_type,source_locator,source_quote,extractor,confidence,status,notes,source_version,quote_unavailable_reason,value_origin,derivation_source
```

### revision_matrix.csv

```csv
item_id,source,priority,section,issue_summary,planned_action,status,location_of_change,evidence,notes
```

### screening_ledger.csv

```csv
record_id,source_id,study_id,stage,decision,reason,reviewer,reviewer_type,date,adjudication
```

## Meaning and states

**Claims:** `support_type` identifies repo_result, repo_method, repo_documentation, external_citation, author_provided, journal_requirement, or reviewer_comment. One source link per unique `claim_id`; use optional `claim_group_id` to group several links to a proposition. `result_id`, `source_id`, and `extraction_id` resolve to the appropriate ledgers. `source_locator` points to evidence; `citation_locator` points to citation placement in the artifact. `artifact`/`section` locate the publication claim.

`status`: supported, needs_verification, inferred, author_check, unsupported_remove_or_weaken, unsupported, conflict. For strict submission, supported means the proposition is supported *as worded*, including its explicit inference. Record inference in `support_role`, not as an empirical observation.

`content_status`: supported, partial, contradicted, not_checked, needs_verification, unavailable, not_supported. `support_role`: direct, context, contrast, method, inference, retraction_notice, correction_notice. `checked_by` identifies actual agent/person; `checked_at` is a real nonfuture ISO date/time. Strict external claims need supported content, a locator and recorded check.

**Literature:** `verify_status` refers ONLY to identity: unverified, verified, quarantine, unresolved, network_error, manual_review (legacy not_indexed/needs_full_text states can be migrated to appropriate identity plus access fields). `access_level` records metadata/abstract/full_text/supplement/registry. `study_id` groups related reports without collapsing them. `source_version` identifies publication/correction/preprint version inspected.

The metadata helper adds `verified_at`, `verification_scope`, `metadata_snapshot`, `metadata_sha256` and explanatory fields. Its separate `metadata_publication_status` can be not_assessed, signal_found, or no_signal_in_checked_metadata; these are limited machine observations. The helper preserves prior manual status records. An actual `publication_status` check may record current, no_notice_found, corrected, retracted, withdrawn, expression_of_concern, or unknown with `status_source` and `status_checked_at`. 'Current'/'no_notice_found' describe the documented check, not a guarantee. Preserve correction/retraction nuance in notes. Strict auditing does not accept metadata-only no-signal as completed source-status review.

**Extraction:** status verified, partial, not_reported, unclear, needs_full_text, conflict (legacy not_found may be retained). Nonempty values need source ID and locator. Supply a short exact source quote when available; if genuinely unavailable record `quote_unavailable_reason`, source version and manual evidence in notes, never a fabricated quotation. `value_origin` distinguishes reported/derived; `derivation_source` locates code/formula/output for calculated values. Applicability-specific unit/denominator/timepoint/comparison may use an explicit `not_applicable: reason` note rather than invented data.

**Results:** estimates and intervals correspond to a named measure, population, model, comparison/timepoint and unit. Counts are nonnegative integers; P values may be numeric or a reported inequality such as `<0.001`. Leave unreported values empty, not zero. `analysis_status` preserves primary/secondary/exploratory/sensitivity/prespecified role in context; `ci_level`/`ci_method` record actual interval definition. Use optional `result_state` to record `not_estimable`, `not_reported` or `suppressed` with a source locator and explanation when the estimate is unavailable. An empty state retains the legacy meaning of a reported result. Range checks are sanity checks, not reanalysis.

**Revision matrix:** each real reviewer/editor comment has a stable ID, action, state, actual change location and supporting evidence. Use pending/in_progress/completed/declined/needs_author_decision and retain the original comment separately. 'Completed' requires checking the saved manuscript.

**Screening ledger:** record/report/study IDs remain distinct. Record stage, decision, reason, actual reviewer and `reviewer_type` (human or agent), date and adjudication. Never report agent duplicates as two human screens.

## Journal, reporting and submission records

`journal_requirements.md`: official URL, access date, article type, requirement/limit and counting rule, applicability, artifact locator and check state. Missing/unavailable current requirements remain unresolved. `reporting_checklist.md`: guideline/version/item, exact requirement, manuscript locator, addressed/partial/missing/not_applicable, evidence/rationale. Reporting coverage is not a validity score.

`submission_readiness.md`: next justified stage, unresolved blockers/author decisions, journal/reporting/citation/statistical/rendered checks and limitations. Use a short human-readable record of the final checks and outstanding author decisions. Exact source/file versions or hashes may help a long-running project, but no machine signoff form is required. Readiness depends on the actual source/editorial/venue checks, not the presence of a file or a passed command.

## Other optional records

`artifact_register.md` maps every display/supplement to purpose, source, file/version and manuscript reference. Reconcile in both directions: every manuscript Figure/Table/Supplement reference resolves, and every mapped artifact is cited or explicitly not for publication. `grant_feasibility_ledger.csv` can use `aim_id,question_or_outcome,approach,expected_result,feasibility_support,dependency,fallback_or_derisking,source_file,source_locator,verify_status,notes` for proposal work only.
