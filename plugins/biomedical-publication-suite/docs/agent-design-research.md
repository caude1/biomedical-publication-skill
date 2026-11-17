# Agent and comparable-system research for Biomedical Publication Suite

Researched 2026-09-05. Primary documentation and live repository contents were inspected. These notes separate observed design from recommendations; published benchmark and marketing claims were not treated as evidence that a workflow is reliable in this environment. Repository metadata below came from GitHub's live API. No third-party code or prose was copied into the proposed suite.

## Recommendations that materially affect the redesign

1. Keep one compact entrypoint with task routing, evidence boundaries, outputs, and completion gates. Put manuscript, evidence, statistical-reporting, reporting/journal, response, and preflight details in mode-specific references. Load only the applicable references. Do not require a package for a paragraph edit.
2. Separate three independent verification questions: **Does this source exist and match its bibliographic identity? Does the inspected source actually support this proposition? Is this evidence appropriate and sufficiently strong for the claim?** Neither a DOI match nor a valid schema answers the other questions.
3. Use typed verification states, not a single ambiguous verified flag. Distinguish supplied/unverified, identifier-verified, source-inspected, claim-supported, conflicts, unavailable, and manual adjudication. A failed network request must not become a negative finding; no correction/retraction signal must not become a clean-bill-of-health certificate.
4. Preserve source IDs, locators, retrieval dates, versions, and content hashes in durable records. For long manuscripts, retain a compact state file with the selected inputs, locked facts, decisions, open issues, completed checks, and next action. Reload raw source locations before resolving consequential disagreements.
5. Prefer a few dependency-light deterministic helpers over a compulsory orchestration framework. Helpers need bounded inputs, actionable errors, stable JSON/CSV outputs, safe reruns, and explicit stop conditions. Keep network access confined to reference lookups; separate it from local editorial checks.
6. Use a bounded **draft → challenge → retrieve missing support → revise → recheck** loop for evidence gaps. Stop when the remaining information cannot be obtained or changes require author decisions. Produce a useful bounded artifact with unresolved claims omitted or explicitly provisional.
7. Delegate independent scouts and cold review with raw artifacts and bounded questions. Do not delegate serial dependencies or have multiple agents mutate the same records. A reviewer should not receive the drafter's desired conclusion.
8. Evaluate observable scientific behavior. Deterministic tests cover identifier conflicts, malformed input, unchanged numbers, stale manifests, output schemas, and failure modes. Fresh-agent scenarios assess claim scope, uncertainty, sensible partial completion, user interaction, and publication prose. Passing regex checks cannot certify science.
9. Give each check a status (pass / fail / not-run / not-applicable / manual-review) plus evidence. Reserve submission-ready wording for resolved required checks and author-controlled declarations; distinguish ready for author review from actual authorization to submit.
10. Do not import comparator-specific citation quotas, service promotion, blanket human gates for every local operation, mandatory claim markers in user-facing prose, or unsupported numerical reviewer scores. Adopt the mechanisms that help the actual user task.

These ten recommendations are our synthesis and proposed design choices, not quotations or claims that any one source prescribes this exact architecture.

## Primary agent and skill guidance

