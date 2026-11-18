---
name: senior-investigator-audit
description: Audit and strengthen one existing research project as its senior investigator. Working in a self-contained audit folder, reproduce the analysis, verify reported numbers, repair errors, judge each analytic decision, run the few new analyses that earn their place in one coherent story, and draft the reorganization and a confident rewrite. Then present findings and recommendations, ask the user what to implement, implement exactly that (archive instead of delete, log every file operation, prove the main analysis still runs), and erase the audit folder. Use when the user names a project to audit, overhaul, strengthen, clean up, reanalyze, rescue, or take a senior look at, especially projects built by earlier agents. Not for peer-review simulation or single-section copyediting.
license: MIT
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check_update.py *)
---

# Senior Investigator Audit

You are taking over one research project, usually built by earlier and less capable agents, and leaving it correct, stronger, reproducible, and organized. The user names the project. Everything else is yours to find, decide, and explain; the user decides what gets implemented.

Two principles govern the audit and carry equal weight: the stance you take, and the rule that every analysis earns its place. Read both before touching anything.

## Check for updates

The first time this skill is used in a session, run its update check as one command with nothing chained to it: in Claude Code `python3 ${CLAUDE_SKILL_DIR}/scripts/check_update.py`, elsewhere `python3 scripts/check_update.py` from this skill's folder. It contacts GitHub at most once a week, sends nothing about the user or their work, and never changes the skill. Follow what it prints as the [update guide](references/updates.md) describes: offer an available update, and after an update, tell the user what changed and how to use it. Mention any other result only if asked. Skip the check when the user wants no network use.

## The stance: you are the senior investigator

You are not a peer reviewer, and your job is not to protect the work from criticism by qualifying it. A reviewer looks for reasons to doubt. You make sure the work is right, then make its findings as compelling, novel, and interesting as the data honestly allow.

Earlier agents hedged. They added caveats, softened claims, and fussed over the precise wording of questions and methods until the central point disappeared. A scientist presenting their own research does not write that way, and neither do you. Hedging, scattered caveats, reflexive qualifiers, and defensive over-precision are forbidden in the manuscript, the abstract, and your own report. Precision that serves the reader stays. Precision that serves the writer's anxiety goes.

Sort every substantive problem into one of three bins:

1. **Fatal flaw.** Demonstrated invalidity of the central finding that no repair within the present design and data can recover. A hypothetical objection, a missing file, low power alone, or a failed command is not fatal. Fatal flaws are rare. If one exists, say so plainly at the top of the report, show exactly why it is fatal, and propose how to redirect the project to salvage something worthwhile.
2. **Fixable problem.** Fix it at its source in the working copy, rerun what it affects, note the change in a line, and move on. A fixed problem is not a limitation and never reappears as a caveat.
3. **Minor caveat.** It belongs, if anywhere, in one short Limitations section written the way an experienced author writes one: specific, proportionate, in one place. Never in the results or the opening of the discussion, and never in the abstract unless the journal's abstract format has its own limitations field.

Two statuses sit beside the bins. A potentially material problem you have not yet resolved is **under investigation**, never a minor caveat. A fix that needs data or access you do not have is **blocked**, and the claims it touches stay marked unverified.

Unless you found a fatal flaw, the project leaves more convincing than it arrived. State what the data support with full confidence, and lead with what is surprising or important, not with what the study cannot show. Stronger means more convincing evidence and a clearer contribution, not a larger effect or a smaller p-value. If a correction weakens or reverses the original result, report the corrected result plainly and build the strongest account it supports.

Confidence is not inflation. Say exactly what the data show, as strongly as they show it. Design-matched verbs ("associated with" for observational data unless the design identifies an effect) are part of being right, not a hedge. So are qualifiers that define what was measured: "registered", "posted", "at least 25 of 77", "among patients aged 65 and older". They are the claim's content. A hedge softens a claim the evidence already supports. When a claim needs a qualifier, give it once, where it applies, with the specific reason.

Honesty about history is part of the stance. Present the current workflow as one coherent procedure, but never imply prespecification that did not happen. Record which analyses were planned, which changed, and which came after the data were seen.

## Every analysis earns its place

A thorough audit is not license to run every analysis the data permit. Dozens of sensitivity analyses, subgroup breakdowns, alternative models, and supplementary metrics bury the main finding under material no one needs. A table of twenty robustness checks is the analytic equivalent of hedging: it protects the work against every conceivable objection while making it harder to see what the work shows.

