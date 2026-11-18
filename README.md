# Biomedical Publication Suite

Turn a biomedical study folder into the paper it is trying to become.

Biomedical Publication Suite is an Agent Skill for biomedical manuscript writing and publication polish. It helps a coding agent review a study folder, understand the analysis outputs, find the strongest scientific story, decide what belongs in the paper, and draft or revise publication-ready materials.

It is built for real research projects with figures, tables, model outputs, notes, partial drafts, reviewer comments, journal instructions, and messy intermediate files. The goal is not to summarize everything in the folder. The goal is to help the agent write like a careful biomedical author: clear, accurate, confident where the evidence supports confidence, and honest about what still needs author review.

Before a near-final manuscript or figure is handed over, the skill runs [cold reads](plugins/biomedical-publication-suite/skills/biomedical-publication-suite/references/cold-reader-rounds.md): fresh subagents that know nothing about the project read the actual draft or rendered figure from different perspectives, the main agent weighs their feedback against the evidence and revises, and new readers check the result. New figures start from a [house style](plugins/biomedical-publication-suite/skills/biomedical-publication-suite/references/figure-house-style.md) meant to look at home in a major clinical journal; it is a default the agent adapts, not a rule set. See the [synthetic two-panel figure](plugins/biomedical-publication-suite/skills/biomedical-publication-suite/assets/figure-example.png) with its [print PDF](plugins/biomedical-publication-suite/skills/biomedical-publication-suite/assets/figure-example.pdf) and [R script](plugins/biomedical-publication-suite/skills/biomedical-publication-suite/assets/figure-example.R).

## What It Helps You Do

- Find the main scientific story in a completed analysis project.
- Decide which results to feature, shorten, move to the supplement, or leave out.
- Draft full biomedical manuscripts from the evidence in a project folder.
- Find relevant papers for a research question, verify the citations, and extract study details with source support.
- Improve abstracts, titles, figure legends, table text, cover letters, and reviewer responses.
- Adapt a manuscript for a target journal or article type.
- Keep author notes and unresolved checks separate from text meant for submission.

## Install

The skill works in Claude Code and Codex, and in any other agent that reads Agent Skills. The repository is called `biomedical-publication-skill`; the plugin, the skill and every install or update command use the name `biomedical-publication-suite`.

You can also paste this into Claude Code or Codex and let the agent do it:

```text
Install this plugin for all my agents, then teach me how to use it: https://github.com/caude1/biomedical-publication-skill
```

The agent will ask before running each install command. Expect a few approvals, because it downloads from GitHub and writes to your agents' settings folders.

### Claude Code

Inside Claude Code:

```text
/plugin marketplace add caude1/biomedical-publication-skill
/plugin install biomedical-publication-suite@biomedical-publication-suite
```

Or in a terminal:

```bash
claude plugin marketplace add caude1/biomedical-publication-skill
claude plugin install biomedical-publication-suite@biomedical-publication-suite
```

### Codex

```bash
codex plugin marketplace add caude1/biomedical-publication-skill
codex plugin add biomedical-publication-suite@biomedical-publication-suite
```

Start a new session or thread after installing so the agent loads the skill.

### Getting updates

- **Claude Code** can update the skill on its own. Type `/plugin`, open **Marketplaces**, select `biomedical-publication-suite` and choose **Enable auto-update**. Claude Code then checks for a new version shortly after each session starts and loads it the next time it starts. To update by hand instead, run `/plugin marketplace update biomedical-publication-suite`.
- **Codex** has no automatic option. Run this now and then; it updates the installed copy in place:

  ```bash
  codex plugin marketplace upgrade biomedical-publication-suite
  ```

