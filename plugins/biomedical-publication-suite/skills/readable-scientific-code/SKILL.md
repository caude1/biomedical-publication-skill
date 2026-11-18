---
name: readable-scientific-code
description: Write, review, and simplify readable code for coursework and scientific analyses, including research reports, R Markdown or Quarto documents, notebooks, and reproducible scientific projects. Apply automatically in these settings, especially when code will be shared. Prefer organized notebooks and proportionate engineering while preserving scientific meaning and results. General application development is outside automatic scope.
license: MIT
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check_update.py *)
---

# Readable Scientific Code

Write code that its intended readers can understand, modify, reproduce, and comfortably explain. Correctness, necessary functionality, and scientific validity come first. Complexity stays when its benefit earns its place. Coursework should resemble thoughtful student work; never introduce artificial awkwardness or mistakes to imitate a student.

## Check for updates

The first time this skill is used in a session, run its update check as one command with nothing chained to it: in Claude Code `python3 ${CLAUDE_SKILL_DIR}/scripts/check_update.py`, elsewhere `python3 scripts/check_update.py` from this skill's folder. It contacts GitHub at most once a week, sends nothing about the user or their work, and never changes the skill. Follow what it prints as the [update guide](references/updates.md) describes: offer an available update, and after an update, tell the user what changed and how to use it. Mention any other result only if asked. Skip the check when the user wants no network use.

## Calibrate to the task

Infer the audience, data stability, and deliverable from the request and project. Follow suitable course or project conventions without asking about routine style differences. Ask only when an unresolved choice materially affects the work.

- **Coursework:** assume a reader who understands the subject but is learning to code. Favor recognizable operations and visible calculations; respect assignment constraints.
- **Exploratory research:** assume a collaborator comfortable with routine analysis. Make inputs, transformations, and important assumptions easy to inspect.
- **Publishable research:** retain that readability while strengthening provenance and verification as needed for the scientific claims and reproducibility requirements. Publication alone does not justify a framework, container, or elaborate test suite.
- **Reusable tools and production components:** changing inputs, public interfaces, repeated use, and consequences of failure can justify functions, modules, tests, and error handling. Apply these criteria when such components occur within a scientific project or this skill is explicitly requested; do not remove necessary protections in the name of simplicity.

## Prefer notebooks for analytical work

Use notebooks for new substantive analyses, including exploratory work: usually `.Rmd` or `.qmd` for R, and an appropriate notebook format for Python. Prefer them even when little explanatory prose is needed. An explicit request for a script takes precedence. When cleaning up an existing script, preserve its format and suggest a notebook conversion if useful; convert only when requested or clearly included in an authorized reorganization.

- Give the notebook a clear title, a useful subtitle when appropriate, and descriptive section headings matched to the task. Add a table of contents when it improves navigation in a long notebook. Headings, code, comments, and useful outputs can provide most of the explanation; add prose where the audience or assignment needs it.
- Use well-scoped chunks with descriptive labels where supported. Each chunk should handle a coherent task or related steps. Keep readable pipelines intact; avoid both one giant analysis chunk and a chunk for every small transformation. Place outputs near the code that produces them.
- Use scripts mainly for short helpers or one or a few focused operations, such as an export or a computation runner. Longer scripts need a concrete execution or integration reason. If an analysis outgrows one notebook, consider a few coherent notebooks before a pipeline of broad scripts. Explain how any external computation connects to the notebook.

Keep a small helper used only by one notebook in that notebook when practical; share it in a short script when several notebooks need the same operation.

## Decision rules

1. **Use existing packages and familiar tools.** For any standard task (reading and reshaping data, models and tests, tables, figures, file handling), use an established, maintained package or library function and ordinary idioms instead of writing your own, and prefer them over clever constructions, deep nesting, and custom infrastructure. Reinventing a solved task costs readers' trust and invites errors. Write a custom implementation only for a specific reason (no suitable package, a demonstrated correctness or performance problem, or an assignment that requires it), and say why in a comment. Check for a suitable package operation before writing a helper, and install a needed package as the session's permissions allow. Default to R for analyses, favoring straightforward tidyverse tools alongside ordinary base R and statistical packages. Choose Python or another language for better-suited packages or a credible, material runtime advantage; Python is not inherently faster. Preserve a suitable existing implementation.

