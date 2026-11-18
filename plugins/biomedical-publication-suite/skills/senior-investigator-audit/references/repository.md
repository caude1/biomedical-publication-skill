# Reorganizing the repository

Read this before step 6 (the reorganization proposal) and again before step 8 (implementation). The test for success is from Noble (2009): someone new to the project can look at the folder and understand what was done and why, then run one command and regenerate the main results.

## Contents

1. Target structure
2. Classifying every file
3. Common messes and where they go
4. Writing the move plan
5. Applying it in batches
6. The entry point and environment
7. Documentation
8. Proving nothing broke
9. iCloud and git

## 1. Target structure

Use the layout in the project's own research guide if it has one. Otherwise, this is the default:

```
data/raw/            immutable inputs, byte-identical to what was obtained
data/processed/      analysis-ready data built by code
data/cached/         expensive intermediates, safe to rebuild
analysis/pipeline.*  the single entry point
analysis/scripts/    production code
analysis/sandbox/    exploratory work (outputs to results/temp/)
results/tables/      publication tables, written by code
results/figures/     publication figures, written by code
results/temp/        sandbox outputs only
docs/                CONTEXT, DIRECTORY, CHANGELOG, DATA_DICTIONARY
manuscript/          the canonical manuscript source and its displays
archive/             everything of uncertain or historical value
```

The layout is a default, not a mandate. Keep a sound existing structure where moving it would add disruption without improving navigation or reproduction; consistency is the destination, not a reason for moves. A multi-cohort project can keep `analysis/cohorts/<name>/` if the pipeline iterates over cohorts. The principles do not bend: raw data immutable, outputs written only by code, one entry point, history only in `archive/`, and names that describe content, never history (no `v2`, `final`, `old`, `updated`, `rescue`, `gate`, `prepolish`, or dates). These rules govern active content: a dated raw-data snapshot folder keeps its retrieval date (provenance), and `archive/` keeps its dated batches.

## 2. Classifying every file

Work from `_audit/inventory/manifest_before.csv` and `inventory_before.md`. Every file gets exactly one decision:

- **Keep:** used by the pipeline or the manuscript, current, and correctly placed and named.
- **Move or rename:** current but misplaced or named by history.
- **Archive:** superseded, orphaned, duplicated, stale, agent scratch work, old manuscript or submission versions, outputs no current code produces, and anything whose value you cannot establish.
- **Delete:** only OS, editor, and bytecode junk: `.DS_Store`, `~$` lock files, `*.pyc`, and a `__pycache__` folder that holds nothing but bytecode. Archive everything else, including tool caches (`.pytest_cache`, `.mypy_cache`) and notebook checkpoint folders, which can hold the only copy of someone's work.
- **Raw data** found in the wrong place moves into `data/raw/` with its content untouched. It is never archived.

**Only current material in the working tree.** The point of the reorganization is that a later reader or agent opening the project sees the current analysis and nothing else: no superseded scripts beside live ones, no sandbox of abandoned ideas, no history pointers, dated comments or "do not reintroduce" lists in code or agent instructions. Earlier attempts left lying around steer the next reviewer toward or away from old ideas. Removed material stays recoverable and logged: in `archive/` by default, or, where the project's own instructions keep it out of the project entirely (for example in the Trash, with a manifest beside it), wherever those instructions say.

**Is it live?** Check before archiving anything that looks unused. A file is live if any of these names it:

- `source()`, `import`, or `%run`;
- a Makefile, `_targets.R`, or a Snakefile;
- a Quarto or R Markdown chunk, or a notebook;
- the README or the manuscript;
- a path assembled at runtime (`paste0`, `glue`, `file.path`, a glob or `list.files` pattern).

The inventory catches most of these, but not paths built at runtime. Search for the file's stem before archiving. A search you did not run proves nothing.

## 3. Common messes and where they go

