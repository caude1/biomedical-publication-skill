# Accuracy: reproduce, trace, re-derive, read the code

Read this before steps 2 and 3. The aim is simple: every number the paper reports comes from code that runs, and that code is correct.

## Contents

1. Reproduce before you compare
2. Clean-state reruns and slow pipelines
3. Tracing reported numbers
4. Re-deriving the headline estimate
5. Reading the code: the error catalog
6. Statistical misapplications to recognize
7. Consistency checks you can compute
8. Triage and fixing

## 1. Reproduce before you compare

Agents that know the target numbers can debug toward them. In one reproduction benchmark, agents given the paper were more likely to call deliberately irreproducible results reproduced, and an instruction to "try defensible alternatives and keep what matches" produced plausible fabricated output. So compute independently first, record what the code produces, and only then compare with the paper; a genuine mismatch is a finding.

- **Find the entry point:** the inventory's candidates, the README, `pipeline.*`, `Makefile`, `_targets.R`, `Snakefile`. Read it before running it, and list every path it writes. Code that writes into `data/raw` (the inventory's "may write into raw data" section) must be stopped before any rerun: point it at a copy, or change it to read raw data read-only.
- **Live sources.** When the raw data came from a live registry or API, the dated snapshot the analysis used is the raw data. Reproduce from the snapshot. A fresh fetch is a separate drift check: write it to `_audit/runs/refetch_<date>/` and report how the key numbers moved, in one line.
- **List the whole output tree before interpreting anything.** Agents often read the wrong output file.
- **Settle dependencies first, without changing the project's environment.** Run its interpreter as it is; when packages are missing, build a separate environment inside `_audit/work/` (`python3 -m venv _audit/work/.venv`, then install from `requirements.txt` into it). Environments are not mirrored into `work/` (only renv's setup files are copied), so `renv::restore()` or `npm ci` run inside `work/` builds a separate library there. Record R/Python and key package versions (`sessionInfo()`, `pip freeze`).
- **Prefer an established package to a hand-written implementation** of a standard method. Reviewers expect the published package, and a custom implementation raises the question of why it was used. When the project hand-coded one, refit with the package in the working copy (installed as the session's permissions allow, outside any project's renv or virtual environment), confirm the results agree, and recommend the switch; keep any comparison of the two in the report.
- **If a file seems to be missing, search** the project and its parent folder before declaring it missing. Files are often not where the README says.
- **Check which tools exist before choosing how to run** (`command -v quarto R Rscript python3`). If a `.qmd` pipeline needs Quarto and it is missing, run `Rscript -e 'knitr::purl("analysis/pipeline.qmd", "pipeline_purled.R")'` in the working copy and run that script, or render `.Rmd` files with `rmarkdown::render()`. Ask before installing system tools.
- **Run the pipeline inside `_audit/work/`** (the helper scripts run from the project root), and keep each run's outputs and console logs in `_audit/runs/<run>/`. Record every run (command, runtime, what failed and why, what it produced) for the reproduction chain in `_audit/REPORT.md`.

## 2. Clean-state reruns and slow pipelines

- **Run twice when you can:** first with existing caches (a fast check that the code runs at all), then from raw data with caches bypassed (the real reproduction).
- **Compare runs** with `compare_outputs.py <before> <after>`. It aligns tables by column name and matches rows by a unique identifier (pass `--key nct_id`, or let it use a unique first column), so an added column or a dropped row is reported as such instead of making every later cell "differ". Duplicate identifiers make key matching unreliable; the tool then compares sorted rows, still reports added or dropped columns and rows, and says so (pass a compound `--key` to match exactly). Its verdict is VERIFIED (everything compared matched), DIFFERENT (anything differs, is missing, or is new; pass `--allow-new` when new outputs are expected), PARTIAL (nothing differed, but some files, such as figures, could not be compared), or NOTHING COMPARED (a folder is missing or empty). Add `--moves archive/file_moves.csv` after a reorganization.
- **To bypass a cache,** use the pipeline's own switch if it has one. Otherwise rename the cache folder aside in the working copy (the working copy is disposable; the project's own caches are never touched in part 1) and let the rerun rebuild it.
- **For a long pipeline,** reproduce the path to the primary result first. Run long jobs in the background and read code while they run. Cache and parallelize as the project's own guide describes, if it has one.
- **When raw data is absent** (licensed extracts, data on another machine), verify from the earliest intermediate available and record the gap under "Not verified". Never mark it as reproduced.

## 3. Tracing reported numbers

`python3 $S/trace_numbers.py --doc <manuscript> --doc manuscript/tables/table1.csv --outputs _audit/work/results --out-md _audit/runs/number_trace.md` lists every number in the documents (manuscript text and any hand-built table files) with the output values it could come from. A number "found" in an output is a candidate source: the same value can appear in an unrelated table. "Consistent" means an n/N (x%) statement computes correctly within the text; it says nothing about where n and N came from.

- **Unmatched numbers** each need a resolution:
  - a typo: correct it from the output;
  - stale: regenerate the output and update the text;
  - computed by hand: make the code compute and save it;
  - untraceable: recompute it or remove it.