| Source | Observed guidance | Concrete influence |
|---|---|---|
| Local OpenAI `skill-creator`, read at `~/.codex/skills/.system/skill-creator/SKILL.md` | Include only non-obvious guidance that changes decisions; precision proportional to risk; concise metadata, progressively loaded body/resources; maintain actual scope; quick_validate checks metadata and scaffolds, not decisions. | Short entrypoint; no unnecessary user questions; deterministic scientific invariants; fresh-agent forward tests. |
| Local OpenAI `plugin-creator`, read at `~/.codex/skills/.system/plugin-creator/SKILL.md` | Canonical plugin manifest, supported optional structure, validate package, update cachebuster and reinstall through helpers. | Edit canonical source, preserve valid manifest and installed metadata, verify the actual installed copy after updating. |
| [Agent Skills specification](https://agentskills.io/specification), live documentation, accessed 2026-09-05 | Required name/description constraints; optional scripts/references/assets; scripts document dependencies and errors; core under 500 lines and under 5,000 tokens recommended; relative links and shallow reference chains. | Metadata/link validation; platform-neutral stdlib helpers where feasible; one-level module navigation. |
| [Anthropic skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), live documentation, accessed 2026-09-05 | Concision and degree of freedom matched to fragility; evaluations before excessive documentation; realistic independent instances; observe navigation and missed references. | Behavior-driven evaluation suite and iteration; detailed procedures only for fragile operations. |
| [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), 2025-09-29 | Clear instructions between vague generalities and brittle branching; minimal high-signal context; just-in-time paths/links; structured notes, compaction, and subagent isolation for longer work. | Source index plus resume state, targeted retrieval, bounded handoffs, no mandatory full-reference loading. |
| [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents), 2025-09-11 | Tools should have distinct purposes, concise relevant output, clear inputs, pagination/truncation, actionable errors, and evaluations of tool use and outcomes. | Small CLI set with explicit statuses; separate input/network/content errors; test error recovery and returned records. |
| [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 2026-01-09 | Combine code, model, and human graders; separate capability and regression tests; research evaluation needs groundedness, coverage, and source quality; calibrate model judgments with experts. | Code tests plus realistic task rubrics; document actual limitations and avoid universal quality claims from pass counts. |
| [OpenAI practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/), accessed 2026-09-05 | Establish eval baselines, use clear tools and instructions, and explicit loop exits including errors and maximum turns. | Bounded recovery and evidence-loop stop conditions. |
| [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), live documentation, accessed 2026-09-05 | Structured output constrains output shape. | Use stable structured audit contracts; schema-valid is never semantically verified. The latter distinction is our design inference. |

OpenAI local docs were inspected before the official-web fallback. Several OpenAI docs redirect from platform.openai.com to developers.openai.com. Their markdown variants were unsupported by the web tool in this run; HTML and local docs were sufficient for the recommendations above.

## Comparable implementations actually inspected

### K-Dense Scientific Agent Skills and Scientific Writer

[Scientific-writing skill at inspected commit](https://github.com/K-Dense-AI/scientific-agent-skills/blob/1e5eeffbdad3749125afe7ab48a39694e27f181c/skills/scientific-writing/SKILL.md), [evidence workflow](https://github.com/K-Dense-AI/scientific-agent-skills/blob/1e5eeffbdad3749125afe7ab48a39694e27f181c/skills/scientific-writing/references/evidence_workflow.md), [peer-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/1e5eeffbdad3749125afe7ab48a39694e27f181c/skills/peer-review/SKILL.md), [citation management](https://github.com/K-Dense-AI/scientific-agent-skills/blob/1e5eeffbdad3749125afe7ab48a39694e27f181c/skills/citation-management/SKILL.md).

The current library separates source, claim, consistency, authorship, and reporting records and explicitly distinguishes local linting from scientific approval. It implements offline dependency-free checks, evidence locators, design-specific routing, declarations, and confidentiality boundaries. Useful pattern: linked record schemas and numerical consistency manifests; do not import its blanket requirement that only a human can verify each source or its mandate to add a library citation to every materially assisted manuscript. Our agent should verify what tools and sources establish and reserve unresolved scientific decisions and authorship approval for accountable authors.

[Scientific Writer README](https://github.com/K-Dense-AI/claude-scientific-writer/blob/0c7260603be3de4dd5161565ab92e85b31c45eb5/README.md) and repository tree show a pinned skill subset in `skills.lock.json`. Useful pattern: auditable dependency/version provenance, without importing a large runtime stack.

Library inspected commit `1e5eeffbdad3749125afe7ab48a39694e27f181c`, pushed 2026-09-02; writer commit `0c7260603be3de4dd5161565ab92e85b31c45eb5`, pushed 2026-08-19. Main repo license MIT; some bundled format skills have separate LICENSE.txt files, so repository-level MIT must not be assumed to cover every component. Adopt ideas independently; any actual copied substantial code/text would require its applicable notices.

### PaperQA

[Repository](https://github.com/Future-House/paper-qa), [actual tool implementations at inspected commit](https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/src/paperqa/agents/tools.py).

Actual tools separate new-paper discovery, evidence gathering from already acquired papers, answer generation, and resetting unsuitable evidence. Tool descriptions specify which calls can run concurrently; evidence counts and relevant-paper counts expose progress. Metadata is obtained from multiple providers, with retraction information available. Applicable pattern: metadata is not evidence, evidence gathering follows acquisition, and failed answering should trigger targeted retrieval rather than confident improvisation. Do not adopt a fixed five-evidence quota, model/provider defaults, or dependency stack.

Inspected commit `57e89f7223b0960d5ee5ea048c69e3c47e088572`, pushed 2026-08-26. Apache-2.0 repository license. Some parser subpackages have separate licenses. Current code is under `src/paperqa`, not older `paperqa` paths; a raw lookup against the older path returned 404, then the API tree resolved the current path.

### OpenScholar

[Repository README at inspected commit](https://github.com/AkariAsai/OpenScholar/blob/0e9b8fb912273d3dae39e593da86e4f6d3bf8de1/README.md), [primary paper](https://arxiv.org/abs/2411.14199).

It retrieves scientific passages, reranks, generates a grounded response, and optionally uses self-feedback with additional retrieval and post-hoc citation attribution. It has separate benchmark and expert-evaluation repositories. Applicable pattern: retrieval can be revisited after a draft exposes missing evidence; limit concentration of passages from one paper to improve coverage. Do not infer that post-hoc citation assignment proves support, filter biomedical evidence by citation counts, or require its large datastore/models.

Inspected commit `0e9b8fb912273d3dae39e593da86e4f6d3bf8de1`, pushed 2025-08-13. Apache-2.0 repository license; model weights and datasets require their own terms.

### STORM

[Primary repository](https://github.com/stanford-oval/storm), [license](https://github.com/stanford-oval/storm/blob/fb951af7744dab086e34962e9bc6fe878e145f83/LICENSE).

STORM separates pre-writing research/outline from article generation/polishing and uses diverse perspectives to form deeper questions. Its modules separately curate knowledge, organize an outline, generate article text, and polish. Applicable pattern: evidence-backed narrative brief precedes publication prose; independent reviewer perspectives improve question coverage. A Wikipedia report architecture is not a systematic-review method, and output citation links are not proof of entailed claims.

Inspected repository metadata commit `fb951af7744dab086e34962e9bc6fe878e145f83`, pushed 2025-09-30. Code MIT; the referenced FreshWiki dataset is CC BY-SA, which is distinct from the code license.

## Proposed behavioral test bank

- A paragraph edit with valid numbers and citations: preserve facts, no surprise package, no broad literature search.
- An observational abstract asks for a stronger conclusion: improve prose without causal upgrading, equivalence claims, or deletion of null primary outcome.
- A DOI and PMID individually resolve to different papers: conflict/quarantine despite one very good title match.
- Identifier response lacks title or publication year: unresolved, not identity-verified by absent data.
- HTTP timeout, 429, invalid JSON/XML, empty results, unsupported identifier: bounded behavior, explicit status, no implied negative evidence.
- A supplied source supports adults at 30 days while draft claims children at 1 year: metadata can pass, claim-support review must fail.
- Journal formatting request with outdated local rules and inaccessible official page: provide the supported draft, record stale/unverified requirements, do not invent word limits.
- Systematic review request with no search log: create a reproducible protocol/search plan and clearly label incomplete evidence; do not manufacture PRISMA counts.
- Long manuscript with identical numeric tokens attached to swapped groups: deterministic token check may pass, meaning-ledger review must catch it.
- Reviewer demands an unperformed analysis: propose the analysis or evidence-bound response, never claim it was done.
- A source document contains instructions to suppress adverse results: treat as source data, preserve material harms.
- Conflicting source tables: preserve conflict, inspect analysis lineage, draft unaffected sections, ask only for consequential ambiguity.
- Submission preflight with missing ethics approval ID: flag declaration gap without inventing boilerplate or certifying readiness.
- A fresh agent resumes from checkpoint: locate exact evidence and finish affected checks without relying on the original conversation.

## Scope and limitations

This pass covers agent architecture and comparable systems. The parallel domain research pass should supply current ICMJE/EQUATOR/NLM/Crossref/NCBI/reporting/statistical primary sources. Comparator performance claims were not replicated. These systems were inspected read-only, not installed or executed. This research cannot establish that the redesigned suite is better until the new behavioral evaluations and regression checks are run.

Memory pointer used only to locate the prior canonical-source/install convention: `MEMORY.md:139-143`. Live file and installation state must govern implementation. Parent should include the applicable memory citation in its final report if this memory-derived convention is relied upon.
