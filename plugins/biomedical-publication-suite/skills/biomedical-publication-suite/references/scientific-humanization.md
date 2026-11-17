# Scientific editing and author voice

Use for revision, humanization, voice matching, and editorial review. Humanization means clear, precise scientific prose. Never pursue detector scores, infer authorship from style, add deliberate errors, or manufacture irregularity.

## Two independent decisions

**Intensity:** light (local grammar/clarity), standard (paragraph focus and cohesion within sections), deep (justified structural reconstruction), or review-only (prioritized findings without rewriting). Infer the least invasive level that solves the request. A deep edit needs a concrete problem such as buried question, disconnected evidence, duplicated paragraph roles, or research chronology obscuring scientific logic. A functional structure needs no rearrangement.

**Authority:** source-locked expression versus evidence-calibrated revision. Isolated prose defaults to its supplied facts, with uncertainty about their correctness preserved. Broader outputs/protocol/sources can justify correction or recalibration. Style alone cannot justify strengthening a claim.

Source locking does not require repeating a known error. If the supplied design and statement establish unsupported causality or equivalence, correct the wording and disclose the material change. If evidence is unclear, retain only the defensible proposition or flag the disputed passage as provisional; do not silently certify or amplify it.

## Meaning ledger

For a small edit, use a mental list. For a substantial revision, use existing notes or a compact record when needed; keep source locators available and protect:

- material scientific propositions and negation, distinguishing observation from interpretation or proposed mechanism; irrelevant internal work-log details are not protected publication content;
- design, setting, population, comparator, endpoint, time horizon and group direction;
- signed values, inequalities, units, denominator/numerator, estimates/intervals/P values and precision;
- outcome roles, analysis population/model/adjustments, prespecified/exploratory/post hoc/safety status;
- causal/modal strength, uncertainty, citations and exact supported scope;
- quotations, equations, variables, citation keys/fields, cross-references, accession IDs and software/reagent versions;
- primary, null, adverse, contradictory and consequential secondary findings.

Establish the most compelling defensible organizing contribution before polishing. Develop it cumulatively rather than giving every source detail equal emphasis. A paragraph must advance the argument; a sentence must contribute information or a necessary logical link. Revise in order: scientific job → meaning ledger → justified structure changes → paragraph flow → sentence clarity → voice → [register review](prose-register.md) → source comparison → cold editorial read. Stop preference-only polishing when the artifact is accurate and useful.

When a file comparison would help, optionally run `python3 <skill-dir>/scripts/revision_invariants.py --source original.md --revised revision.md`. Review each difference; the script cannot detect all changes in meaning or prove equivalence. Numbers can be swapped across groups while their multiset remains identical. Follow citations through sentence moves to preserve scope.

## Natural prose with scientific precision

Give paragraphs a recoverable argument. Use given-to-new flow and explicit antecedents. Transitions should name an actual relationship rather than decorate disconnected sentences. Prefer concrete subjects/direct verbs when clear; passive voice is useful when the procedure/object carries focus. Technical repetition is often necessary; do not cycle synonyms for an outcome or model.

Remove unsupported importance claims, vague attribution, empty trailing inference, abstract filler, canned contrasts, generic endings and cosmetic variation when they weaken the artifact. These are editorial questions, not forbidden words. Discourse markers such as "Notably" and "Importantly" are acceptable; when a transition is cut, restore the logical link instead of leaving two unconnected sentences. Read the whole artifact before editing: sentences built for rhetorical shape are disproportionately likely to misstate the result, and a contradiction found during editing goes to the author as a separate note, never as a silent fix. [Prose register](prose-register.md) has the families, the earned forms and the protection rules. Preserve field-standard nominal terms, literal robust standard errors/pivotal trial language, evidence-tied hedging, and purposeful punctuation.

Keep uncertainty at the claim where it changes interpretation. Do not use P-value thresholds to choose confidence of voice. A nonsignificant result is uncertain evidence, not proof of no effect. Preserve protocol amendments, methods rationale, reproducibility details and material limitations wherever readers need them.

## Voice calibration

Use supplied or requested representative samples. Record genre/audience, person, sentence density, terminology, spelling, transitions, rhythm, punctuation and hedge placement. Match traits without copying distinctive phrasing, importing sample facts/citations, or recreating its errors. Do not infer style preferences from identity or filesystem names. An optional `author_voice_profile.md` is useful only for repeat work.

## Comparison and output

Manually verify: superlatives, rankings, scope words, simultaneity, negations and hedge conditions survive claim by claim; supported material scientific propositions are preserved, except evidence-based corrections disclosed to the author; omit irrelevant workflow history; no changed scope/direction/value/endpoint role; no moved citation supporting a different assertion; no erased uncertainty or harmful/null finding. When comparing studies, match population/comparator/timepoint/measure/analysis before claiming superiority.

For editing, return clean text first and material author concerns separately. For review-only, return prioritized findings with exact locators, consequences and remedies. For requested redlines, preserve the user's output order and show meaningful scientific/structural changes; do not bury a material change in hundreds of formatting marks. If a format tool is unavailable, label a textual comparison honestly rather than claiming tracked changes.

Use [cold editorial read](manuscript-voice.md) after revision. For a high-stakes manuscript, a fresh reviewer receives the draft and raw evidence, not your intended conclusion. Ask them to recover question, design, findings, scope, and uncertainty and identify unsupported leaps. Their agreement is useful scrutiny, not proof of correctness.