| Found | Decision |
|---|---|
| Parallel output trees (`outputs/` and `results/`) | Current outputs into `results/tables` and `results/figures`; the rest to `archive/` |
| Submission or packaging folders (`FINAL_FILES_TO_SEND`, `submission_package`, `manuscript_package`) | The current submitted version into `manuscript/` (or `manuscript/submission/`); older packages to `archive/manuscript_history/` |
| Agent workspaces (`_CC`, `_GPT`, `_llm_rounds`, `manuscript-council`) | `archive/agent_workspaces/` |
| Scripts and notebooks at the root | Production code into `analysis/scripts/`; exploration into `analysis/sandbox/` or `archive/` |
| Knitted HTML and `*_files/` folders | Regenerate from source; archive the old copies |
| Handoff, progress, and final-report notes | Fold what is still true into `docs/CONTEXT.md` and the changelog, then archive |
| Several manuscript versions | One canonical source in `manuscript/`; the rest to `archive/manuscript_history/` |
| Data files at the root or in odd places | Raw into `data/raw/`; derived into `data/processed/` if current code builds it, otherwise archive |
| Environments (`.venv`, `renv/library`) | Leave in place; add them to `.gitignore` in a repository |
| An existing `archive/` or `__old/` | Leave its contents where they are; consolidate `__old/`-style folders under `archive/` |

## 4. Writing the move plan

`_audit/proposal/reorg_plan.csv`, columns `action,src,dst,reason`. In part 1 you only dry-run it against the project; it is applied in part 2, after the user approves it. Actions: `mkdir`, `move`, `rename`, `archive`, `delete_junk`. Lines starting with `#` are comments; use them to group rows by purpose.

```
action,src,dst,reason
# archive superseded analysis code
archive,analysis_v2.R,,superseded by analysis/pipeline.R, which reproduces its outputs
archive,_GPT,archive/agent_workspaces/_GPT,earlier agent scratch; nothing depends on it
# outputs into the standard tree
move,outputs/fig1.png,results/figures/,one output tree
rename,results/table1_final_v3.csv,results/tables/baseline_characteristics.csv,content name
delete_junk,.DS_Store,,macOS junk
```

Order the plan so that folders are created before files move into them, whole folders move before their contents are renamed, and anything occupying a name is archived before something else takes that name. `archive` without a `dst` keeps the original relative path under `archive/`. For `move`, `rename`, and `archive`, a `dst` that ends in `/` or names an existing folder means "into this folder". The dry run checks every row, previews the lines of code that mention moved paths, and warns about scripts that locate files relative to their own position (`Path(__file__).parents[1]`, `here::i_am`), which break when moved to a different depth. The tool refuses any move whose source or destination resolves outside the project root (a symlinked folder, for instance), and treats a folder that contains raw data as raw data. If a step fails during `--apply`, it stops, reports INCOMPLETE, and exits non-zero; the log shows exactly which steps ran.

## 5. Applying it in batches

1. Check the whole plan before applying anything, row by row. `python3 $S/safe_move.py --root . --plan _audit/proposal/reorg_plan.csv` gives a dry run that also previews stale references.
2. Apply one batch at a time, grouped by aspect (the archive batch, then outputs, then code): by hand (`mv`, or `git mv` for tracked files, with a log row for each file) or with `safe_move.py --apply`.
3. After each batch, fix the stale references (`grep` for the old paths): `source()` paths, `here()` calls, imports, and README links.
4. After any batch that could break the pipeline, rerun the pipeline. If a batch breaks something, fix forward or reverse it with another logged move.
5. Add an entry to `archive/README.md` for each archived batch: what it was, why it was set aside, and what replaced it.

## 6. The entry point and environment