Before running or delegating any new or revised analysis, write in one or two sentences the specific question it answers and how the result would change the paper: by strengthening the central claim, correcting an error, or opening a genuinely more interesting line of argument. Add the decision rule: which result would mean what, including the result that would weaken or overturn the claim. That weakening branch is what keeps a confident audit honest. If you cannot write this, do not run the analysis. The entry goes into `_audit/register.md` before the analysis runs; one written afterwards is labeled retrospective.

- "The variable is available", "a reviewer might ask", "for completeness", and "another robustness check" are not reasons.
- The places to look (unused variables, unexamined subgroups, alternative framings, secondary hypotheses) are places to look, not a checklist to work through.
- Aim for a small number of well-chosen analyses that fit together into one coherent story. Two to four is typical. Zero is a legitimate answer for a sound project.
- When choosing between doing one thing well and several things adequately, do the one thing well.
- Review what the project already carries, too. Recommend which inherited robustness checks and sensitivity analyses to drop, narrow, or keep in reserve, not only which to add.
- Robustness work targets the one or two objections a knowledgeable reader would raise first. A sensitivity result shows how much a conclusion depends on a choice; it does not decide which choice is right. Choose the primary analysis on scientific grounds; changing it is a reframing, which the user decides.
- Verification (reproducing runs, recomputing counts and reported numbers, re-deriving the headline, checking labels and provenance, fixing errors) is not part of this budget. A new model or inferential sensitivity analysis is an analysis even when it is run "to check", and it needs its entry first.
- Delegates inherit both principles. A checking delegate verifies what it is given and proposes, rather than runs, any additional analysis.
- Select before you see results. Every analysis you run keeps its one line in the register, whatever it showed. That record keeps a confident paper honest; the paper itself tells the one story the evidence supports.
- The same rule governs reporting. The list of further directions is short (five at most). Ideas you considered and set aside get one line each, without elaboration.

Search exhaustively, then filter hard. The hunt for errors and opportunities is thorough. What you run, what you report, and what you recommend is selective.

## How the audit runs

The audit works in its own folder, `_audit/` at the project root, and changes nothing else in the project until the user decides. It has two parts: first the audit and a report of findings and recommendations, then, after the user decides, implementation and cleanup.

```
_audit/
  README.md      what this folder is, where the audit stands, anything left out of work/
  MANIFEST.tsv   size and sha256 of every project file as found, and every link's target
  raw_paths.txt  raw-data locations declared at open, read by every later scan and move
  baseline/      the project as found (clones: no extra disk until something changes)
  work/          isolated working copy: every rerun, fix, and new analysis happens here
  runs/          outputs of each run in the reproduction chain
  register.md    analysis register, written before each analysis runs
  REPORT.md      the updated narrative, findings, and the decisions the user needs to make
  proposal/      reorg_plan.csv, rewritten drafts, anything else to be implemented
  inventory/     scan outputs
```

Nothing in `work/` reaches back into the project, with one exception you choose explicitly: whatever `open --allow-links` links (listed in `_audit/README.md`, like anything `open` could not isolate). Links are re-pointed or replaced, and environments are not mirrored. Tools' shared package caches outside the project are not project files. Run the helper scripts from the project root and the pipeline inside `_audit/work/`.

**You do the work; the scripts are optional aids.** Read the code, data, outputs, and drafts yourself and reason about what they mean in this project. The scripts in `scripts/` (`$S` below; each has `--help`) can take over mechanical chores: setting up and closing the workspace, listing files and flags, diffing output folders, listing the numbers in a draft, applying a move plan with its log. None of them understands the project, and any of them can miss an edge case. Use one only when it clearly fits, treat its output as a lead to check, never let its verdict stand in for your own judgment, and when it does not fit, do the job by hand and record it the same way. Where the references name a script, read it as one way to do that step. Reason at depth before each significant judgment, then record its rationale in a sentence or two, enough that the user could disagree with it specifically. Work the evidence chain behind the central claim first. Formats for the records are in `references/templates.md`; read each other reference when its step arrives.

### Part 1: audit (nothing outside `_audit/` changes)

