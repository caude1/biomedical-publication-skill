# Biomedical Publication Suite

A publication assistant centered on scientific reasoning and editorial judgment. It helps turn study evidence into a paper written for an outside reader, with a coherent final rationale, direct findings, and deliberately placed limitations.

## Install

In Claude Code:

```text
/plugin marketplace add caude1/biomedical-publication-skill
/plugin install biomedical-publication-suite@biomedical-publication-suite
```

In Codex:

```bash
codex plugin marketplace add caude1/biomedical-publication-skill
codex plugin add biomedical-publication-suite@biomedical-publication-suite
```

About once a week, when the skill is used, it checks whether a newer version is published and, if so, tells you and offers to run the update command. It sends nothing about you or your work; set `BPS_UPDATE_CHECK=off` to turn the check off. To receive updates automatically in Claude Code, type `/plugin`, open **Marketplaces**, select `biomedical-publication-suite` and choose **Enable auto-update**. In Codex, run `codex plugin marketplace upgrade biomedical-publication-suite` now and then; it updates the installed copy in place.

For other agents, unzip `biomedical-publication-suite.zip` from the [latest release](https://github.com/caude1/biomedical-publication-skill/releases/latest) into the agent's skills folder.

## Use it

Invoke it as `$biomedical-publication-suite` in Codex, or in Claude Code as `/biomedical-publication-suite:biomedical-publication-suite` after a plugin install or `/biomedical-publication-suite` after a folder install, with the manuscript, study folder, results, references or reviewer comments relevant to your request. It adapts to a paragraph edit, a full manuscript, a review or submission preparation. It does not require a scaffold, script run, citation quota or fixed iteration count.

Useful requests:

- “Turn these research notes into a publication-facing Results section. Omit internal analysis history; preserve the final results and their meaning.”
- “Rewrite this abstract with clearer, more confident scientific prose. Keep every result, comparison and necessary uncertainty accurate.”
- “Review this manuscript as a skeptical editor. Give prioritized findings with locations; do not rewrite yet.”
- “Develop the scientific narrative and outline from these outputs, then draft the supported sections and list factual gaps separately.”
- “Verify these references and whether their actual passages support the claims.”
- “Plan this systematic/scoping review from the supplied question and methods. Distinguish completed work from the next steps.”
- “Plan and balance the manuscript length for this article type, using comparable papers or the journal’s verified limit.”
- “Adapt this draft to the current official instructions for this journal.”
- “Get this under the 3,000-word limit by reorganizing, not by trimming in place.”
- “This sentence reads as too informal (or too convoluted, or AI-written). Give me alternatives.”
- “Prune the supplement to what the main text actually needs.”
- “Address these reviewer comments and verify that every response matches a real manuscript change.”
- “This manuscript is nearly final. Run cold reads with fresh readers, fix what they misread, and tell me what you changed and what you declined.”
- “Redraw Figure 2 in the house style so it would look at home in JAMA. Keep the existing group colors.”

The skill keeps literature identity, source access, claim support and publication status distinct. It reports supplied statistics faithfully; new estimates and analyses require actual computation. It preserves author voice, primary/null/adverse findings and real prespecification while removing irrelevant internal-report language. Humanization means better scientific writing, never detector gaming.

For near-final work, the [cold-reader workflow](skills/biomedical-publication-suite/references/cold-reader-rounds.md) gives the draft or rendered figure to fresh subagents that know nothing about the project, each reading from a different perspective. The main agent weighs their feedback against the evidence, revises, and sends the new version to new readers. The [figure house style](skills/biomedical-publication-suite/references/figure-house-style.md) is the default look for new figures: print-scale type, a restrained palette and working conventions for common figure types, all adjustable. See the [synthetic two-panel figure](skills/biomedical-publication-suite/assets/figure-example.png) with its [print PDF](skills/biomedical-publication-suite/assets/figure-example.pdf) and [reproducible R script](skills/biomedical-publication-suite/assets/figure-example.R), and the [subgroup forest plot](skills/biomedical-publication-suite/assets/forest-example.png) that a fresh agent drew from the guide during testing.

## Architecture

Start at [SKILL.md](skills/biomedical-publication-suite/SKILL.md). Task-specific references load only when needed. [Optional helpers](skills/biomedical-publication-suite/references/tool-contracts.md) support repeated identifier, file and ledger checks; they do not replace scientific/editorial review. Python 3.10+ standard library is sufficient. Reference lookup can use available tools or manual authoritative inspection.

[Agent adapters](agent-adapters/README.md) point other local clients to the same portable skill. [Research provenance](docs/agent-design-research.md), [publication standards](docs/publication-standards-research.md), and [third-party notices](THIRD_PARTY_NOTICES.md) explain material influences and their limits.

## Maintenance and evaluation

Keep one durable source for an installation (this plugin folder, wherever it is cloned) and point each agent's skill directory at it with a link. Plugin caches are generated from that source on reinstall; edit the source, never a cache. Executable skill resources use relative paths.

Run `python3 -m unittest discover -s tests -v` for deterministic regressions and `python3 scripts/validate_suite.py` for package/link/resource checks. [Behavioral evaluations](tests/behavioral-evals.json) and [evaluation instructions](tests/EVALUATION.md) exercise actual fresh-agent writing and reasoning. Code tests do not establish prose quality or scientific correctness. Rerun targeted behavioral cases when changing editorial instructions.

The design favors manual workflows: prose is judged by reading, and helpers only check facts a machine can settle. No automatic hooks, mandatory external service, autonomous submission or machine readiness certification is installed.

## License

MIT. See [LICENSE.txt](skills/biomedical-publication-suite/LICENSE.txt). Sources that informed the design keep their own licenses and are credited in the [third-party notices](THIRD_PARTY_NOTICES.md).