2. **Make each argument earn its place.** Omit redundant defaults and settings with no useful effect. Retain choices determining parsing, missingness, ordering, grouping, methods, reproducibility, or useful presentation. Briefly explain consequential or unfamiliar choices. When an option's effect is uncertain, compare relevant values, types, counts, estimates, or output with and without it. If equivalence cannot be established, retain it and report the uncertainty.

3. **Follow the analytical reasoning.** Keep short, readable, single-use operations together. Introduce an intermediate object when it will be reused, needs inspection, or makes substantial logic easier to follow. Avoid both a named object for every step and a long expression that conceals decisions. Use descriptive names, whitespace, consistent indentation, and readable line breaks.

4. **Comment with purpose.** Use short, frequent comments before meaningful steps, usually one or two lines explaining purpose, assumptions, denominators, or consequential choices. Explain unfamiliar mechanics when needed. Adjacent prose can supply the explanation; avoid a comment quota, obvious syntax narration, decorative banners, edit history, and commented-out alternatives. Use prose for reasoning or interpretation that needs it; extensive narration is unnecessary.

5. **Abstract stable shared logic.** Accept modest repetition when it keeps analyses or figures easy to change independently. Use a function for meaningful, stable logic that should change consistently across its uses, or when naming an operation materially clarifies reasoning or prevents errors. Apply the coupling test: would a future change reasonably apply to every use? Growing caller-specific flags suggest separate operations. Neither a fixed repetition threshold nor a blanket ban on single-call functions replaces this judgment.

6. **For fixed, understood data, prefer direct code.** Inspect inputs and verify the work, then normally omit routine assertions, optional join safeguards, fallback branches, and hypothetical edge-case handling from the shared analysis. Do not retain checks solely because inputs might change someday. Persistent checks need actually varying inputs, a specification requirement, or an observed problem requiring continued detection. Preserve actual missing-value handling, eligibility rules, identifier handling, and denominator logic. Let adequate library errors surface; avoid wrappers that duplicate them and suppression or fallback values that conceal data problems.

7. **Keep scientific choices visible.** Show data sources, observation units, eligibility, missingness, transformations, denominators, assumptions, and calculations in the main analysis artifact. Orient readers using existing prose or a concise, non-sensitive input preview or summary as useful; show meaningful cohort changes without adding a table for every filter. Keep substantive analytical steps visible, and identify the inputs and outputs of any external helper or computation.

8. **Verify without adding clutter.** Match verification to the actual risks and change: inspect inputs, reconcile counts and denominators, verify important calculations, and execute the relevant work without hidden state. Render R reports or run standalone scripts in a fresh process; for Jupyter, restart the kernel and run all cells. Use separate verification code when it has lasting value; do not automatically create an audit package or test file. Report what was verified and material limits. Verification is not permission to add models, outcomes, or other analyses.

9. **Minimize the sharing burden.** Prefer a small set of necessary files and dependencies, self-contained reports where practical, and simple relative paths from a stated execution directory. Favor fast, stable, pinned public URLs when the trade-off is small; use local exact inputs for offline access, unreliable or costly downloads, privacy, or archival needs. Respect data-sharing restrictions. Add packages when their benefits outweigh setup cost. Record provenance and relevant versions proportionate to reproduction needs; add lockfiles, containers, or a README for concrete setup or reproduction benefits. Choose caching versus separate computation case by case; cached results must track relevant inputs and settings. Keep credentials and machine-specific personal paths out of shared code.

10. **Keep outputs clear.** Use informative labels, units, denominators, and sensible display precision. Preserve unrounded calculations. Populate narrative results from computed objects when supported; check manually maintained results against outputs. Prefer ordinary package calls and modest styling; retain settings solving actual layout problems. Inspect the relevant rendered outputs for clipping, overlap, and legibility, and disclose any formats not inspected.

For repeatedly used R packages, a setup block usually reads better than repeated namespace prefixes; qualify one-off or ambiguous functions. In Python, favor recognizable dataframe operations and ordinary loops over clever expressions; choose vectorization when it helps. Retain execution scaffolding needed by the runtime, including a main guard for process-based parallelism where required. Parallelism must justify its setup, memory, and reproducibility costs.

## Representative simplifications

These examples assume the stated fixed inputs have already been inspected. They illustrate decisions, not universal rewrites.

### Remove scaffolding while retaining meaningful settings

This fixed file uses month/day/year dates, and blanks, `"NA"`, and `-99` denote missing results; sample dates are complete and unique within each patient. The readr and dplyr packages are loaded in the report setup.