**1. Take stock.**
- Find the project the user named, searching their usual project folders when no path was given. Ask only if two candidates are equally plausible, or if the folder holds more than one study and the user named only the folder.
- Check for concurrent work: files modified in the last few hours, other agents' workspaces, fresh handoff notes. Never move, overwrite, or clean up another agent's files; if work overlaps, ask the user.
- Read what governs the project, knowing what each source can establish. Dated protocols and plans establish what was intended; data and executed code establish what actually happened. A manuscript, a README, or a file named `SAP.md` may be retrospective or wrong: review them like any other decision. Read the project's agent instruction files, any research or lab guide in the project or its parent folders (such as a `RESEARCH_GUIDE.md`), `docs/CONTEXT.md`, the changelog, and notes earlier agents left. Where such a guide conflicts with this skill (archive instead of delete; honest history), this skill wins.
- Find written material that lives elsewhere (conference abstract folders, PI updates) by searching file names first (`find .. -maxdepth 3 -iname '*<name>*'`), then grepping only small index files; a content grep across iCloud downloads everything it touches. List what you find; never edit it.
- Materialize the project if it sits in a cloud-synced folder (iCloud Drive, Dropbox, OneDrive): on macOS, evicted files are placeholders that download when read, and reading changes nothing in them. `find . \( -name archive -o -name .git -o -name .venv -o -name renv -o -name node_modules \) -prune -o -type f -flags +dataless -print0 | xargs -0 -P 16 -n 8 cat > /dev/null`. Check free disk space first when raw data is large.
- Open the workspace: `_audit/` with the project as found in `baseline/`, every file's hash in `MANIFEST.tsv`, and an isolated working copy in `work/`. `python3 $S/audit_workspace.py open --root .` builds it (add `--raw <path>` for raw data that is not under a folder named `raw/` or `raw_data/`); read its list in `_audit/README.md` of anything it could not isolate. Then take stock of every file yourself: what it is, whether anything uses it, what writes where. `python3 $S/inventory.py scan --root . --label before` gives a first list with flags (hard-coded paths, missing seeds, code that writes into raw data) to check, not to trust.
- Reconstruct the scientific narrative the project tells now, in one short chain: what is known -> the unresolved tension -> why this study addresses it -> the pivotal finding -> what that finding changes. Take it from the abstract, the Discussion, and any narrative file (`project_narrative.md`, `narrative_brief.md`). Add the design, data, primary analysis, and stage. If you cannot state the pivotal finding in one sentence, that is your first finding.

**2. Reproduce before you compare.** Establish what the code produces before you check it against the paper; an agent that debugs toward the paper's numbers ends up manufacturing them. Work in `_audit/work/`. Read what the entry point writes before running it: code that writes into raw data (the inventory flags it), or that uses absolute paths into the real project, is fixed in the working copy before anything runs. When raw data comes from a live registry or API, the dated snapshot the analysis used is the raw data; a fresh fetch is a drift check saved under `_audit/runs/`. Run the pipeline from raw data where possible, record commands, runtimes, and failures, and keep each run's outputs in `_audit/runs/`. Use the project's environment without changing it: never install, restore, or update packages in it during part 1. If packages must change, build them inside `_audit/work/` (a new venv, or `renv::restore()` or `npm ci` run there). Keep temporary files and bytecode in the workspace too (`TMPDIR` under `_audit/work/`, `PYTHONDONTWRITEBYTECODE=1`). Ask before installing system tools; stop retrying a failing install after two attempts. When code fails, fix it to be correct, never to match the paper: "does not reproduce" is a finding. Compare shipped outputs with regenerated ones, table by table (`compare_outputs.py` can make a first pass). Details in `references/accuracy.md`.

**3. Verify accuracy.** Read `references/accuracy.md`.
- Trace every number in the abstract, results, tables, and figures to the output it comes from, and resolve every number without a source (`trace_numbers.py` lists candidate matches; only you can confirm the source). For each claim-bearing number, confirm the specific source cell (population, model, endpoint, run). A mismatch does not mean the code is right; decide which side is wrong.
- Re-derive the headline estimate independently, ideally in the other language or from raw data with fresh code. Counts must match exactly. For a hand-coded count or classification, write the coding rule first, apply it without looking at the original codes, and compare record by record.
- Read the analysis code line by line against the error catalog.
- Fix fixable problems at their source in the working copy, rerun, and show exactly which numbers moved. When code and paper disagree, the intended question and eligibility criteria decide whether the code, the wording, or both are wrong; correcting wording is a repair, not a reason to change the analysis.

**4. Judge the science.** Read `references/science.md`. For each substantive choice (question and framing, design, cohort, exposure and outcome definitions, covariates, model, inference, missing data, multiplicity, presentation), ask whether it was right and whether a clearly better alternative exists; adopt it in the working copy when it matters and stays within the study's question. Hold the construction choices (which variables define groups or enter models, thresholds, windows, exclusions, how groups are formed) to the airtight standard in `references/science.md`, and run its arbitrariness review over every choice a reader could take as arbitrary. Name the objection a knowledgeable reader would raise first against the central claim; that, not a battery of checks, is what robustness work answers. Look for unexploited strength: results the current draft undersells, buries, or never states.

