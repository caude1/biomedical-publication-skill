# Sources and lineage

What this skill borrowed, and from where. Agents running an audit do not need this file. It exists so a user can trace each rule to its origin and compare this skill with alternatives. Surveyed in September 2026; every source listed was retrieved and read (abstract only where marked).

## Design decisions

- The audit runs in its own folder (`_audit/`), changes nothing else until the user decides, then implements exactly what the user approves and erases the folder.
- Recommendations center on the scientific narrative: what the updated narrative is, and how and why it changed.

## Two drafts, merged

The skill merges two independent drafts, one written with Claude Code (the starting point: helper scripts, a real-project pilot, anti-hedging mechanics, blind reproduction, snapshot-versus-refetch, independent re-derivation) and one written with Codex. The second draft and its review of the first contributed:

- the "under investigation" and "blocked" statuses, and the strict fatal-flaw test;
- honest analytic history and no invented prespecification;
- preserving the complete starting state, not just outputs;
- delegates inheriting the selectivity rule, and no new models run as "verification";
- the named non-reasons for running an analysis;
- source authority by claim (dated plans versus executed code versus manuscript wording);
- approval judged by structural impact, with concrete plans (path map, rollback, verification commands);
- the lighter record set;
- a bounded list of tool defects (false matches in the comparator, file-protection gaps, optimistic success states), each now covered by a regression test in `selftest.py`.

Its methods sources: ICH E9(R1) (a sensitivity analysis targets the same estimand; a different question is a supplementary analysis); Cochrane Handbook chapter 10 (honest post hoc exploration, direct subgroup contrasts); SAMPL (reconciling denominators, estimates, and uncertainty); the ASA statement on p-values (2016); the FAIR principles (Wilkinson et al. 2016).

## Related skills

- **A research guide.** The default repository layout and naming rules began as a personal research guide kept beside a portfolio of projects. Where any such guide conflicts with the skill (archive instead of delete; honest analytic history), the skill wins.
- **biomedical-publication-suite**, bundled with this skill (`manuscript-voice.md`, `narrative-frameworks.md`, `reader-friction.md`): already aligned with the stance ("state findings confidently", "choose a story, not an inventory"); the rewrite draws on it, and where anything differs, SKILL.md wins. Its narrative chain (known, tension, why this study, pivotal finding, what it changes) and its pairing of a Scientific Narrative with an Editorial Rationale shape the report's narrative section, so that recommendations center on how the scientific narrative changes.
- **readable-scientific-code**, bundled with this skill: governs how rewritten analysis code reads.
- **Manuscript-package skills** that keep `claim_register.csv`, `results_ledger.csv`, and a `project_narrative.md` (central story, contribution framing, claim boundaries, section storyline, open narrative risks): their records are reused rather than duplicated. Such skills typically exclude rerunning analyses and integrity auditing, which is why this is a separate skill.
- **Publication text linters** cover process leakage and filler; `hedge_lint.py` covers only hedging and caveat placement, so they do not overlap.

## Agent skills and agent studies

- **MixtapeTools "Referee 2" and "Blindspot"** (Scott Cunningham, github.com/scunning1975/MixtapeTools): cross-language re-derivation of the headline estimate, with the mismatch type diagnosing the cause; a raw-data hash manifest; the "unexploited strength" pass; a settled-decisions table so later agents stop re-proposing dropped analyses.
- **Pedro Sant'Anna's research workflow template** (github.com/pedrohcgs): typed tolerances for reproduction; "a mismatch does not assume the code is correct"; archive READMEs; dry runs before bulk edits; the view that a hedge is load-bearing or absent.
- **codecleanup-skills** (github.com/bibeshpyakurel/codecleanup-skills): baseline, proof, batch, ledger; "false-alive" checks before calling a file unused; "a search that was never run is not proof".
- **obra/superpowers, verification-before-completion:** completion claims rest on a command run and read.
- **academic-research-skills** (github.com/Imbad0202/academic-research-skills): agent failure modes (a bug reframed as a surprising finding, methods drifting from the code, early frame-lock); silent upgrades in claim strength.
- **Anthropic skill-creator and model prompting guides:** a short SKILL.md with references loaded on demand; reasons instead of shouted rules; find everything first and filter in a separate pass; gates based on artifacts rather than repeated "verify" instructions.
- **SocSci-Repro-Bench** (arXiv 2606.11447): when reproduction was impossible, agents given the paper, or told to keep whatever matches it, more often reported plausible but fabricated reproductions. Hence independent computation first and no tuning toward the paper's numbers.
- **CORE-Bench** (arXiv 2409.11363), its post-saturation follow-up (arXiv 2606.26158), and **PaperBench** (arXiv 2504.01848): settle dependencies first; list the output tree before interpreting it; agents read shipped outputs instead of rerunning.
- **REPRO-Bench** (arXiv 2507.18901): search before declaring a file missing; inventory, inspect, run, compare.
- **Brodeur et al., PNAS 2026** (doi:10.1073/pnas.2524747123), human, AI-assisted, and AI-led replication teams: reproduce, then hunt for errors, then at most two robustness checks that bear on identification; heterogeneity splits are not robustness; keep conceptual decisions with the lead.
- **Kosmos** (arXiv 2511.02824): statement-level provenance; agents invent obscure metrics.
- **Confirmation and tone studies** (Asher et al. 2026; arXiv 2606.11456, 2609.27756, 2606.07951, 2504.00025): a pro-finding frame raises stated support while the estimates stay the same, harsh-critic framing makes models doubt real effects, and rewriting drifts certainty upward. Hence decision rules before running, a claim list fixed before drafting, and a verb check afterwards.

