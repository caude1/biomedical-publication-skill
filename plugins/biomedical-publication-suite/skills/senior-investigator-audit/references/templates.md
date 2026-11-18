# Templates

Formats for the audit's records. During the audit everything lives in `_audit/`. After implementation, the changelog entry, the audit's record in `archive/audit_<date>/`, and a short block in the agent instructions remain; the workspace is erased. Keep every record short: the records exist so the user can check your judgment and decide.

## Contents

1. `_audit/register.md`: written before each analysis runs
2. `_audit/REPORT.md`: the narrative, the verdict, and the recommendations
3. `_audit/README.md` status lines
4. `docs/CHANGELOG.md` entry, written after implementation
5. `archive/README.md` entry
6. "Settled decisions" block for the project's agent instructions

`archive/file_moves.csv` has one row per affected file: timestamp, run_id, step, action, src, dst, size_bytes, sha256, reason, status (`done`). `safe_move.py` writes these rows when you use it; when you move files by hand, append the same row for each file yourself.

## 1. `_audit/register.md`

Write each entry before running or delegating the analysis. Fill in the result afterwards, whatever it shows. An entry written after the result was seen is marked retrospective. Verification (reruns, recomputed counts and numbers, re-derivation of the headline, fixes) does not go here.

Every decision rule names the result that would weaken or overturn the claim, not only the one that would support it. A sensitivity result shows how much the conclusion depends on a choice. It never makes the alternative the new primary analysis by itself: that choice is made on scientific grounds, and if it changes the primary analysis it is a reframing the user decides.

```markdown
### A2. Does the association hold when exposure is measured at diagnosis rather than at baseline?
- Why it earns its place: exposure timing is the first objection a clinical reader raises. If the
  estimate holds, the central claim no longer depends on the baseline definition.
- Decision rule: estimate within the original interval, same direction -> one sentence of support in
  Results. Direction flips or the estimate halves -> the finding depends on exposure timing; work out
  which definition matches the study question (a change of primary definition is a recommendation
  for the user) and report the dependence plainly either way.
- Status: run before results were seen (_audit/work/analysis/sandbox/04_exposure_timing.R)
- Result: HR 1.49 (1.18 to 1.88) vs 1.52 (1.21 to 1.91) originally.
- Consequence: one sentence in Results; no change to the central claim.
```

If an analysis cannot be run as registered, its result is "could not be run as registered", with the reason. Do not substitute a different analysis under the same entry.

End the register with **Considered and set aside**: one line per idea, no elaboration.

## 2. `_audit/REPORT.md`

Aim for something the user can read in ten minutes. The narrative is the centerpiece: every recommendation follows from it. The narrative formats of biomedical-publication-suite (`references/narrative-frameworks.md`) and manuscript-builder (`project_narrative.md`) are the models; use the project's own narrative file format when it has one.

