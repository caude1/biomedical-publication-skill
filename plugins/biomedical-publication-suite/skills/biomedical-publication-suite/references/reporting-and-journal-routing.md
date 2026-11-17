# Reporting and journal routing

Load for study-design routing, journal targeting, journal adaptation, reporting coverage, or submission preparation. A small prose edit does not require a new journal search unless its answer depends on current requirements.

## Choose the applicable guidance

1. Identify actual design, article type, stage, main claim and specialized methods. Keywords are clues, not the decision rule.
2. Use the dated starting points below, then open the current official statement, checklist and applicable extension through the [EQUATOR library](https://www.equator-network.org/reporting-guidelines/). Load the explanation document for ambiguous items.
3. Read current instructions for the exact target journal and article type. Record URL, access date, source version/date, requirement and application. A published exemplar illustrates style; it cannot establish a current requirement.
4. Reconcile explicit journal instructions, reporting guidance and institutional/ethics constraints. Scientific accuracy and required transparency cannot be waived by house style. If venue wording appears obsolete or conflicting, document the conflict, prepare compatible work, and leave the unresolved requirement visible.

## Dated starting points

Select by the question the paper answers. For example, reading stored images against a reference standard, predicting future deterioration, and testing whether decision support improves patient outcomes can all involve the same software. They require different reporting evidence. For overlapping objectives, apply the relevant items to each. The TARGET and RECORD statements and the links for trial, diagnostic-AI and review-protocol guidance were checked on 2026-11-17. Reopen relevant guidance at use time.

| Actual study or output | Starting point | Particular routing issue |
|---|---|---|
| Randomized trial report | [CONSORT 2025](https://www.consort-spirit.org/published-statements) | Include an impact trial of an AI-supported clinical workflow here. Check applicable design/intervention extensions, allocation unit, primary outcomes and harms. |
| Randomized trial protocol | [SPIRIT 2025](https://www.bmj.com/content/389/bmj-2024-081477) | Compare the dated protocol, statistical analysis plan (SAP) and registry. Trace changes in outcome, time point and analysis to amendments and their timing. An unresolved difference stays visible. |
| Cohort, case-control, cross-sectional | [STROBE](https://www.strobe-statement.org/checklists/) with [RECORD](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1001885) for routinely collected health data | Describe who enters the data source, cohort selection and measurement. For linked or coded data, report applicable algorithms, available validation evidence and losses on linkage. |
| Observational study explicitly emulating a target trial | [TARGET 2025](https://www.bmj.com/content/390/bmj-2025-087179) | Pair the proposed trial protocol with its implementation in observational data. Check eligibility, assignment and start of follow-up at time zero, and the assumptions behind the estimated contrast. |
| Other quasi-experimental or explicitly causal observational study | Locate design-specific guidance plus relevant observational/intervention items | STROBE is not a universal complete router for interrupted time series or difference-in-differences. Audit causal estimand and identification assumptions. |
| Diagnostic accuracy | STARD; [STARD-AI 2025](https://www.nature.com/articles/s41591-025-03953-8) where applicable | Index test, reference standard, thresholds, indeterminate results and patient flow. |
| Clinical prediction model using regression or ML | [TRIPOD+AI 2024](https://www.bmj.com/content/385/bmj-2023-078378) | Development/validation, leakage, calibration, discrimination and applicability. The guideline is not limited to ML. |
| Systematic review or meta-analysis | [PRISMA 2020](https://www.prisma-statement.org/prisma-2020), extensions and [PRISMA-S](https://www.prisma-statement.org/prisma-search) | Load [review-methods.md](review-methods.md); reporting guidance cannot supply missing conduct. |
| Review protocol / scoping review | [PRISMA-P](https://www.prisma-statement.org/protocols) / [PRISMA-ScR](https://www.prisma-statement.org/scoping) | Protocol versus completed review; mapping versus effect estimation. |
| Case report / case series | CARE or design-specific series guidance | Actual consent, publication privacy and clinical chronology. |
| Animal research | ARRIVE 2.0 | Do not apply animal-specific items indiscriminately to cell-only studies. |
| Qualitative research | SRQR or COREQ as applicable | Reflexivity, sampling, analysis and source quotations. |
| Quality improvement / economic evaluation | SQUIRE 2.0 / CHEERS 2022 | Context, implementation, resource assumptions and uncertainty. |
| Clinical guideline / consensus | RIGHT and appropriate development/appraisal guidance such as AGREE | Separate recommendations/panel judgments from research findings. |
| Other translational, laboratory, omics or AI study | Search EQUATOR and field-specific standards | Choose by method and claim; distinguish an AI intervention study from AI writing assistance. |

Do not auto-convert every observational statement to association if a causal estimand and defensible identification strategy are explicit. Conversely, randomization does not validate every post hoc or subgroup causal claim. Evaluate each claim using [statistical-reporting.md](statistical-reporting.md).

## Map coverage to actual text

For a checklist request, use the supplied or official form when available. Record the guideline version, item, subparts, manuscript locator and any outstanding action. A Methods heading alone cannot support a checkmark. For example, if a form asks for both the extent and the handling of missing data, a table of missing counts supplies only the first part. Mark that combined item `partial` and locate the analysis method. If handling is a separate item with no supporting text, mark it `missing`. Use `addressed`, `partial`, `missing` or `not_applicable` with a reason as appropriate. Refresh page and line locators after the final render.

Never fill absent methods with plausible boilerplate or infer that an action occurred because a checklist expects it. Reporting omissions can be repaired from evidence; missing conduct cannot. Record protocol/SAP amendments and analysis deviations with actual timing. A complete coverage map does not certify validity, low risk of bias, adherence, or acceptance.

## Journal targeting and adaptation

For an unspecified venue, draft in a suitable conventional structure and label the target as undecided. For a targeting request, compare a small shortlist on scope, audience, accepted article type, verified requirements and material tradeoffs. Distinguish editorial-fit judgment from verified policy. Do not invent acceptance probabilities, impact factors, fees, indexing or turnaround times.

For a journal adaptation, capture applicable requirements in the existing working record, if needed. Include article/abstract structure and counts, displays, reference style, file formats, blinded review, reporting documents, supplements, registration, ethics/consent, funding/COI/contributions, data/code/materials access, AI policy and required submission statements. Record how counts are defined. Unknown fields stay unknown; a venue-family convention is a drafting default, never a verified rule.

Adapt structure/references after facts are stable. Recheck abstract/body/display agreement and render final files to inspect layout. Unavailable official instructions permit a useful provisional draft but block an unqualified claim of journal compliance or submission readiness. Use [revision-response-and-submission.md](revision-response-and-submission.md) for the final gate.

## Length adaptation

Apply the verified article-type word-count inclusions/exclusions and separate abstract/display limits. Budget space for the methods and interpretation the reader needs. Treat the venue limit as a ceiling and retain item-level coverage after cuts. With no target, use comparable article type/design/scope to estimate total and section balance; see [manuscript length](manuscript-length.md).