Before:

```r
read_samples <- function(path) {
  if (!file.exists(path)) stop("Input file is missing")
  read_csv(
    path,
    col_types = cols(sample_date = col_date("%m/%d/%Y")),
    na = c("", "NA", "-99"),
    trim_ws = TRUE
  )
}
samples <- read_samples("samples.csv")
first_samples <- samples |>
  arrange(patient_id, sample_date) |>
  distinct(patient_id, .keep_all = TRUE)
```

After:

```r
# Parse the documented dates and missing-result codes.
samples <- read_csv(
  "samples.csv",
  col_types = cols(sample_date = col_date("%m/%d/%Y")),
  na = c("", "NA", "-99")
)

# The earliest sample defines each patient's observation.
first_samples <- samples |>
  arrange(patient_id, sample_date) |>
  distinct(patient_id, .keep_all = TRUE)
```

The wrapper, redundant file check, and default whitespace argument go. Date parsing, missing codes, and chronological selection stay because they define the analysis. The `na` argument replaces the parser's defaults: include the strings that actually denote missing data in this file, rather than automatically repeating every default. Actual missing dates or ties require an explicit analytical decision.

### Collapse intermediates that serve no purpose

Here, `eligible` is logical, `outcome` is 0/1 with possible missing values, and the intermediate objects have no other use.

Before:

```r
eligible_patients <- patients |> filter(eligible)
observed_patients <- eligible_patients |> filter(!is.na(outcome))
grouped_patients <- observed_patients |> group_by(treatment)
risk_by_treatment <- grouped_patients |>
  summarise(patients = n(), risk = mean(outcome))
```

After:

```r
# Estimate risk among eligible patients with observed outcomes.
risk_by_treatment <- patients |>
  filter(eligible, !is.na(outcome)) |>
  group_by(treatment) |>
  summarise(patients = n(), risk = mean(outcome))
```

Keep a named cohort instead when readers need to inspect it or later calculations reuse it.

### Replace a single-use wrapper with its familiar operation

Before:

```r
make_results_table <- function(data) {
  knitr::kable(data, digits = 2, caption = "Model estimates")
}
make_results_table(estimates)
```

After:

```r
knitr::kable(estimates, digits = 2, caption = "Model estimates")
```

The useful presentation settings remain. A helper may earn its place when substantial, stable formatting logic is genuinely shared across many tables.

## Reviewing existing code

1. Inspect the actual inputs and intended analysis. Establish a relevant baseline from execution or verified outputs: selected observations, counts, denominators, estimates, intervals, and displayed results. State if the original cannot run.
2. Classify complexity as remove, retain, or investigate. A hand-written version of a standard operation is a candidate to replace with the established package function; compare results before and after. Make targeted changes and compare after consequential edits. Preserve parsing, types, missingness, exclusions, joins, ordering, grouping, methods, random-number behavior, precision, and output meaning. Use appropriate numerical tolerances where exact equality is unsuitable.
3. Correct demonstrable implementation bugs against the stated analysis and report their effects. Surface unresolved scientific choices for a user decision; simplification does not authorize changing eligibility, missing-data policy, or statistical methods. Do not silently reinterpret an approved analysis.
4. Report plainly what was removed and how equivalence was checked, which consequential choices stayed and why, any bug fixes and result changes, and what remains unverified. Distinguish unchanged results from intentionally corrected results; matching rounded output alone does not prove equivalent calculations. Claim byte-for-byte identity only for files actually compared. Scale detail to the work; keep this change history out of the final analysis narrative.

## Final review

- Can the intended reader follow and explain the code with the provided comments and prose?
- Does the format honor the notebook default and its exceptions, with clear notebook headings, coherent chunks, and focused script roles?
- Does each abstraction, check, argument, dependency, and file serve a concrete purpose?
- Are scientific choices and denominators visible, with actual data handling preserved?
- Has the relevant code run cleanly, and have consequential changes been checked against important results?
- Can someone reproduce the deliverable from the stated inputs and setup without unnecessary sharing burden?

## Working with the other skills

This skill ships with biomedical-publication-suite and senior-investigator-audit. Figures and tables meant for a manuscript follow the publication suite's figure house style and table guidance. A full review of a research project, including whether its analyses are right, belongs to the senior investigator audit, which applies this skill whenever it rewrites code.
