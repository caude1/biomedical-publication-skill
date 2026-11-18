# Writing the stronger version

Read this before step 6. The rewrite presents the audited project the way its senior author would: the corrected numbers, the better methods, the analyses that earned their place, and a framing that leads with what matters.

## Contents

1. Fix the narrative first
2. Fix the claims before the prose
3. Lead with what matters
4. Confident sentences: patterns and rewrites
5. Where caveats go
6. Methods at the reader's level
7. Figures
8. Register review, by hand
9. Checks after drafting

## 1. Fix the narrative first

The narrative decides everything downstream: which claims lead, the abstract's emphasis, paragraph order, the central figure, and the Discussion. It is also what the user decides on. Write it in `_audit/proposal/` before any prose.

- **The chain.** What is known -> the unresolved tension -> why this study addresses it -> the pivotal finding -> what that finding changes. One principal contribution. Before choosing, compare two or three candidate frames: an unexpected pattern, a clinically consequential difference, a resolved conflict in the literature, a useful negative finding, a methodological advance, a mechanistic connection. Choose by importance, explanatory power, novelty supported by literature you actually retrieved, strength of evidence, and relevance to the reader. A small P value is not importance, and "first" needs a search behind it.
- **Allocate attention.** Central: developed fully. Supporting: enough detail to make the central claim convincing. Boundary-changing (contrary evidence, harms): enough to calibrate the claim, and if it changes the inference, the narrative changes. Secondary: a sentence or a table. Internal: omitted.
- **Boundaries and storyline.** State what the design lets the paper claim, in the verbs it supports, and sketch the section storyline: title, abstract lead, central figure, Discussion opener.
- **Before and after.** Keep the narrative you found beside the updated one, and for every element that moved, the evidence that moved it (a fix, a new analysis, a verified source) and what was promoted, subordinated, or dropped. This comparison is the heart of the report (`templates.md`, section 2).
- **Honest status.** An exploratory or post hoc insight can lead the paper when that is its actual status and the paper says so. Never invent a prospective hypothesis, and never hide the original primary endpoint to make a frame work.
- **The project's own format.** If the project keeps a narrative file (manuscript-builder's `project_narrative.md`: central story, contribution framing, claim boundaries, section storyline, open narrative risks; or a `narrative_brief.md`), draft its update in the same format.

For deeper guidance, biomedical-publication-suite's `references/narrative-frameworks.md` uses the same chain and pairs a Scientific Narrative with an Editorial Rationale; the report's "Updated" and "How and why it changed" sections are those two.

## 2. Fix the claims before the prose

Rewriting shifts expressed certainty, usually upward, and the shift compounds across passes. A claim list fixed before drafting, and derived from the narrative, keeps the prose bold and accurate at once. Build it first, rewrite once from it, then check the draft against it.

| Claim | Evidence (estimate, interval, n; source file and locator) | Verb the design supports | Tier | Appears in |
|---|---|---|---|---|

**Verb ladder.** Use the strongest rung the design reaches, and use it without apology.

- *Observed quantity:* "was", "occurred in", "rose from X to Y".
- *Association* (observational data without an identifying design): "was associated with", "was 40% higher among".
- *Prediction:* "predicted", "discriminated (AUC 0.81)", "was well calibrated".
- *Effect* (randomization, or a quasi-experimental design whose identifying assumptions you state): "reduced", "increased", "caused".
- *Mechanism:* only with mechanistic evidence. Otherwise, one sentence in the Discussion proposing it as the explanation the data point to.

**Tiers.** One central claim (two at most), the supporting claims that make it convincing, and secondary results reported briefly. Give narrative weight by importance, not by the number of analyses behind a result.

**Silent upgrades to catch.** Association becoming cause. An adjusted estimate described as if unadjusted. A sample result stated for a population. A finding turned into a practice recommendation. An exploratory result presented as confirmatory. "No significant difference" becoming "no difference". Each is an overclaim, and each is fixed by choosing the right verb once, not by adding hedges around the wrong one.

## 3. Lead with what matters