## Methods literature

**Project organization and reproducibility**

- Wilson G, Bryan J, et al. Good enough practices in scientific computing. PLoS Comput Biol 2017;13:e1005510. doi:10.1371/journal.pcbi.1005510
- Noble WS. A quick guide to organizing computational biology projects. PLoS Comput Biol 2009;5:e1000424. doi:10.1371/journal.pcbi.1000424
- Sandve GK, et al. Ten simple rules for reproducible computational research. PLoS Comput Biol 2013;9:e1003285. doi:10.1371/journal.pcbi.1003285
- Project TIER Protocol 4.0 (projecttier.org).
- Vilhuber L, et al. A template README for social science replication packages, v1.1. 2022. doi:10.5281/zenodo.7293838
- Cookiecutter Data Science v2, "Opinions" (DrivenData).
- Marwick B, Boettiger C, Mullen L. Packaging data analytical work reproducibly using R (and friends). Am Stat 2018;72:80-88. doi:10.1080/00031305.2017.1375986
- Gentzkow M, Shapiro JM. Code and Data for the Social Sciences: A Practitioner's Guide. 2014.

**Checking reported numbers and data**

- Brown NJL, Heathers JAJ. The GRIM test. Soc Psychol Personal Sci 2017;8:363-369. doi:10.1177/1948550616673876 (abstract)
- Nuijten MB, et al. The prevalence of statistical reporting errors in psychology (1985-2013). Behav Res Methods 2016;48:1205-1226. doi:10.3758/s13428-015-0664-2
- Altman DG, Bland JM. How to obtain the P value from a confidence interval. BMJ 2011;343:d2304 (formula as used in the verification step).
- STRATOS TG3, initial data analysis. Huebner M, et al. Obs Stud 2018;4:171-192. doi:10.1353/obs.2018.0014; Heinze G, et al. BMC Med Res Methodol 2024. doi:10.1186/s12874-024-02294-3
- Kapoor S, Narayanan A. Leakage and the reproducibility crisis in machine-learning-based science. Patterns 2023;4:100804. doi:10.1016/j.patter.2023.100804

**Analytic decisions and robustness**

- Morris TP, Kahan BC, White IR. Choosing sensitivity analyses for randomised trials: principles. BMC Med Res Methodol 2014;14:11. doi:10.1186/1471-2288-14-11 (the three-question test)
- ICH E9(R1) addendum on estimands and sensitivity analysis, 2019.
- Lu X, White H. Robustness checks and robustness tests in applied economics. J Econometrics 2014;178:194-206. doi:10.1016/j.jeconom.2013.08.016
- Steegen S, et al. Increasing transparency through a multiverse analysis. Perspect Psychol Sci 2016;11:702-712. doi:10.1177/1745691616658637
- Del Giudice M, Gangestad SW. A traveler's guide to the multiverse. AMPPS 2021;4. doi:10.1177/2515245920954925 (abstract)
- Gelman A, Loken E. The statistical crisis in science. Am Sci 2014;102:460.
- Maunsell J. Announcement regarding supplemental material. J Neurosci 2010;30:10599-10600.
- VanderWeele TJ, Ding P. Introducing the E-value. Ann Intern Med 2017;167:268-274. doi:10.7326/M16-2607; with the counterpoint by Ioannidis JPA, Tan YJ, Blum MR. Ann Intern Med 2019;170:108-111. doi:10.7326/M18-2159
- Lipsitch M, Tchetgen Tchetgen E, Cohen T. Negative controls. Epidemiology 2010;21:383-388. doi:10.1097/EDE.0b013e3181d61eeb
- Hernán MA, Robins JM. Using big data to emulate a target trial. Am J Epidemiol 2016;183:758-764. doi:10.1093/aje/kwv254

**Writing**

- Mensh B, Kording K. Ten simple rules for structuring papers. PLoS Comput Biol 2017;13:e1005619. doi:10.1371/journal.pcbi.1005619
- Gopen GD, Swan JA. The science of scientific writing. Am Sci 1990;78:550-558.
- Pinker S. The Sense of Style. 2014 (on compulsive hedging).
- Docherty M, Smith R. The case for structuring the discussion of scientific papers. BMJ 1999;318:1224-1225. doi:10.1136/bmj.318.7193.1224
- Puhan MA, et al. Discussing study limitations in reports of biomedical studies. Health Qual Life Outcomes 2012;10:23. doi:10.1186/1477-7525-10-23
- STROBE items 19-20; ICMJE recommendations.

## Considered and not borrowed

- Reviewer-style skills (K-Dense peer-review, scientific-critical-thinking, pre-submission review simulators, Sakana's reviewer): their output is the defensive list of concerns this skill replaces.
- Full multiverse tooling and hypothesis tournaments (AI co-scientist): too heavy for one-project audits and at odds with the rule that every analysis earns its place.
- Deletion-first cleanup skills: replaced by logged archiving.
