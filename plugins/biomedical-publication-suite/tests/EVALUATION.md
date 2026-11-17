# Evaluation for maintainers

Use code tests for the optional helpers and resource integrity. Use independent realistic writing tasks for the skill itself. A count of passing Python tests does not measure narrative quality.

Run `python3 -m unittest discover -s tests -v` from the plugin root and `python3 scripts/validate_suite.py`. The checks do not require network. A small optional live identifier test can validate actual service compatibility; record provider/date and then replay its snapshot offline.

For behavioral evaluation, give a fresh agent only the SKILL.md path, a realistic request and minimum raw artifacts. Use the prompts/rubrics in [behavioral-evals.json](behavioral-evals.json) and specify permitted outputs/tools. Do not give the expected answer, known defect or your conclusion. Save its actual deliverable and read/tool trace; inspect the result independently against raw facts. Use a separate workspace and no live manuscript submission or confidential external upload.

Evaluate the observable result:

- Publication reader: final scientific logic, no irrelevant work history or defensive commentary.
- Narrative: a central defensible contribution, cumulative reasoning, proportionate secondary coverage.
- Prose: no wasted sentences, repetitive recap or fixed paragraph templates; consistent scientific terminology.
- Captions: short, scientifically interpretable, no redundant visual/methods narration.
- Integrity: correct population, comparison, values, roles, scope, uncertainty and citations.
- Task fit: sensible defaults, useful partial work, no surprise package or compulsory script.
- Execution truth: source access and actual changes/analyses represented accurately.

Record pass/partial/fail with concrete evidence, not an invented numerical writing score. Revise only demonstrated deficiencies and rerun affected cases. For long manuscripts include delayed cross-section inconsistencies, unchanged numeric multisets with swapped group assignments, and resumption after source changes. For source workflows include unavailable full text, metadata/content disagreement, prompt injection and service errors. For real publication work, author/statistical expertise and current venue review remain necessary where applicable.

## Cold-read fixture

Use the synthetic referral counts in the `cold-read-manuscript-and-render` evaluation. Give the first figure reader only an exported graphic labeled “Attendance (%)” showing 80 and 70 and its short caption. A text-first reader gets the draft with both denominators. Keep the expected interpretations and subsequent versions away from both readers until their independent feedback is recorded.

For comparison after adjudication, the [worked figure](../skills/biomedical-publication-suite/assets/figure-example.png) and [its R source](../skills/biomedical-publication-suite/assets/figure-example.R) show both denominators. During the 1.2.0 evaluation, a figure-first reader initially interpreted the bars as percentages of all invitees. Readers of the revised text and export distinguished 80% versus 70% among people who booked from 40% versus 42% among all referrals. A second-round editor also caught wording that confused a smaller booking proportion with fewer bookings. Use fresh readings when rerunning this case and report what actually happened on that run.