- Find the sentence a colleague would repeat after hearing the talk. That sentence leads the abstract's results and conclusion, opens the Discussion, and decides the central figure.
- The abstract conclusion says what was found and why it matters. It never ends on a limitation. The design is already named in the abstract's design line; restating "observational, so causality cannot be inferred" in the conclusion adds nothing.
- The Introduction builds to the gap the study fills in as few paragraphs as the argument needs, and states the objective plainly.
- The Discussion opens with the main finding and what it changes, then places it against the literature (especially the most recent and the most contradictory work), then explains the mechanism or interpretation the data point to, then gives limitations in one paragraph, then closes on the contribution.
- Cover each subject in one place (Mensh and Kording's rule). That is the structural reason caveats live in one section: a limitation stated in the abstract, again in the results, and again in the discussion is three dilutions of one point.
- A title may state the finding when the design supports the verb.
- Each paragraph has one job and hands off to the next. A reader should be able to say why paragraph B follows paragraph A.

## 4. Confident sentences: patterns and rewrites

| Earlier-agent pattern | Rewrite |
|---|---|
| "X may potentially be associated with Y." | "X was associated with Y (OR 1.8; 95% CI 1.3 to 2.4)." |
| "X may be an important component of Y." | State what the data show about X and Y, with the estimate. If they show little, cut the sentence. |
| Abstract conclusion ending "…should be interpreted with caution given the observational design, and causal inference cannot be established." | Delete. End on the finding and its consequence. |
| "Although not statistically significant, there was a trend toward…" | "The estimate among men was imprecise (OR 1.37; 95% CI 0.92 to 2.02)." Or report it in a table and move on. Never "trend". |
| "…which may reflect limited power." | Delete. The interval already shows the precision. |
| "It is important to note that…", "It should be noted that…" | Delete the frame and say the thing. ("Notably," and "Importantly," are acceptable discourse markers; judge the sentence they open.) |
| "We were able to demonstrate…", "This study sought to explore…" | "We found…", "We tested whether…" |
| "To our knowledge, this is the first study to…" | If your literature search supports it: "No previous study has…". Otherwise cut it. |
| "Further research is needed to confirm these findings." | Cut, or name the one study that would settle the open question and why. |
| "appeared to be possibly associated" | "was associated" |
| Methods narrating implementation ("identifiers were read as character values, headers normalized before field resolution") | Move it to code comments or the data documentation. The paper keeps what a reader needs to reproduce or judge the analysis. |
| Methods narrating history ("the final model", "after revising the exposure", "the canonical analysis") | Describe the final procedure as the procedure, and label what was post hoc. Never write "prespecified" unless a dated plan shows it. |

Keep sentences declarative, subjects concrete, and numbers doing the persuading. Adjectives such as "striking", "novel", "robust", and "important" persuade no one; the estimate does. Put the new information, usually the finding and its number, at the end of the sentence where the stress falls, and keep the verb close to its subject (Gopen and Swan). Do not use em dashes.

A hedge is load-bearing or it is deleted. For each qualifier, ask what specific uncertainty it carries. If you cannot name one, delete it. Good writers hedge by choice, not by tic, and they trust the reader's common sense (Pinker). The usual tics are "apparently", "comparatively", "fairly", "in part", "presumably", "relatively", "seemingly", "somewhat", "to some extent", and "may" or "might" stacked on "suggest".

## 5. Where caveats go

- **One Limitations paragraph** near the end of the Discussion, usually three to six sentences. Each names a specific limitation, the direction and rough size of its likely effect when known (as STROBE asks), and, in a clause, what the analysis did about it. Biases too small to matter need no sentence. No boilerplate ("the retrospective design") unless you name the actual threat it creates. Do not list problems the audit fixed. Do not end the paper on limitations.
- **The abstract carries no caveats,** with one exception: if the target journal's structured abstract has its own limitations field (Annals of Internal Medicine's does, for example), write one specific sentence there naming the main limitation. Follow the journal's format; do not import the habit elsewhere.
- **A qualification that changes what a claim means is not a caveat.** Build it into the claim ("among patients aged 65 and older, …") and move on.
- **Replace a vague caveat with a number when an analysis earned its place:** an E-value, a tipping point for missing data, a negative-control result, a bound. "An unmeasured confounder would need a risk ratio of at least 2.6 with both treatment and outcome to explain the association away" is a confident sentence about robustness; "residual confounding cannot be excluded" is a hedge.
- **Reporting obligations are not hedges.** Deviations from a registered protocol or SAP, exclusions, and missing-data handling are reported plainly in Methods.

## 6. Methods at the reader's level

Include: data source, setting, and dates; population and eligibility; exposure, outcome, and covariate definitions (with the reason for the adjustment set); the model; how uncertainty was estimated (clustering, robust errors, bootstrap); missing-data handling; the sensitivity analyses that earned their place; software and versions; code and data availability.