```markdown
# Audit of <Project>, <YYYY-MM-DD>

## The scientific narrative

### As found
The chain the current draft tells, in three to five sentences: what is known -> the unresolved tension ->
why this study addresses it -> the pivotal finding -> what that finding changes.

### Updated
The same chain, as the paper will now tell it. Then:
- Findings, ranked: central (one, two at most), supporting, secondary. One line each, with the estimate.
- Claim boundaries: what the design supports saying, in the verbs it supports.
- Storyline: title, abstract lead sentence, central figure, Discussion opener, section order.

### How and why it changed
| Element | As found | Updated | What changed it |
|---|---|---|---|
| Population | all 1,240 enrolled patients | the 1,108 eligible at time zero | F2: 132 patients entered after follow-up had started (immortal time) |
| Pivotal finding | exposure associated with higher 1-year mortality (HR 1.57) | the excess risk is concentrated in the first 30 days (HR 2.10), with none after 90 days | F1 (deduplicated join), A2 (landmark analysis) |

Promoted, subordinated, or dropped: one line each, with the reason.

## Verdict
Two or three sentences: where the project stands and the single most important thing the audit changed or
found. A fatal flaw is the exception to the order: state it plainly at the very top of the report, above
the narrative, with the proposed salvage.

## Recommendations
A numbered list of decisions. For each: what you recommend, what it changes in the project, what the
user loses by declining, and which other decisions it depends on. Adopting the updated narrative usually
comes first.
1. Adopt the updated narrative (a reframing): yes. Changes the title, abstract, and Discussion opener.
2. Apply fixes F1-F3: yes. Moves the numbers listed under Accuracy.
3. Add analyses A1-A2 to the pipeline: yes. They carry the new pivotal finding.
4. Reorganize the repository (proposal/reorg_plan.csv): yes.
5. Replace the abstract and changed sections with the drafts in proposal/: yes.
6. Documentation: README, docs/, agent instructions.

## Scientific review
Question and framing, design and data, the reader's first objection and how the work now answers it.

| Decision | What was done | Verdict | Better alternative (if clearly better) | Action | Rationale |
|---|---|---|---|---|---|
| Missing BMI | Complete-case analysis (31% dropped) | Replace | Multiple imputation with the outcome and the predictors of missingness in the model | Adopted in the working copy; complete-case kept as one sentence | Patients missing BMI died more often (12% vs 7%), so complete-case estimates are biased unless missingness is unrelated to the outcome given the covariates. Imputation assumes instead that missingness depends only on recorded variables (MAR); recorded variables (site, year) predict it well, which makes that assumption plausible, though no test can prove it. |

## Accuracy and repairs
Reproduction chain, one line per run:
- Run A, as found: _audit/baseline (212 outputs).
- Run B, original code from raw, in _audit/work: 205 of 212 outputs verified; 7 different (table3.csv is stale).
- Run C, after fixes: differences from B are exactly those in the fixes table.
- Not checked: figure 4 needs the licensed extract, which is not in the project.

| # | Problem | Bin / status | Fix | Effect on results |
|---|---|---|---|---|
| F1 | Left join duplicated 212 patients | Fixable, fixed in work/ | Deduplicated before the join | N 4,318 -> 4,106; HR 1.57 -> 1.52 |

Reported numbers that change: each one, old -> new, with its source cell.

## New analyses
For each: the question, why it earned its place, the result, and its role in the updated narrative.

## Further directions
At most five, ranked by how much each would strengthen or extend the work, one or two sentences each.
Considered and set aside: one line each.

## Repository proposal
Proposed tree beside the current one; old-to-new path map (proposal/reorg_plan.csv, dry run passed);
code and documents that reference moved paths; rollback (reverse moves from the log); verification
commands.

## Written material
Drafts in proposal/ and what they replace. Material outside the project that would need updating
(listed, never edited).

## Open items
Anything under investigation, blocked, or not checked.
```

## 3. `_audit/README.md` status lines

`audit_workspace.py open` writes the README. Update its status line as the audit moves:

- `part 1, audit in progress.`
- `part 1 complete: report written, waiting for the user's decisions.`
- `part 2: implementing decisions 1, 2, 4 (declined: 3, 5).`
- `part 2 complete: verified; ready to close.`

## 4. `docs/CHANGELOG.md` entry (after implementation)

This entry is what survives the workspace, so it carries the honest record: what changed, why, and each analysis's status.

```markdown
## <YYYY-MM-DD>: senior investigator audit
- Narrative: "exposure associated with higher 1-year mortality" -> "excess risk concentrated in the first
  30 days". Adopted at the user's decision.
- Fixed: duplicated patients removed before the join (N 4,318 -> 4,106; HR 1.57 -> 1.52); immortal time
  removed by starting follow-up at eligibility.
- Analyses run during the audit, each registered before its result was seen (exploratory; register in
  archive/audit_<YYYY-MM-DD>/analysis_register.md): A1 exposure at diagnosis (HR 1.49; one sentence in
  Results); A2 landmark analysis (adopted, carries the narrative); A3 negative-control outcome (HR 1.02;
  not reported in the paper).
- Reorganized: 19 files moved, 18 archived (archive/file_moves.csv); the audit's record, with prior
  versions of edited files, in archive/audit_<YYYY-MM-DD>/.
- Declined: renaming the manuscript folder.
- Verified: the project's rerun matches the audit's final run (compare_outputs VERIFIED); inventory PASS.
```

## 5. `archive/README.md` entry

One entry per archived batch, newest first (`audit_workspace.py close` adds its own entry for the audit's record):

```markdown
## <YYYY-MM-DD> audit
- `archive/analysis/rescue_models.R`: superseded model script; replaced by
  `analysis/scripts/survival_models.R`, which reproduces its estimates with the corrected join.
- `archive/agent_workspaces/_GPT/`: scratch work from an earlier agent; nothing in the pipeline
  or manuscript depends on it.
```

## 6. "Settled decisions" block

Add to the project's agent instructions (`AGENTS.md` or its equivalent), ten lines at most:

```markdown
## Settled decisions (audit <YYYY-MM-DD>; see docs/CHANGELOG.md)
- Narrative: the excess mortality is early (first 30 days), not sustained.
- Follow-up starts at eligibility; patients enrolled after that are excluded.
- Not pursued, deliberately: age-stratified headline models; facility-size exposure.
```