- **Derived numbers** (matched only through a percent or exponent transform) need their arithmetic checked once.
- **Arithmetic mismatches** are "n/N (x%)" statements in the text whose percentage does not compute. Each is an error to fix.
- **Numbers the tracer cannot see:** values held only in `.rds`, `.RData`, or `.parquet` outputs. Print them from R or Python, or better, have the code also save them as a small CSV so the paper's numbers stay traceable.
- **Confirm the specific source cell** for every claim-bearing number (abstract, central results), not just some matching value somewhere.
- **A mismatch does not mean the code is right.** Decide which side is wrong. Sometimes the paper was corrected by hand and the code never caught up.
- **Tolerances when comparing a reproduction:**
  - counts: exact;
  - estimates, intervals, and standard errors: agree at the reported precision;
  - p-values: agree at the reported precision, and a value reported as a threshold (P < .001) is satisfied by the recomputed value;
  - percentages: within 0.1 percentage point.
- **Check denominators** across the abstract, the flow diagram, Table 1, and the models. They must agree wherever the same population is analyzed.
- **Check figures against their data:** read the plotting code's input, not the image.

## 4. Re-deriving the headline estimate

One independent re-derivation of the central estimate is the strongest single accuracy check. Do it for the central estimate only, not for every model.

- Write fresh code, ideally in the other language (R and Python fail in different ways), from the analytic dataset or from raw data. Implement the model as the Methods describe it; do not copy the original code.
- N must match exactly, the estimate to about three significant digits, and the standard error closely.
- A mismatch tells you where to look:
  - a different N points to filters, merges, or missing-data handling;
  - the same N with a different estimate points to model specification, variable coding, or reference levels;
  - the same estimate with a different standard error points to clustering, robust errors, or degrees-of-freedom corrections.
- If the Methods and the code disagree, one of them is wrong. Decide which is scientifically correct and fix the other.

**Hand-coded measures.** When the headline is a count or classification that someone made by hand (adjudicated endpoints, chart review, coded free text):

- Write the coding rule down before looking at any record: what counts, what does not, and the terms or criteria that decide it.
- Apply it to every record without looking at the original codes. If tracing provenance has already shown you those codes, hand the coding to a fresh agent that has not seen them. Let code flag candidates, then confirm each by reading the record.
- Compare record by record with the original coding. Report the agreement, and resolve every disagreement by the rule.
- List borderline records by ID with the decision and the reason, and give the count with them included.
- If a subagent is available, have it code a sample independently from the written rule and report its agreement with yours.

A coding that exists only as a hand-made file with no written rule is a fixable problem: the rule and the code that applies it replace the file.

**Verifying an exposure or event list.** When the analysis rests on a list of events or statuses (closures, diagnoses, program start dates, site classifications) assembled from administrative records:

- Check in both directions. Confirming each recorded event finds the false ones; missed events need a systematic sweep of every unit and period against independent sources, because nothing points to them.
- Correct by fixed, deterministic rules applied to every unit without reference to outcomes, and record each correction with its sources in a verification register. Flag corrections that rest on a single source, and report how the central estimate changes when they are undone and when each type of correction is undone.
- Say plainly how confident the list is and why, and record what kind of error the source files make, known or suspected.

**Provenance back to the first pull.** Find the earliest version of the data the project received and account for every difference between it and the analytic file: each filter, recode, merge, and correction, with the count it changed. An unexplained difference is a finding.

## 5. Reading the code: the error catalog

**Screen the analytic data first.** Before trusting any model, look at the data it runs on:

- missingness by variable;
- each variable's distribution, with its five highest and five lowest values;
- the number of distinct values per variable;
- impossible values and duplicate records.

Keep this screen separate from the research question. Do not look at exposure-outcome associations while screening. Duplicated or badly merged records and biologically impossible values are the two most productive places to look.

Then search the code for the errors below, exhaustively. Most earlier-agent errors are here.

**Joins**
- Check row counts before and after every merge.
- Many-to-many joins duplicate rows.
- Inner joins silently drop unmatched keys.
- Key types can mismatch (numeric vs character IDs, lost leading zeros in FIPS or ZIP codes).
- When you fix a join, make it assert its own cardinality: `validate="1:1"` with `indicator=True` in pandas, or `relationship = "one-to-one"` and `unmatched = "error"` in dplyr 1.1 or later.

**Filters**
- Inclusion and exclusion criteria can be applied in the wrong order, or after outcomes were computed.
- A filter on `==` drops NA rows silently.
- A lingering `group_by` changes later summaries.

**Missing-value codes**
- Codes such as -9, 99, 999, 9999, "Unknown", or blanks get treated as values.
- Means and sums are sometimes computed without handling NA.

**Coding**
- Scale items can be reverse-coded.
- 0/1 meanings can be swapped.
- The reference level can differ from the one the paper describes.
- Codes (ZIP, ICD, stage) can be treated as numbers.
- A cut-point can use `>=` where the paper says `>`.

**Units and time**
- Mixed units (mg vs g, months vs years).
- Date formats parsed the wrong way round.
- Time zero, follow-up start, and lag direction set incorrectly.
- Person-time computed in the wrong unit.

