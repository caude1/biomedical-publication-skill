# Literature discovery, verification and synthesis

Use for literature-supported drafting, reference audits and evidence extraction. For formal reviews also read [review methods](review-methods.md). For the optional bundled verifier read [identifier verification](identifier-verification.md).

## Establish scope before retrieval

Translate the question into appropriate PICO/PECO/PCC or a simpler conceptual scope. Specify relevant population, intervention/exposure, comparator, outcomes, designs and time range; record meaningful assumptions. A targeted citation check need not become an exhaustive review. A narrative search is not a systematic search.

Use available PubMed/Entrez, Europe PMC, full-text/library/reference-manager tools, registries, relevant discipline databases and citation trails according to the question. Public web search finds leads and official pages; it cannot by itself establish database completeness. Read primary sources for material claims. Existing reviews help identify studies and disagreements but do not substitute for primary verification when attributing original findings.

For a search whose coverage will be reported, record the database and platform, exact query, date, limits, retrieved/exported count, export file and access errors. For a targeted citation check, record the version and passage inspected. Describe coverage only to the extent the search supports it.

## Keep records, reports and studies distinct

Assign stable source/report IDs. Deduplicate exact identifiers and carefully reviewed bibliographic matches while preserving discovery routes and aliases. A registry ID can connect several distinct publications; it is not a record deduplication key. Link reports to a study ID to avoid double counting a cohort in synthesis. Do not collapse protocol, preprint, results, correction and follow-up automatically.

## Verify before asserting

1. Confirm identity by consistent title/authors/year/venue and DOI/PMID or a stable publisher/registry/source record. A book or nonindexed source can be verified manually; absence of DOI/PMID does not make it false.
2. Fetch the source needed for the claim. Metadata supports bibliographic identity; abstracts support only what they explicitly report. Inspect full text, supplements and tables for detailed outcomes, subgroup methods and harms. OCR requires checking the original page for critical numbers/symbols.
3. Record the exact supporting locator, access level, source version/date, short exact excerpt where appropriate, and support role. Do not extract from snippets or generated summaries. Missing fields remain not_reported/unclear/needs_full_text; missing is not zero.
4. Check status/version using publisher and relevant index/update records. Distinguish a correction from retraction and a notice from the original article. No signal in one provider is a limited check, not proof. Corrected findings require the corrected version. Retracted evidence may be discussed as a retraction, not used uncritically as valid support.
5. Assess applicability and limitations before synthesis. Identity, content support, bias and certainty answer different questions; see [evidence control](evidence-and-claim-control.md).

For facts that are not research findings (whether a hospital closed and when, what a regulation requires, an agency's count), cite the official or primary source: the agency, registry, statute or organization itself. Encyclopedias, news aggregators and other secondary pages are leads; cite one only when no primary source can be found, and say so in the author notes.

Never infer identifiers from memory or repair a mismatch by substituting a plausible paper. Keep discrepancies with source-specific evidence. A transient API failure is network_error, not evidence that a reference is fake.

### Match each citation to the words it supports

Read the sentence with its neighboring sentences and locate each claim in the source. A prevalence estimate, an explanation for it and a treatment implication each need their own evidential basis. Place a citation after the supported clause or split the sentence when sources have different roles. For a numbered group, check which report contributes each finding. Keep a reference that supplies relevant context in that role.

For example, a cohort paper reports fewer readmissions after discharge among patients enrolled in follow-up. It reports no measure of adherence. Cite the paper for the readmission association. If adherence is discussed as a possible explanation, identify it as an interpretation and check any evidence offered for it separately.

If the publisher posts a correction, read the notice alongside the corrected article. Trace the affected table cells, estimates and conclusions to their uses in the manuscript and supplement. An author-name correction may require only a reference update. A changed denominator may require revising several results. Give the claim, extraction and literature records the same source-version label when they rely on the same version. Keep separate report IDs for versions that need separate attribution.

## Identifier-helper reconciliation

The helper preserves the input and writes a complete reconciled register plus pass/nonpass subsets and metadata snapshots. Inspect all nonpass records and material discrepancies. Use its reconciled register explicitly in downstream citation auditing, or deliberately merge reviewed identity fields back by unique source ID. A successful helper run does not change the input register or mark content support as checked. Do not silently discard unresolved rows or overwrite manual support/status decisions with metadata-only results.

## Source-grounded extraction

For reusable extraction records, one row per field/result, with source ID, field/value, unit, denominator, timepoint, comparison, source locator, version and short source quote where suitable. Verified numeric values must retain analysis population and measure definition. A table cell can use exact row/column labels and a brief cell excerpt; missing quotations need an explicit access/right/format reason and manual source inspection. Do not invent a quote to satisfy a schema.

Distinguish extracted from calculated values. New calculations need code, input provenance, formula/assumptions, output and a check; never label a derived statistic as reported by the article. Extraction and citation scripts check record structure, not the truth of a quote or entailment.

## Synthesis and stop conditions

Organize by question/outcome or explanatory argument rather than one paragraph per paper. Separate direct results, contextual comparisons, conflicting evidence, mechanisms proposed by sources, and your own inference. Cite near each claim and do not stretch an abstract statement into an unreported population/timepoint.

When a draft exposes a gap, retrieve targeted missing evidence and revise; stop after a bounded attempt when access is unavailable or the question needs an author decision. Return supported synthesis and precise unresolved claims/searches. Do not invent references to fill gaps, state 'no studies exist' from failed search, or claim all sources verified when only a subset was checked.

Before delivery, check source identity, each material claim's passage, status/version, citation placement and coverage, study-family duplication, and boundaries of accessible evidence. Preserve cited preprint status and distinguish ongoing trials from results.