Leave out: the story of how the analysis evolved, approaches tried and dropped, file formats and parsing details, agent workflow, and anything that reads as a note to the team. Keep what honesty requires: which analyses were prespecified in a dated plan, which were exploratory or added after the data were seen, and any deviation from the plan. Presenting the final workflow as one coherent procedure must never imply prespecification that did not happen.

Methods must describe what the code actually does. Earlier agents' Methods sections drift from the code as analyses change, so check each Methods statement (population, definitions, model, adjustment set, inference) against the script that implements it.

## 7. Figures

- The central figure shows the central finding directly: the comparison that matters, with its uncertainty, labeled in plain words.
- One idea per figure. Label lines and groups directly instead of relying on a legend where you can. Put units on axes. Titles describe; captions explain how to read the display.
- Every figure is generated by code in the pipeline and saved in `results/figures/` (in the working copy during the audit). Never edit a figure by hand.
- Panels that do not serve the story move to the supplement or out of the paper.

## 8. Register review, by hand

The confident rewrite this skill asks for has its own failure mode. Earlier agents hedged; a rewrite that strips the hedges tends to land in flat certainty, where an adverb, a reassuring compound or an absolute stands in for the evidence: "clearly demonstrates", "rigorously validated", "fully adjusted", "no evidence of". That is not the confidence this skill wants. Confidence is the estimate, the interval and the design-matched verb in the sentence; an adverb in front of them adds nothing and invites the objection the number would have answered. The same goes for staging: "This is the key finding", "Rural patients did not simply die more often", a Discussion paragraph that ends on a maxim. State the finding with its number and stop.

Do this review by reading every sentence in context, not with a phrase scan. Whether a shape is a tic depends on the section, the claim and the field. biomedical-publication-suite's `references/prose-register.md` is the guide: the families to look for by section, the shapes that are earned in scientific prose (real lists, literal terms such as "robust standard errors", short sentences in Methods, "Table 2 shows", discourse markers such as "Notably"), and the rules that protect the science. Four of its rules matter most here:

- **Read the whole draft before editing.** A sentence built for rhetorical shape is disproportionately likely to misstate the result; a "key finding" that names a secondary endpoint is an accuracy finding, and it goes into the report, never a silent fix.
- **Invent nothing.** The fix for a vague sentence is a specific one, and the specific comes from `_audit/work/results`, a retrieved source or the user. Where a number or citation is missing, write `[DATA NEEDED: what]` and list it in the report.
- **Constructions carry claims.** Superlatives, rankings, scope words ("all", "only", "each"), simultaneity, negations and hedge conditions survive the rewrite claim by claim, alongside the claim list in section 2.
- **Newcomer read.** The rewrite, the README and the docs are written right after the audit changed the project, which is exactly when prose leans on a version the reader never saw: "the corrected cohort", "the revised exposure definition", "now", "no longer", "after the fix", a Methods paragraph that explains how an error was repaired instead of what the procedure is. Hand the final text alone to a fresh subagent that never saw the original and fix every point it raises. Analytic history belongs in `docs/CHANGELOG.md` and the report, not in the paper.

Read the slots where staging concentrates (title, headings, abstract conclusion, Discussion opener, the last sentence of each Discussion paragraph, figure titles) with a reader that did not write them: a subagent given the draft and the guide, or, if none is available, say in the report that the read was not independent.

The report and your message to the user get the same review. Lead with findings and their numbers, label sections plainly, and keep verdict-shaped headings and certainty adverbs out of both.

## 9. Checks after drafting

1. `python3 $S/hedge_lint.py <draft>`: caveat placement near 100%, no caveats in the abstract (apart from a journal's own limitations field), results, or conclusion, no stacked hedges outside Limitations.
2. `python3 $S/trace_numbers.py --doc <draft> --outputs _audit/work/results`: no unmatched numbers.
3. Every verb matches the claim list. There are no silent upgrades.
4. Methods match the code.
5. `publication_text_lint.py` from publication-artifact-refiner, if installed, for process leakage and filler.
6. The register review in section 8 is done by reading: no staging, no certainty adverbs standing in for estimates, nothing added that the outputs do not contain, no phrase that leans on the pre-audit version.
7. Read the abstract alone, cold. Within its results and conclusion, a reader knows what was found and why it matters.