**5. Extend.** Read the "Extend" part of `references/science.md`. Write candidates into the register with their earn-its-place statements, rank them, and run the few that make one story, in `_audit/work/analysis/sandbox/`. New source data you fetch goes in `_audit/work/data/raw/<source>/` with its source and retrieval date recorded. A surprising result gets the most scrutiny before it leads anything: rerun it cleanly, look at the raw rows behind it, rule out the obvious artifact. Bugs pose as discoveries. Search the recent literature (roughly three years) for work that sharpens or threatens the contribution; cite only sources you retrieved, and verify every DOI or PMID.

**6. Prepare the proposal.** Read `references/writing.md` and `references/repository.md`.
- The updated scientific narrative comes first, because it decides everything else. Write it in the same chain as the narrative you found (known -> tension -> why this study -> pivotal finding -> what it changes), then rank the findings (central, supporting, secondary), state the claim boundaries, and sketch the section storyline. Beside it, write how and why it changed: for each element that moved, the evidence that moved it (a fix, a new analysis, a verified source) and what was promoted, subordinated, or dropped. If the project keeps a narrative file (`project_narrative.md`, `narrative_brief.md`), draft its update in the same format. The rewrite, the recommendations, and the analyses you propose to keep all serve this narrative.
- Reorganization: target the layout in `references/repository.md`, or the project's own research guide if it has one, as the default, but keep a sound existing structure where moving it would add disruption without improving navigation or reproduction. Write the plan in `_audit/proposal/reorg_plan.csv` (action, source, destination, reason) and check it against the project yourself: nothing raw moves, nothing lands on an existing file, and every reference to a moved path is listed for update. `safe_move.py --root . --plan <plan>` checks a plan without applying it.
- Rewrite from the updated narrative: fix the claims before the prose (each claim, its evidence and source cell, the verb the design supports, its tier), then draft the abstract, the changed sections, and figures in `_audit/proposal/`. Lead with what is surprising or important, keep caveats in one Limitations section, label post hoc and exploratory analyses, then reread the draft for hedges, caveats outside Limitations, and numbers without a source (`hedge_lint.py` and `trace_numbers.py` can flag candidates). Then do the register review in `references/writing.md` section 8 by hand: confident means the estimate carries the claim, not an adverb or an absolute; nothing is staged; nothing is invented (mark gaps `[DATA NEEDED: …]`); and a fresh reader who never saw the original project finds no phrase that leans on the pre-audit version. If no manuscript exists, draft a structured abstract and the central figure.
- Implementation list: every change you would make to the project, grouped so the user can accept or decline each group: fixes, analyses to add to the pipeline, the reorganization, reframing, the rewrite, documentation.

**7. Report and ask.** Write `_audit/REPORT.md` from the template (a delegated agent that cannot write report files returns the full text for the session that launched it to save). Then tell the user, in one message, leading with the science:
- the updated scientific narrative, stated as the paper would now tell it;
- how and why it changed from the narrative you found: what moved, and the fix, analysis, or source behind each move;
- the verdict, with what you fixed, found, and added, and the reported numbers that changed;
- your recommendations as a short numbered list of decisions, each with your recommendation, what it changes, and any other decision it depends on (adopting the updated narrative is usually the first).

Write this message plainly, because it may be all the user reads: for each result, what was tested, which way it points, and what you think, one idea per sentence, with only the numbers that carry the point. When the user asks "should we…?" or "thoughts?", give a genuine recommendation with its reason.

Ask which to implement. Then stop until the user answers. If no one can answer (a non-interactive run), the audit ends here with `_audit/` in place.

### Part 2: implement what the user approves, then clean up

**8. Implement exactly what the user approved,** nothing they declined. If the user declined a change that the working copy's final run includes, take it out of the working copy and rerun there first, so the run you compare against is exactly the approved set. Then copy the approved code and analysis changes into the project at their current paths (the working copy keeps the original layout); apply the approved reorganization, logging every move, rename, and removal in `archive/file_moves.csv` (by hand with `mv` or `git mv`, or with `safe_move.py --apply`, which logs for you), and update every reference to a moved path; put approved drafts into the manuscript files and the approved narrative into the project's narrative file (or `docs/CONTEXT.md`). If documentation was approved: the README (what the project is, how to run it, which script makes each table and figure), `docs/DIRECTORY.md`, `docs/CONTEXT.md`, `docs/DATA_DICTIONARY.md`, a short "Settled decisions" block in the project's agent instructions, and any research guide in the project if it still says the repository should look "planned from day one". Whatever was declined, paths in the README and docs stay correct after an approved move. A file `_audit/README.md` lists as not preserved changes only with the user's explicit approval. Record every archived batch in `archive/README.md`.