- **One entry point** (`analysis/pipeline.R`, `.py`, `.qmd`, or a Makefile) runs everything from raw data to the manuscript's tables and figures in order. If none exists, write one that calls the production scripts in sequence.
- **Clean-run test.** The entry point, or a documented flag on it, clears generated outputs first (`results/tables`, `results/figures`, `data/processed`, caches), so that every output comes from current code (Gentzkow and Shapiro). During the audit, archive the old outputs rather than deleting them; see `accuracy.md`.
- **Relative paths only:** `here::here()` in R, paths relative to the project root in Python. No `setwd()`, no absolute paths, no `rm(list = ls())`.
- **Seeds are set once,** near the top, for anything random.
- **Outputs are written only by code.** No hand-edited tables, and no numbers typed into the manuscript that the code does not produce.
- **Capture the environment:** `renv::snapshot()` or a `requirements.txt` with pinned versions, plus the R or Python version in the README.
- **Keep production modest:** consolidate by analytic domain (preprocessing, models, figures, tables) rather than fragmenting into steps; review consolidation once `analysis/scripts/` passes about ten files.
- **Code that can be shared.** Identify the minimum a reader who requests the code needs to reproduce the reported results, and keep it separate from material that stays internal. The shareable part reads as public-facing code: relative paths, declared dependencies, no internal notes to agents, no personal paths. Whether it is posted or available on request is the authors' decision. A short note in the agent instructions asks future changes to keep these properties, so the separation does not need another review.

## 7. Documentation

- **`README.md`**
  - What the project is and what it found (two or three sentences).
  - How to run it (one command) and the expected runtime.
  - Software requirements.
  - Data availability and provenance: source, citation, date obtained, how to get access.
  - A table mapping every table, figure, and key in-text number to its program and output file. This follows the "list of tables and programs" in the Social Science Data Editors' template README:

    | Figure/Table | Program | Output file | Note |
    |---|---|---|---|
- **`docs/CONTEXT.md`:** question, design, cohort, endpoints, and data provenance, as they are now, not as they evolved.
- **`docs/DIRECTORY.md`:** one line per folder and per important file.
- **`docs/DATA_DICTIONARY.md`:** every variable the analysis uses, with its definition, units, and codes (missing-value codes included).
- **`docs/CHANGELOG.md`:** the audit entry (see `templates.md`), which outlives the erased workspace.
- **The project's agent instructions** (`AGENTS.md` and similar): the "Settled decisions" block (see `templates.md`).

## 8. Proving nothing broke

These are gates. The reorganization is not done until all four pass; UNVERIFIED is not a pass.

1. `inventory.py scan --label after`, then `inventory.py verify` returns PASS: every original file is present, moved as logged, or logged junk; raw data and archived files are byte-identical; and files whose content changed are listed for you to confirm as intended edits. UNVERIFIED means some raw or archived files lacked hashes on one side (usually evicted cloud files or files over the size cap); materialize and rescan; if that fails, name the unchecked files to the user and close the audit only with their agreement. The "before" manifest was taken in step 1, so this check covers the whole audit, not only the reorganization.
2. The pipeline runs end to end from a clean state through the entry point.
3. `compare_outputs.py` between the post-fix run and the post-reorganization run reports VERIFIED, following renames with `--moves archive/file_moves.csv`. PARTIAL means some files (usually figures) could not be compared: regenerate them and inspect them.
4. Nothing active depends on `archive/`. The inventory's "Active code depending on archived files" section is empty.

## 9. iCloud and git

- **iCloud.** Moving an evicted file is a metadata operation and costs nothing. Reading or hashing it forces a download. Materialize only the active folders, in parallel (`find <folder> -type f -flags +dataless -print0 | xargs -0 -P 16 -n 8 cat > /dev/null`), and check free disk space before materializing large data. `inventory.py` reads active text files in parallel and does not hash evicted files unless you pass `--hash-dataless`.
- **git.** `safe_move.py` uses `git mv` for tracked files so history follows them. Do not commit unless the user asks; leave the working tree for the user to review, and summarize the changes in the report. Large data does not belong in git.
