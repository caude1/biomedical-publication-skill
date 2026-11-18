# Changelog

## 1.5.0 (2026-11-18)

New guidance on writing for a reader who has never seen the project, drawn from two long rounds of revising real manuscripts and stated as general principles for any paper. A new guide, `references/reader-friction.md`, sets the standard that a reader should never have to stop and ask what a phrase means, why the authors made a choice, or what a term refers to. It covers giving every number, threshold, period, or comparison that could look arbitrary its reason, spending space on what makes a result believable instead of on doubts the team resolved during the analysis, and the sentence and paragraph habits that cause friction, with a section on methods-heavy papers for clinical readers.

- **Sections.** The abstract ends on its take-home message and carries a limitation only when the conclusion would otherwise mislead. The Introduction states a hypothesis whose answer is not obvious and does not make the paper look redundant. The Discussion opens by orienting a reader who skipped to it, develops implications for the people who can act on them, works strengths into its points, and closes by tying the argument together before a lean, honest Limitations subsection.
- **Analyses in the paper.** Robustness and sensitivity analyses that only confirm a result go to the supplement or stay in reserve, while analyses a protocol, analysis plan or reporting guideline names are always reported, at least in the supplement; one that weakens a claim changes the claim. Analyses are labeled by role, prespecified and exploratory analyses are distinguished as ICMJE recommends, and nothing is called prespecified without a dated protocol. A bias known to act toward the null is explained where the result is interpreted, as a reason it cannot explain the association, never as support for a null result. Friction edits remove argument, never procedure.
- **Register and conventions.** Connectives that name a relation are welcome and varied; announce-then-enumerate sentences, taglines, coined metaphors, and one construction on repeat are flagged. The serial comma, no contractions or possessive apostrophes, paraphrase in place of quotation, effects on a scale readers can weigh, a label for every P value, and short parallel names for derived groups are now defaults.
- **Figures and tables.** One job per figure, counts that cannot be mistaken for percentages, counts and P values in forest plots by default, hierarchy through fill and weight, accurate labels and keys, decision trees that show what each branch means for the patient, a standardized-difference display for group similarity, and a table layout for reading.
- **Working with authors.** Proposed edits shown in context, a list of every change and unimplemented recommendation after a substantial revision, plain explanations of analytic results, a review-copy layout, warmer coauthor replies, and AI disclosures that are brief and describe what actually happened.
- **Examples and evaluations.** Seven new worked examples on the synthetic referral and staffing data, a first-time clinical reader for cold reads, and five behavioral evaluations.

## 1.4.0 (2026-11-17)

The skill now tells you when a newer version is published. About once a week, the first time it is used in a session, it reads the public version number, compares it with your copy, and if yours is older, shows the update command for Claude Code, Codex or a zip install and offers to run it. It never updates itself, sends nothing about you or your work, and keeps its note of the last check outside the skill folder. Set `BPS_UPDATE_CHECK=off` to turn it off.

## 1.3.4 (2026-11-17)

Updates now reach people who installed the plugin: each release is published automatically with a new version number, and the README explains how to receive updates in Claude Code and Codex. No change to the skill's guidance.

## 1.3.3 (2026-11-17)

One-line installs from GitHub for both Claude Code and Codex, tested in each, and the right handle for calling the skill after a plugin or folder install. No change to the skill's guidance.

## 1.3.2 (2026-11-17)

Released under the MIT License. The license text is at the repository root and in the skill folder.

## 1.3.1 (2026-11-17)

Install instructions point to the public repository, `caude1/biomedical-publication-skill`, and the manifests name the GitHub account as the author.

## 1.3.0 (2026-11-17)