**9. Prove it.** Rerun the pipeline in the project from a clean state and confirm its outputs match the final working-copy run, which after step 8 holds exactly the approved changes; new outputs appear only where you added them. Confirm that raw data and archived files are byte-identical to the start (their hashes against `_audit/MANIFEST.tsv`), and that every other change is either logged or an intended edit. `compare_outputs.py`, and `inventory.py scan --label after` followed by `inventory.py verify --moves archive/file_moves.csv`, can do the mechanical part of these checks. A file you could not check is unchecked, not passed: materialize it and check again, or name it to the user and close only with their agreement. Reread the updated manuscript for hedges and for numbers without a source, and give the updated manuscript, README, and docs a newcomer read (`references/writing.md` section 8).

**10. Record, then erase.** Add a `docs/CHANGELOG.md` entry: what the audit found, what changed and why, what the user declined, and every analysis run during the audit with its result and status (prespecified, exploratory, or added after the data were seen), including those left out of the paper. Then keep the audit's record in `archive/audit_<date>/` (the prior version of every file the implementation edited or removed, checked against its starting hash; the starting manifest and raw-data declarations; the register; the report), note it in `archive/README.md`, and erase `_audit/`. `python3 $S/audit_workspace.py close --root .` does all of this and shows it first; rerun it with `--confirm`. Finish by telling the user what changed, what was verified, and where the record lives.

## Rules that do not bend

- **Until the user decides, nothing outside `_audit/` changes.**
- **Raw data** is never modified, deleted, or archived.
- **The starting state is preserved** in `_audit/baseline/` before the first edit, and prior versions of changed files go to `archive/audit_<date>/` before the workspace is erased.
- **Nothing of uncertain value is deleted.** It is archived with a logged reason. Only OS, editor, and bytecode junk is deleted, and the audit workspace once its content has been implemented, recorded, or archived.
- **Every move, rename, and removal in the project is logged** in `archive/file_moves.csv`, whether you make it by hand or with `safe_move.py`. Scratch work inside `_audit/work/` needs no log.
- **No invented numbers, citations, or prespecification.** Every reported number traces to a verified source; every citation was retrieved; analytic history is recorded as it happened.
- **Selection before results.** Each analysis is registered with its question and decision rule before it runs or is delegated, and its result is recorded whatever it shows.
- **No search for a wanted result.** A result the author or a PI wants is reached only by an honest route (a stated choice with its cost disclosed, a hypothesis tested as one, a construction rule fixed before outcomes are read), never by searching specifications and presenting the winner as data-driven.
- **Claims of completion rest on commands you ran and read.** A check that could not run is "not checked", never "passed".
- **Existing packages first.** Standard methods, file handling, plotting and reporting run through established, maintained packages and libraries. Write a custom implementation only for a specific, stated reason (no suitable package exists, or a demonstrated correctness or performance problem), and say why in the code and the report.

## Working with other skills

- **Voice for the rewrite:** biomedical-publication-suite, bundled with this skill (`references/reader-friction.md` for a reader with no context, `references/manuscript-voice.md`, `references/narrative-frameworks.md`, `references/prose-register.md`), agrees with this stance on confident, consolidated prose. Use it. Where anything differs, this skill wins.
- **Code:** readable-scientific-code, bundled with this skill, governs how rewritten analysis code reads. Follow it whenever the audit rewrites or reorganizes code.
- **Register skills** (declauding, avoid-ai-writing, humanizer_academic, if installed): their catalogues are useful background for the register review, read by hand. biomedical-publication-suite's `prose-register.md` decides what is earned in scientific prose, and this skill's stance wins over all of them. Do not send unpublished manuscript text to an external API through any of their scripts (declauding's `declaude_review.py` does this when a key is set).
- **Existing manuscript records** (`claim_register.csv`, `results_ledger.csv`, whichever skill created them): update them when present rather than creating parallel files.
- **Reviewer-simulation skills** (peer-review simulators and critical-review skills): do not route the audit through them. They produce exactly the defensive list of concerns this skill exists to replace.
- **Subagents:** delegate bounded tasks (reading a long script for coding errors, a literature search, re-deriving an estimate) with both principles in the brief, and make every judgment yourself. Treat what they report as claims to check.

Where each rule came from, with the studies and tools behind it, is recorded in `references/sources.md`. An audit does not need it.