**Units of analysis**
- Duplicated IDs.
- Patients confused with encounters.
- Clustered observations treated as independent.

**Code sets**
- ICD matched by prefix when it should be exact, or the reverse.
- ICD-9 and ICD-10 mixed without a crosswalk.

**Leakage (prediction work)**
- Scaling, imputation, or feature selection done before the train/test split.
- The outcome, or information from the future, present among the features.
- The same patient in both training and test sets.
- Tuning done on the test set.

**Aggregation**
- Rates averaged instead of pooled from counts.
- Percentages of percentages.
- Ecological units weighted incorrectly.

**Randomness**
- No seed.
- A seed reset inside a loop.
- A bootstrap that ignores the clustering unit.

**Outputs**
- Numbers hard-coded into the manuscript or tables.
- Output files edited by hand.
- Stale files.
- Figures and tables built from different versions of the data.

## 6. Statistical misapplications to recognize

**Any design**
- Subgroup claims drawn from separate p-values rather than an interaction test.
- Confirmatory claims with no account of multiplicity.
- Continuous variables dichotomized.
- Stepwise selection.
- Post hoc power.
- Adjustment for mediators or colliders.
- Covariate coefficients read causally (the "Table 2 fallacy").
- Repeated measures or clustering ignored.
- Regression to the mean in change scores.

**Observational cohorts**
- Immortal time from an exposure defined after time zero.
- Prevalent-user bias.
- Confounding by indication.
- Selection that depends on the outcome.
- Competing events handled with 1 minus Kaplan-Meier.
- Eligibility, treatment assignment, and time zero misaligned relative to the target trial.

**Survival**
- Proportional hazards untested where it matters.
- The wrong time scale.
- Left truncation ignored.

**Case-control**
- Matched designs analyzed without conditioning on the matching.

**Randomized trials**
- Per-protocol results presented as primary.
- Significance tests on baseline balance.
- Large, imbalanced missing outcomes handled by complete-case analysis.

**Prediction**
- Too few events per parameter.
- No internal validation (no bootstrap optimism correction).
- Discrimination reported without calibration.
- Thresholds chosen on the test set.

**Diagnostic accuracy**
- Spectrum bias.
- Verification bias.
- A threshold chosen and evaluated on the same data.

**Counts and rates**
- A missing log person-time offset.
- Overdispersion ignored.
- Zero inflation ignored.

**Panels and aggregate data**
- Clustering at the wrong level.
- Few clusters without a small-sample correction.
- Staggered-adoption difference-in-differences estimated with plain two-way fixed effects.
- Individual-level conclusions drawn from aggregate data.

**High-dimensional data**
- No false-discovery control.
- Batch effects left in.
- Features selected and tested on the same data ("double dipping").

**Survey data**
- Weights, strata, or PSUs ignored.

**Missing data**
- Complete-case analysis when missingness is substantial and related to exposure or outcome.
- Imputation models that omit the outcome.

## 7. Consistency checks you can compute

- **Percentages** against their counts and stated denominators.
- **Interval and p-value agreement for ratio measures** (Altman and Bland):
  - SE = (ln upper − ln lower) / 3.92;
  - z = |ln(estimate)| / SE (the absolute value: the formula is for the two-sided P);
  - P ≈ exp(−0.717z − 0.416z²) for a quick check; when a disagreement matters, compute the exact normal tail, P = 2(1 − Φ(z)).

  Disagreement prompts inspection (it may be a different test or an asymmetric interval); it is not an automatic correction.
- **GRIM:** a mean of n integer-valued responses must equal some whole-number total divided by n, after rounding (accept either rounding direction). The test only has power when n is below 10 to the power of the reported decimal places, and only for granular data such as counts or Likert items. GRIMMER extends the idea to standard deviations.
- **Test statistic, degrees of freedom, and p-value** agree.
- **Subgroup Ns** sum to totals, and the flow diagram's arithmetic closes.
- **No unexplained change** in N across tables or columns, and no years, sites, or groups dropped without comment.

## 8. Triage and fixing

- Find everything first, then triage. Filtering while searching makes you miss things.
- A potentially material problem you cannot resolve yet is **under investigation**, not a caveat. A fix that needs data you do not have is **blocked**; keep the affected claims marked unverified.
- Fix fixable problems at their source in the working copy (the starting state is preserved in `_audit/baseline/`), rerun, and let `compare_outputs.py` show exactly which numbers moved. Record each in the fixes table of `_audit/REPORT.md`.
- When a pipeline is rewritten, first make the rewrite reproduce the original outputs exactly. Then put each logged problem behind a switch whose default reproduces the original behavior, so the effect of every fix on every reported number can be measured and the user can decide each one.
- A fix that flips the sign of the central estimate, moves it across the paper's decision threshold, or changes its magnitude substantially may change the narrative. Say so in the updated narrative and its "how and why it changed" table.
- Before calling anything fatal, attempt the fix. If the corrected analysis still supports a real claim, even a weaker one, the problem is fixable and the framing may need to change.