- **Cold reads.** The multi-round workflow now runs by default on near-final manuscripts and figures. It says how to start readers that are actually cold (fresh subagents in a folder that holds only the reader's copy, launched together), adds a two-minute reader, a register reader and a newcomer reader, tells the coordinator how to weigh suggestions that would only add length or hedging, and ends with a short report of what changed and what was declined.
- **Figure house style.** Rewritten as the default look for new figures and stated plainly as guidance to apply by judgment. It now gives the purpose of the style, a fuller palette and type specification, number formats, and conventions for forest tables, trajectories, bars, heat maps, maps and flow diagrams. The journal's instructions and a manuscript's existing figure set take precedence. The worked figure moved into the skill's `assets/` folder so it travels with a standalone install. It was revised after two rounds of cold reads by fresh readers: a triangle end marker that read as an arrow became a circle, the forest axis gained direction labels, panel A now carries one inferential statement, and the legend left the image.
- **Main instructions.** Kept the shorter 1.2 structure and restored the points it had dropped: the three ways scientific prose misses a plain formal register, numbers in place of adjectives, a lean limitations section, no project vocabulary in deliverables, and the author's own edits as the statement of their preferences.
- **Supplements.** Restored the short, selective default while keeping the 1.2 additions on contrary evidence, access promises and venue files.
- **Worked examples.** Added three pairs on register, limitations and the conclusion, using the same synthetic referral data.
- **Conventions.** Restored the explicit P-value convention.
- **Tested by use.** A fresh agent given only the skill drew a subgroup forest plot and ran two rounds of cold reads on it unprompted. Its figure is included as a second worked example, and the gaps it reported in the guide (line-width units, axis titles, rounding, interaction tests, where the legend goes) are fixed.
- All illustrative sentences now use the synthetic referral and staffing examples. Three behavioral evaluations were added.

## 1.2.3 (2026-11-17)

Panel A labels each booking curve with its starting cohort size. The figure guide explains when starting counts suffice, when to show numbers at risk, and when visit counts describe participants assessed.

## 1.2.2 (2026-11-17)

Redesigned the synthetic worked figure with boxed panel letters, bold titles, and a table and forest plot comparing attendance among all referrals and among patients who booked. The curve annotations and shared figure legend use a print-journal layout. The R example derives the day-14 booking difference and confidence interval and the full-curve log-rank test from the same synthetic records. It exports a 300-dpi PNG and an embedded-font vector PDF.

## 1.2.1 (2026-11-17)

The package validator now accepts version-named installation directories while still detecting a mismatched plugin identity. A regression test exercises both cases in a copy of the installed package.

## 1.2.0 (2026-11-17)

- Condensed the main skill instructions and added a two-round cold-reading workflow for near-final manuscripts, figures, supplements, and responses. The coordinator checks independent interpretations against the evidence and sends revisions to fresh readers.
- Added optional figure house-style guidance, including print-scale typography, accessible series encodings, aligned forest tables, visit counts, and a runnable ggplot2 theme.
- Replaced the worked examples with synthetic, source-grounded examples covering referral denominators, nested odds ratios, temporal interpretation, qualified clinical implications, and reviewer responses. A journal maximum is now a ceiling rather than a drafting target.
- Added a procedure for reconciling author-edited Word drafts with a changing build source and preserving citation fields, comments, and computed values.
- Expanded reporting guidance for study-specific questions, clinical estimates, reviews and related reports. Added dated official sources.
- Corrected metadata replay and identity matching, missing ledger and record checks, confidence-bound handling, and detection of swapped values in labeled Markdown tables. Existing draft ledgers remain usable. The optional results-state column preserves the meaning of unreported or suppressed values.

## 1.1.0 (2026-11-17)

The skill now reviews prose by reading and reserves helpers for facts a machine can settle.

- `SKILL.md`: a default seven-step sequence; a stated target register (plain and formal, neither performed, loose nor convoluted); rules that every comparison names its comparator and every percentage its denominator; lean limitations and restraint in pre-answering objections; a section on working with the author; routes for supplement pruning, word-limit cuts and conventions; a sharper description.
- New `references/prose-register.md`: a by-hand register review organized by manuscript section, with the forms that are earned in scientific prose, rules that protect the science during a register edit, and a newcomer read after a reanalysis.
- New `references/biomedical-conventions.md`: how to word an effect, number and unit presentation, nomenclature, and language about people.
- New `references/worked-examples.md`: eleven synthetic before-and-after pairs.
- `publication-surface-standard.md`: figure design, tables and supplement economy.
- `manuscript-length.md`: cut to a limit by reorganizing before trimming.
- `section-and-artifact-guides.md`: conclusion, Discussion space, abstract methods and title precedent.
- `revision-response-and-submission.md`: cover letters, coauthor correspondence, and treating simulated review as input.
- `literature-intelligence.md`: official or primary sources for facts that are not research findings.
- `publication_qc.py`: discourse markers ("Notably", "Importantly", "Moreover") are no longer flagged.
- Packaging: a Claude Code plugin manifest, a portability check in the validator, seven new behavioral evaluations, and a test workflow.

## 1.0.0 (2026-09-05)

Redesign around scientific reasoning and editorial judgment: publication-reader perspective, narrative framing, length planning, evidence and claim control, review methods, statistical reporting, optional audit helpers, and behavioral evaluations.

## 0.1.0 (2026-06)

Initial release.
