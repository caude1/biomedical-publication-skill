# Statistical reporting and result consistency

Load for numeric results, statistical methods, effect interpretation, displays, cross-artifact consistency or requested reanalysis. Baselines: [SAMPL](https://www.equator-network.org/wp-content/uploads/2013/07/SAMPL-Guidelines-6-27-13.pdf) and [ICMJE statistics](https://www.icmje.org/recommendations/browse/manuscript-preparation/preparing-for-submission.html), checked 2026-09-05. Specialized analyses require their own current methodological sources.

## Choose the work boundary

| Work | Can proceed from | Evidence and completion limit |
|---|---|---|
| Edit statistical prose | Supplied text/outputs | Preserve values/status; identify ambiguity. This does not validate the analysis. |
| Check reporting/consistency | Tables, model output, protocol/SAP and manuscript | Trace findings and reconcile repeated facts. State if raw-data reproducibility was not checked. |
| Reproduce a stated calculation | Authorized data plus code or fully specified method | Run in an isolated output location; retain command, runtime, inputs/results. Never replace originals silently. |
| New or changed analysis | Data access, sufficient methods and task authorization | Specify estimand, population, outcomes and assumptions. Material unresolved choices need author/statistical input; continue independent checks meanwhile. |

Do not rerun an unknown pipeline merely to polish a paragraph. Never invent software versions, adjustment sets, imputation, sample-size rationale, assumptions or diagnostics.

## Bind a result before writing it

For each important result identify outcome/endpoint role; estimand/comparison; analysis population; unit of analysis/denominator; time point; estimate type/value; interval type/level; p-value/test when relevant; adjustment/model; source file and exact locator. Use source output directly for a compact task; retain this context in existing notes or an optional results ledger when many results need reconciliation.

Check what generated each percentage. An observed event proportion can have an integer numerator and denominator. A survey-weighted proportion, standardized risk, or time-to-event estimate can differ from the raw fraction. Give the unweighted sample size or number at risk separately when available. Preserve the estimator and uncertainty, and do not reconstruct a numerator by multiplying the estimate by the enrollment total.

When outputs disagree, check population, time point, model, units and source version first. Keep the disputed result unresolved until authority is established; choosing the smaller effect or newer filename is not valid reconciliation. Do not normalize legitimate analysis-set differences. A revised output invalidates dependent abstract, Results, Discussion, displays, supplement and response claims until rechecked.

## Interpret within the analysis

- Give magnitude and uncertainty, not just a significance label. Preserve interval type: confidence intervals and Bayesian credible intervals differ. Match relative/absolute measures to their actual estimand.
- Nonsignificance does not establish no effect or equivalence. Equivalence/noninferiority requires suitable design, margin and analysis; a wide interval may be inconclusive.
- Preserve confirmatory/exploratory, primary/secondary, subgroup, sensitivity and post hoc status. A sensible final rationale does not establish prespecification.
- Between-subgroup claims require the relevant interaction/heterogeneity analysis; one significant and one nonsignificant estimate alone is insufficient.
- Distinguish SD/SE, participants/observations, biological/technical replicates, events/participants and risk/rate/odds/hazard. Repeated measures and clustering affect uncertainty.
- Describe missingness, exclusions, multiplicity and diagnostics only as performed/documented. Omitting testing context cannot make exploratory p-values confirmatory.
- For prediction preserve validation, leakage controls and performance uncertainty. Discrimination alone does not demonstrate calibration, transportability, clinical usefulness or treatment benefit.
- For causality require an explicit estimand and design/identification argument. Randomization supports applicable comparisons, not every derived claim. Nonrandomized causal analyses need stated assumptions and sensitivity limitations; adjustment alone is insufficient. Keep necessary qualifications beside the claim.
- Clinical relevance, mechanism and causality are distinct judgments. Do not replace an uncertain mechanism with a confident causal sentence.

How an effect is worded (percent change or multiple, relative or absolute, which noun the measure supports) and how numbers, P values and intervals are formatted are covered in [conventions](biomedical-conventions.md).

## Choose the wording from the design

Use the pertinent row when the proposed conclusion depends on how the estimate was obtained.

| Source result | What to establish before writing | Consequence for the manuscript |
|---|---|---|
| Randomized trial with treatment discontinuation, crossover or rescue therapy | Which treatment strategies, population, endpoint, handling of post-randomization events and summary measure define the question? How were missing observations handled in estimating it? | A comparison by randomized assignment can address outcomes after rescue therapy. A hypothetical contrast without rescue answers a different question. Identify a different estimand as a separate question, even if it uses the same data. A sensitivity analysis in the E9(R1) framework tests assumptions about the same estimand. [ICH E9(R1)](https://www.fda.gov/media/148473/download) |
| Cohort defined from visits or claims | Identify eligibility, exposure ascertainment, baseline, follow-up, and the unit of analysis. Determine whether the recorded date marks onset, diagnosis, or first appearance in the available data. | Describe a first *recorded* diagnosis when onset is unknown. If future treatment receipt defines the group at baseline, flag the timing problem before interpreting a treatment effect. For a target trial emulation, compare these times with the specified trial protocol. [TARGET](https://www.bmj.com/content/390/bmj-2025-087179) |
| Survival analysis | Identify the event, time origin, time horizon, censoring and competing events. Read whether the output reports a hazard, cumulative incidence or survival probability. | A hazard ratio of 0.70 alone gives no 30-day absolute risk difference. Death before readmission precludes later readmission. Describe how death was handled before reporting a readmission probability. [Competing-risk methods](https://pubmed.ncbi.nlm.nih.gov/26858290/) |
| Diagnostic test comparison | Identify the reference standard, threshold, denominator and disposition of unverified or indeterminate results. | With only a cross-tabulation against another test of unknown accuracy, describe agreement and its direction. Disease sensitivity and specificity need evidence about true condition status. [FDA diagnostic-test reporting](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/statistical-guidance-reporting-results-studies-evaluating-diagnostic-tests-guidance-industry-and-fda) |
| Prediction model | Identify when the prediction would be made, whether predictors were available then, and exactly how patients, sites or dates were separated between development and evaluation. | A random split within one cohort is internal evaluation. A patient appearing in training and evaluation through different visits compromises claims about performance in new patients. Describe the actual evaluation population, discrimination, calibration and uncertainty as available. [TRIPOD+AI](https://www.bmj.com/content/385/bmj-2023-078378) |
| Change within a group | Check whether the estimate tests change within each group or the difference in change between groups. | A decline in one arm and little change in the other does not quantify their contrast. For a treatment comparison, locate the reported between-arm estimate and interval or confine the prose to the within-arm results. |

## Mechanical and scientific checks

Check denominators/populations across prose/displays, totals where summation is meaningful, percentage rounding, interval bounds/order, estimate labels, units, signs, precision and cross-references. Flag impossible probabilities or n; do not repair them from plausibility. Distinguish a ratio from its log or a difference. Negative values are meaningful on some scales. An odds, risk or hazard ratio point estimate below zero indicates a scale or transcription problem. A zero cell can put an unadjusted ratio at a boundary or leave it undefined. Rounding can also produce a displayed zero. An approximate interval may extend beyond a parameter's bounds. Check the interval method and source output before flagging a transcription error, and never truncate a bound editorially.

Recompute only quantities identifiable from inputs. Percentage checks need the correct denominator and rounding tolerance. CI/p-value disagreement prompts inspection of test/model/interval method; it is not automatically an error. Rounding, asymmetric intervals, transformations and different tests can defeat simple formulas. If software prints a zero p-value, obtain higher-precision output rather than inventing a threshold.

For figures/tables retain source data/code, transformations, normalization, exclusions and version. Check axes, scales, uncertainty bars, n, units and captions against data. Do not redraw observed data through an image-generation model or infer exact plot values when source values are required.

## Reproducibility handoff

For computation record data dictionary/cohort definition, immutable input locator or hash, code version, command, runtime/package versions, seed when relevant, output path and material deviations. Verify the requested result path rather than claiming the entire project is reproduced. Availability statements describe actual access conditions; restricted data need not be public.

Conclude with checks performed, authoritative outputs, discrepancies resolved/open and whether validation reached reporting consistency, calculation reproduction or broader analysis review. Mechanical checks cannot certify design, model specification or clinical interpretation.