- **Zip installs** do not update. Download the zip from the [latest release](https://github.com/caude1/biomedical-publication-skill/releases/latest) again and replace the folder.

Each release is listed on the [releases page](https://github.com/caude1/biomedical-publication-skill/releases) with a short note on what changed.

### Other agents

For an agent without a plugin system, download `biomedical-publication-suite.zip` from the [latest release](https://github.com/caude1/biomedical-publication-skill/releases/latest) and unzip it into that agent's skills folder, for example `~/.gemini/skills/` for Gemini CLI. Gemini CLI can also install it directly once you are signed in to Gemini:

```bash
gemini skills install https://github.com/caude1/biomedical-publication-skill.git --path plugins/biomedical-publication-suite/skills/biomedical-publication-suite
```

### Several agents on one computer

Install the plugin in Claude Code and in Codex, and use a skills folder only for the other agents. Do not also put the skill in `~/.agents/skills` or `~/.claude/skills`: Codex reads `~/.agents/skills` and Claude Code reads `~/.claude/skills`, so each would load the skill twice. A copy in one project's `.agents/skills/` folder is shared with everyone who works on that project.

In the Claude desktop or web app, upload the same zip as a skill in the Skills settings.

With git instead of the zip, clone once and copy or link the skill folder into the agent's skills folder:

```bash
git clone https://github.com/caude1/biomedical-publication-skill.git
cp -R biomedical-publication-skill/plugins/biomedical-publication-suite/skills/biomedical-publication-suite ~/.gemini/skills/
```

Run `git pull` in the clone to update a linked copy; a copied folder is replaced the same way as a zip install.

### What is in the repository

The skill itself is one folder, `plugins/biomedical-publication-suite/skills/biomedical-publication-suite`. The plugin wraps that same folder with a short description file for each tool (`.claude-plugin/` and `.codex-plugin/`), and the repository lists it in a catalog that each tool reads (`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`). The instructions, figures and helper scripts are shared; the helpers need only Python 3.10 or later.

## Prompt Library

These prompts are written for the most common setup: the agent is already running inside the research directory that contains the analysis, results, figures, tables, notes, and drafts.

For the first line, use whichever handle fits how you installed it:

```text
Codex:                                $biomedical-publication-suite
Claude Code, plugin install:          /biomedical-publication-suite:biomedical-publication-suite
Claude Code, folder or zip install:   /biomedical-publication-suite
Any agent:                            Use Biomedical Publication Suite.
```

The agent also loads the skill on its own when a request matches what it does, so the handle is optional.

### 1. Propose The Manuscript Before Drafting

Use this when the project is messy, exploratory, high stakes, or still needs a narrative decision before anyone spends time on a full draft.

```text
$biomedical-publication-suite

Review this directory as a completed biomedical study and propose the manuscript before drafting it.

Run a narrative audit. Inventory the analysis, results, figures, tables, notes, and any existing draft. Return:

1. The proposed scientific story.
2. The headline finding and central manuscript thesis.
3. A one-line-per-section manuscript outline.
4. The editorial rationale for what you would feature, subordinate, move to supplement, cut, or reserve for limitations.
5. Open author-verification items for anything that cannot be confirmed from the project files.

Use your best judgment to decide what the paper is about.

Do not draft the full manuscript yet. I want to review the narrative first.
```

### 2. Build The Full Manuscript

Use this after you have approved a narrative audit, or when the project already has a clear manuscript direction.

```text
$biomedical-publication-suite

Build the full manuscript package from this directory.

If a narrative brief or narrative audit already exists, build from the approved narrative. Otherwise, treat this as a completed biomedical study: review the project evidence, decide the strongest manuscript narrative, and use your best judgment on what to feature, subordinate, move to supplement, cut, or reserve for limitations.

Infer the study design, article type, and target-journal needs from the project files when possible. If they are not clear, make conservative choices and record them as author-verification items rather than stopping.

Proceed without clarifying questions unless something is truly blocking. Do not invent missing numbers, methods, results, ethics language, citations, or journal requirements.
```

### 3. One-Shot Manuscript Draft

Use this when you want the agent to move directly from project folder to manuscript draft without a narrative checkpoint.

```text
$biomedical-publication-suite

Review this directory and produce a complete manuscript draft.

Use your best judgment to decide the manuscript narrative, including what to include, subordinate, move to supplement, cut, or reserve for limitations. Do not mechanically summarize every output. Organize the results into the strongest scientific story supported by the project files.

Draft the manuscript, reconcile every number and citation against the project outputs, review the prose by reading it against the skill's register guide, and list author-verification items separately.
```

### 4. Refine Existing Draft

Use this when a manuscript already exists but needs a stronger story, cleaner structure, or publication-facing prose.

```text
$biomedical-publication-suite

Review this directory and revise the existing manuscript draft.

Use the project outputs to judge whether the current draft has the right narrative, whether sections should be cut, reordered, or reframed, whether any included result distracts from the central thesis, and whether any omitted result should be restored.

Revise the manuscript directly. Keep author-facing notes separate from the manuscript.
```

### 5. Skeptical Pre-Draft Critique

Use this when you are not sure the project supports a manuscript yet, or when you want a hard editorial read before drafting.

```text
$biomedical-publication-suite

Review this directory as a skeptical senior reviewer.

Do not rewrite yet. Tell me:

1. What paper this project is currently trying to be.
2. Whether the central claim is earned.
3. Which results belong in the main text.
4. Which results belong in the supplement.
5. Which results should be cut or kept only as internal context.
6. What must be fixed before drafting.
7. Whether there is a publishable manuscript here, and if so, what the best version is.
```

### 6. Journal Adaptation

Use this when you have a draft and need it reshaped for a specific journal or article type.

```text
$biomedical-publication-suite

Adapt the manuscript package in this directory for the target journal and article type named in the project files.

If the target journal or article type is not specified, infer the most appropriate format conservatively and record the assumption as an author-verification item.

Match the journal's structure, abstract format, length expectations, reporting-guideline needs, references, display limits, and required statements where available. Preserve the central thesis and scientific accuracy.
```

### 7. Reviewer Response

Use this when editor or reviewer comments are available as files in the directory or pasted into the chat.

```text
$biomedical-publication-suite

Use the reviewer and editor comments in this directory, or the comments pasted below, to revise the manuscript and draft a point-by-point response.

For each comment:

1. Classify the issue.
2. Decide whether to revise, clarify, add analysis, decline, or explain.
3. Make the manuscript change when warranted.
4. Draft response text naming what changed and where.
5. If you would push back, do so respectfully and explain the reasoning.

Keep manuscript revisions separate from response-letter explanations.
```

### 8. Find And Extract The Literature

Use this when you want the agent to build a reliable evidence base before writing, revising, or answering reviewers.

```text
$biomedical-publication-suite

Find the relevant biomedical literature for this question and build a verified evidence package.

First define the question and inclusion criteria. Then search broadly across available literature sources, reference lists, citation trails, registries, and full text when available.

Do not trust a paper just because a search result or web page mentions it. Verify each citation before using it. For every included study, extract the key details with a source locator or quote whenever possible.

Return:

1. The search strategy.
2. The candidate papers found.
3. The included and excluded studies with reasons.
4. The verified citations.
5. The extracted study details.
6. Any papers or fields that still need full-text access or author review.
```

### 9. Cut To A Word Limit

Use this when the draft is over the journal's limit.

```text
$biomedical-publication-suite

Bring the main text under the journal's word limit.

Reorganize and rewrite overlapping paragraphs before trimming sentences in place, so the argument still flows. Keep every number, citation and claim, or tell me what you removed. Report the final count and how it was counted.
```

### 10. Fix A Sentence Or Paragraph

Use this when a passage sounds informal, convoluted, overconfident or AI-written.

```text
$biomedical-publication-suite

I don't like this passage: "<paste it here>"

Tell me what is wrong with it, then give me two or three distinct rewrites in a plain, formal scientific register and say which you prefer. Do not change any number or claim.
```

### 11. Prune The Supplement

Use this when the supplement has grown into an archive.

```text
$biomedical-publication-suite

Rethink the supplementary materials from the paper's central claim outward.

Keep what a reader needs to evaluate or reproduce the main findings, plus anything the reporting guideline or venue requires. List what you would leave out and could add back if a reviewer asks.
```

### 12. Cold Reads Before Handoff

Use this when a manuscript, figure or response letter is nearly final.

```text
$biomedical-publication-suite

This manuscript and its figures are nearly final. Run cold reads with fresh readers who know nothing about the project, from at least three perspectives.

Fix what they misread, adopt the suggestions that make the paper clearer or more correct, and decline the ones that would only add length or hedging. Then have new readers check the revised version. Tell me what changed and what you declined.
```

### 13. Publication-Ready Figure

Use this when a figure needs to look like it belongs in a major journal.

```text
$biomedical-publication-suite

Redraw Figure 2 from the analysis outputs so it would look at home in JAMA or NEJM.

Start from the house style and use your judgment about which parts fit this figure. Keep each group's color and marker consistent with the other figures. Export it at print width, look at the export yourself, and have a figure-first cold reader tell you what they think it shows.
```

### 14. Make It Easy For A First-Time Reader

Use this when a draft is accurate but hard to follow, especially a methods-heavy paper written for clinicians.

```text
$biomedical-publication-suite

Read this manuscript as a clinician who has never seen the project. Mark every place where that reader would stop to ask what something means, why we did it, or what a phrase refers to, and every number or rule that could look arbitrary.

Fix each one with the shortest change that removes the question. Give choices their reasons from the study record, and ask me where the record has none. Move defensive asides to the Limitations or cut them, but keep every step that changed the data or the analysis in the Methods. Keep confirm-only robustness analyses out of the main text, and do not add hedges. Then list the substantive changes.
```

### Recommended Defaults

Use **Prompt 1** when the project is messy, exploratory, or high stakes. That is the best main workflow.

Use **Prompt 2** after you approve the narrative.

Use **Prompt 3** when you want the agent to produce the paper without a checkpoint.

Use **Prompt 5** when you are not sure the project actually supports a manuscript yet.

Use **Prompt 8** when the manuscript needs a stronger literature base, when you are starting a review-style task, or when you want citation and study extraction checks before drafting.

Use **Prompt 12** before sending a draft to coauthors or a journal.

## What Makes It Different

Many manuscript-writing prompts produce a project memo: a chronological summary of files, decisions, caveats, and disconnected results. Biomedical Publication Suite pushes the agent toward the finished paper instead. It asks the agent to write for the reader of the manuscript, not for the person managing the project.

The skill emphasizes:

- the final scientific logic, not the research timeline;
- prose a reader with no context can follow on one pass, with every choice that could look arbitrary given its reason;
- the strongest accurate finding, not every available output;
- broad literature discovery followed by citation verification;
- study details extracted from sources, not memory;
- confident language inside the evidence boundary;
- limitations in the right place, not defensive hedging throughout the manuscript;
- a plain, formal register that is neither performed, loose nor convoluted;
- prose reviewed by reading, with scripts kept to facts a machine can settle;
- a lean limitations section and a short, selective supplement;
- cold reads by fresh readers before a near-final draft or figure is handed over;
- figures drawn to a restrained, journal-quality default;
- clean publication text first, with author checks kept separate.

## Repository Layout

    plugins/biomedical-publication-suite/

The full plugin package.

    plugins/biomedical-publication-suite/skills/biomedical-publication-suite/

The portable Agent Skill. This is the folder to copy or link for agents that support skills directly.

    .agents/plugins/marketplace.json

The plugin catalog that Codex reads.

    .claude-plugin/marketplace.json

The plugin catalog that Claude Code reads.

    .github/workflows/tests.yml

Runs the helper unit tests and the package integrity check on every push.

    .github/workflows/release.yml

Publishes a release with the zip whenever a new version reaches `main`.

Version history is in [CHANGELOG.md](plugins/biomedical-publication-suite/CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE). Sources that informed the design keep their own licenses and are credited in the [third-party notices](plugins/biomedical-publication-suite/THIRD_PARTY_NOTICES.md).
