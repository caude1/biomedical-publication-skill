# Judging the science and extending it

Read this before steps 4 and 5. Judging asks whether each choice was right. Extending asks what the data can still show. Both serve one goal: the strongest true version of the paper.

## Contents

1. The question and the central claim
2. Reviewing analytic decisions
3. The first objection
4. Unexploited strength
5. Extend: where to look
6. Choosing what to run
7. Robustness that earns its place
8. Surprising results
9. Literature
10. Fatal flaws and salvage

## 1. The question and the central claim

Write the question in plain words: population, exposure or intervention (or predictor), comparator, outcome, time horizon, and the number that answers it (the estimand). Then ask:

- **Is the question the one the analysis answers?** The common failures are a causal question paired with an associational analysis, an individual-level question asked of aggregate data, and a prediction question answered with an explanatory model.
- **Is there a sharper version the data answer better?** For example, "how much of the gap does X explain" rather than "is X associated with Y", or the clinically decisive subgroup rather than everyone. A sharper question that changes the headline is a reframing: propose it as the updated narrative, for the user to decide.
- **What is new?** What was known before, what this study adds, and who would do something differently if it is right. If the answer to the last question is "no one", the framing needs work before the prose does.
- **Who says what the study is?** Dated protocols and plans establish what was intended; data and executed code establish what was done. A manuscript, README, or `SAP.md` written by an earlier agent can be retrospective or simply wrong. When the code and the paper disagree (a denominator the paper calls "trials" that includes observational studies, say), the intended question and eligibility criteria decide whether the code, the wording, or both are wrong. Correcting wording to match the established question is a repair; changing the question is a reframing.
- **Don't lock onto a frame.** Compare two or three framings (the inherited one, the one the strongest result suggests, the one a clinician would care about) before settling. Early frame-lock is a characteristic failure of agent-run research. Nothing obliges the audit to approach the problem the way the original analysis did; for a consequential choice, generate genuinely different approaches and compare them before recommending one.
- **Build on what was approved.** When coauthors or a PI approved an earlier version, its framing, structure and wording are an asset. Keep what the evidence still supports, change what it does not, and say why each change was needed.

## 2. Reviewing analytic decisions

For each substantive decision, ask three things. Was it right? Is there a clearly better alternative? Would the alternative change what you would write? Act only when all three point the same way, and record each in the decisions table of `_audit/REPORT.md`.

| Decision | What goes wrong | Alternatives that are often clearly better |
|---|---|---|
| Design | Causal question with no explicit comparison; time zero undefined | Emulate the target trial: align eligibility, assignment, and time zero |
| Population | Exclusions that depend on exposure or outcome; survivors only | Restate eligibility at time zero; add the excluded group back in |
| Exposure | Measured after the outcome, or after time zero (immortal time) | A landmark or time-varying exposure definition |
| Outcome | Ascertainment differs by exposure; competing events ignored | Cumulative incidence with competing risks; a validated definition |
| Covariates | Mediators or colliders adjusted; arbitrary categories | An adjustment set from a causal diagram; splines for continuous confounders |
| Model | Poisson on overdispersed counts; a linear model on a bounded outcome | Negative binomial or quasi-Poisson; a model matched to the outcome type |
| Inference | Clustering ignored; few clusters; many unadjusted tests on confirmatory claims | Cluster-robust or wild-bootstrap inference; one prespecified primary test |
| Missing data | Complete-case analysis with substantial, informative missingness | Multiple imputation with the outcome in the model |
| Subgroups | Separate p-values compared | One interaction test, justified in advance |
| Prediction | Discrimination only; no internal validation | Bootstrap optimism correction, calibration, and a decision curve |
| Presentation | Relative effects only; units nobody thinks in | Absolute risks or rates beside ratios; effects per clinically meaningful unit |

Do not record alternatives that would merely also be defensible. The register is for choices that were wrong or clearly improvable.

### Construction choices must be airtight

The choices that build the analysis (which variables define the groups or enter the model, thresholds and cutoffs, distance or time windows, exclusions, how groups are formed or combined) decide the result as much as the model does, and a reader who cannot see why they were made assumes they were tuned. Hold each consequential one to this standard:

- **Rules, not picks.** A selection from many candidates is a written funnel that accounts for every candidate (eligibility, data-quality rules, the construct each one measures, one measure per construct when the method requires it), run as code. A hand-picked list of plausible variables is not a justification, however sensible it looks.
- **Outcome-independent grounds.** Take the rules from an external framework, the field's standard practice, the cited literature, or the version the coauthors approved, and decide and record them before the outcome models are read. Where a grouping must be fixed before outcomes, write the outcome tables without reading them until the grouping is settled. This is the honest route, and it is also what makes the paper convincing.
- **Principled values.** A cutoff comes from the literature, a standard (a regulatory distance, a guideline threshold), or a round value with a stated reason. A gradient needs at least three levels with stated spacing and a test for trend that scores each level by its median or enters the measure continuously. Two nearby cutoffs without a gradient argument add little.
- **Every model term motivated.** Each fixed effect, trend or interaction has a reason. A term that is standard and reasonable a priori needs no defense in the paper; one that is not gets its reason, and the audit checks what the estimate looks like without it.
- **Exclusions decided on prior grounds.** Data are not excluded on grounds that exist only after seeing the results; such an exclusion becomes a sensitivity analysis. A sensitivity analysis that drops units follows a principle (leave one out, a stated influence measure), never "the two largest".
- **Edge cases by rule.** An absurd record (a clinic counted as open in a year in which it saw one patient) is handled by a written rule that applies to every unit, not by an exception for the one case noticed.
- **The range of reasonable alternatives.** Test each consequential choice against the reasonable alternatives and keep the result as a check on how much the conclusion depends on it, in the register and, if a plan or guideline calls for it, the supplement. If the choice cannot meet this standard, change it (with the user's approval) rather than defend it.

**Arbitrariness review.** List every choice, setting and number a reader could take as arbitrary. For each, give its basis, the reasonable alternatives, whether the conclusion moves across them, and a recommendation: state the reason, cite precedent, change the choice, or show the range. Separate what genuinely weakens credibility from what is only nitpicking. A useful diagnostic is to ask how an advocate for a larger effect and an advocate for a null would each choose among options that could all be justified in advance, and how far apart their answers land. The exercise measures dependence on choices; it never picks the analysis.

**When a particular result is wanted.** When the author or a PI asks for a specific result (a number of clusters, a significant estimate, a smaller interval), lay out the honest routes: a stated analytic choice with its fit or cost disclosed, the result framed as a hypothesis and tested as one, or a construction rule decided before outcomes are read. Decline a search across specifications until the wanted result appears and is presented as data-driven, and say why in one sentence.

## 3. The first objection

Name the objection a knowledgeable reader in this field raises first: confounding by indication, reverse causation, selection into the cohort, exposure misclassification, a secular trend, and so on. Then:

- Show that the design already answers it, or answer it with the one analysis that addresses it most directly. A design-based answer (a negative-control outcome, an active comparator, a within-unit comparison, a lag structure) persuades more than another covariate.
- Where you can, turn it into a number: an E-value for unmeasured confounding, a tipping point for missing data, or a quantitative bias analysis for misclassification. One precise number replaces a paragraph of hedging.
  - **E-value:** E = RR + sqrt(RR x (RR - 1)), after inverting an RR below 1. Report it for the confidence limit nearest the null as well as for the estimate. Apply it to an OR or HR directly only when the outcome is rare; otherwise convert first. Compute it because unmeasured confounding is the first objection, not by reflex. An automatic E-value stands in for thinking about the specific confounder a reader has in mind.
  - **Negative control:** it must share the exposure's confounding structure and have no causal path to the outcome. It detects bias; it does not size it.
- If it cannot be answered and it undermines the central claim, the claim changes (a reframing) or the flaw is fatal.

## 4. Unexploited strength

Earlier agents undersold as often as they erred. Look for:

- Results already in the outputs that the paper never states: a dose-response gradient, a clinically important subgroup with a real interaction, an absolute difference that makes the effect tangible.
- Design strengths described apologetically or not at all: national coverage, long follow-up, a natural experiment, linked data, a validated outcome.
- A place where this study settles a conflict in the literature.
- **A rule a clinician can use.** When the product of the study is a classification, score or model, check whether a short rule applied at the point of care reproduces it, and report its agreement (κ) or, for a prediction rule, its discrimination and calibration, with the exact weights in the supplement. Prefer the simpler rule when its cost is small and stated. Translation of this kind often strengthens the contribution more than another robustness check.
- **Effects in units readers can weigh.** A conditional odds ratio from a mixed model, or a coefficient on a transformed scale, can hide the size of a real effect; model-estimated means, probabilities, or differences on the outcome scale make it visible.

Each of these can strengthen the paper without a single new model.

## 5. Extend: where to look

These are places to look, not a checklist. Each lead becomes a candidate only if it passes the earn-its-place test.

- **Variables collected but never used** (`python3 $S/column_usage.py --root _audit/work --profile`), especially ones that measure a mechanism, a dose, a timing, or a better-measured version of the exposure or outcome.
- **Subgroups with a mechanistic or clinical reason to differ,** tested with an interaction. Never a sweep.
- **Outcomes collected but unanalyzed,** or a more clinically meaningful version of the outcome.
- **Dose-response and timing.** A gradient or a sensible lag strengthens the causal reading more than another adjustment does.
- **Mechanism,** through mediation only when the temporal order and assumptions hold.
- **Alternative framings** of the same data that answer a more interesting question.
- **Secondary hypotheses** the data test cleanly.
- **External data** that sharpens the contribution: an external validation cohort, public benchmarks, national rates for context.
- **Recent literature** that the data can confirm, extend, or contradict.

## 6. Choosing what to run

For each candidate, write the earn-its-place statement (question, how the result would change the paper, decision rule), then estimate its cost and the chance its result is informative.

- Rank by how much the result could change the paper, not by ease or by count.
- Choose the few that fit one story. A good set answers the questions a reader asks in sequence after reading the central finding: Is it real? How big is it? For whom? Why?
- Run them in `_audit/work/analysis/sandbox/` and record every result. Integrate only those that change the paper; everything else keeps its one line in the register.
- If an analysis cannot be run as registered (a model will not converge, a variable turns out unusable), record that as its result. Do not quietly substitute a different analysis under the same entry.
- **Analyses that classify records** (counting which trials registered an outcome, which notes mention a symptom) need their coding rule registered with the question, before any record is read. Code flags candidates and every flag is confirmed by reading. Borderline records are listed by ID with the rule's decision, and the count is also given with them included. One rule shared across related analyses keeps their results comparable.
- Use the field's standard measures. Do not invent metrics, composite scores, or indices; agents do this, and readers distrust it.
- A heterogeneity split is not a robustness check. Pursue a subgroup only as its own question with its own reason.

## 7. Robustness that earns its place

Run one or two checks, each aimed at a specific threat to the identification or measurement of the central estimate. A check shows how much the conclusion depends on a choice; it does not decide which choice is right. If a check moves the estimate a lot, report the dependence plainly and decide the primary analysis on scientific grounds (a change of primary analysis is a recommendation for the user). A check earns its place only if you can answer yes to all three of these questions (Morris, Kahan and White's test for sensitivity analyses):

1. Does it answer the same question as the primary analysis?
2. Could it reach a different conclusion?
3. If it did, would there be genuine uncertainty about which result to believe?

An analysis that fails the first question is a secondary analysis with its own question, and it must earn its place on those terms. One that fails the second or third changes nothing you would write.

- **Review the existing battery, not only what to add.** Recommend which inherited checks to drop, narrow, or keep in reserve; a paper with fewer, sharper checks reads as more confident. A check run only to answer an internal or anticipated reviewer question, with an inert result, stays in the register and the report, not in the paper, unless a plan or reporting guideline names it.
- **Change one assumption per check.** When several change at once, a shift cannot be traced to its cause.
- **Check the core estimate,** not every coefficient in the model. Choose any alternative covariate set for a structural reason, not by rotation.
- **Prefer a check that could plausibly fail.** A check that cannot fail cannot persuade.
- **Report each in a sentence in Results,** with a supplementary table if needed. Never as a battery; supplementary material is not a place to park everything that was run.
- **Specification curves and multiverse analyses** are justified only when the central finding hinges on choices that are genuinely arbitrary among equally reasonable options, and then as one figure. When one option is clearly best, varying it only buries the answer among worse alternatives.

## 8. Surprising results

AI-driven research fails in a characteristic way: a bug gets reframed as a surprising finding. Before a surprising new result leads anything:

- rerun it from a clean state;
- inspect the raw rows that drive it;
- recheck the coding of every variable it involves;
- make sure it is not carried by a handful of observations or a data artifact (a coding change in one year, one site, one batch);
- check that it has a sensible explanation, or say plainly that it is unexplained.

A surprising result that survives this deserves prominence. One that has not been through it deserves none yet.

## 9. Literature

Use the available tools (PubMed, scite, paperclip, web search) to answer three questions:

- Has recent work already shown this?
- Does recent work contradict it?
- What is the best comparison number?

Cite only what you retrieved, check for retractions and corrections, and verify every DOI or PMID. Claim "first" only after a search that supports it, and then state it plainly ("no previous study has…").

## 10. Fatal flaws and salvage

A flaw is fatal when the central finding is invalid and no fix or redesign within the available data recovers it. Examples:

- exposure measured after the outcome, with no way to repair the timing;
- an outcome defined partly by the exposure (circularity);
- a comparison group that is structurally incomparable in a way no design or adjustment addresses;
- data that do not contain the population the question is about;
- an "effect" that is an artifact of how the data were built.

Attempt the fix before declaring the flaw fatal. If the corrected analysis still supports a real claim, even a weaker one, the flaw is not fatal; the framing changes.

Salvage options:

- a descriptive or methodological contribution;
- a different question the same data answer well;
- a feasibility or pilot framing that motivates a future study;
- folding the work into a related project.

Present the flaw and the salvage in the report, as the first recommendation. Do not carry out the salvage without approval.
