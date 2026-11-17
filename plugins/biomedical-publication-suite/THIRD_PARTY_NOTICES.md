# Third-Party Influences and Adaptation Notes

This plugin's scientific-humanization update was written independently after reviewing the sources below on 2026-08-31. The review extracted general editorial and workflow principles. No upstream diagnostic script, detector score, example passage, or substantial block of prose was copied into the plugin. Behavioral-evaluation themes were adapted into independently written prompts with new fixtures. The new `revision_invariants.py` implementation and executable tests are original.

The source projects remain governed by their own licenses. Their inclusion here is attribution and provenance, not a claim that they endorse this plugin.

## Primary comparator

### SciHumanizer

- Source: https://github.com/Elaraby0/sci-humanizer
- Reviewed commit: `8b7d7025437f35cb7525aedb17119543f8ca600f`
- Upstream skill version: 1.1.1
- License: MIT; upstream notices name Siqi Chen (2025) and Elaraby0 (2026) and retain a separate Stanford-course rights boundary.
- Adopted in original language: scientific truth conditions before style; a pre/post meaning ledger; structure-before-sentence revision; contextual treatment of passive voice, hedges, technical repetition, and punctuation; preservation of null and adverse findings; nonsignificance semantics; confidential-manuscript controls; and behavioral evaluation themes.
- Not adopted: the upstream diagnostic implementation, mandatory tracked-plus-clean output, any lexical blacklist, fixed length thresholds, course-corpus claims that cannot be independently inspected from the repository, or detector-oriented success criteria.

## Additional skill and plugin comparators

### Humanize Paper

- Source: https://github.com/SyntaxSmith/humanize-paper
- License: MIT.
- Adopted in original language: the two-axis distinction between edit intensity and claim authority; named-defect requirement before structural reconstruction; protected mechanical anchors and semantic-risk markers; and the warning that a script cannot prove semantic equivalence.
- Not adopted: ML-specific examples or any claim that regular expressions can validate meaning.

### Academic Humanizer

- Source: https://github.com/AIScientists-Dev/academic-humanizer
- License: MIT.
- Adopted in original language: author and venue calibration; explicit separation of manuscript evidence from grant feasibility; and preservation of supported proposal ambition.
- Not adopted: fixed funder or venue rules, domain-specific examples, or hard punctuation bans.

### Codex Academic Humanizer

- Source: https://github.com/henmuc/codex-academic-humanizer
- License: MIT.
- Adopted in original language: light, standard, and deep revision intensity; protected LaTeX, citations, variables, cross-references, and identifiers; long-document terminology consistency; and trait-based voice matching.
- Not adopted: mandatory paragraph-by-paragraph comparisons.

### Humanizer

- Source: https://github.com/ashgreat/humanizer
- License: MIT.
- Adopted in original language: candidate signals from paired academic revisions, including inflated verbs, copula avoidance, metadiscourse, paragraph fragmentation, and flattened rhythm; cluster-based rather than single-token review.
- Not adopted: corpus thresholds, AI-likeness scores, a universal first-person target, or an em-dash ban. Its paired corpus is not biomedical and therefore informs editorial questions rather than biomedical rules.

### Humanize Writing

- Source: https://github.com/shir-danishyar/humanize
- License: MIT.
- Adopted in original language: distinguish generation from revision; protect quotations and factual anchors; infer register from audience; and preserve supplied voice samples.
- Not adopted: formal-register punctuation quotas, banned-word semantics, or detector optimization.

### SciWrite

- Source: https://github.com/labarba/sciwrite
- License: CC BY 4.0.
- Adopted in original language: review-only and targeted-review modes; severity-ranked editorial findings; terminology consistency; numerical/citation integrity; and the value of interactive teaching when requested.
- Not adopted: course-derived wording, examples, fixed active-voice rules, or universal acronym assumptions.

### Scientific Using Kit

- Source: https://github.com/keithhegit/sci-using-kit
- License: MIT.
- Adopted in original language: a comparison-legitimacy gate spanning population, intervention or exposure, comparator, outcome, time horizon, ascertainment, model, effect measure, aggregation, and evidence level.
- Not adopted: engineering-specific examples or domain-specific comparison tables.

### Anthropic Doc Co-Authoring

- Source: https://github.com/anthropics/skills/tree/main/skills/doc-coauthoring
- License: see the upstream repository.
- Adopted in original language: context-isolated reader testing that asks a fresh reviewer to recover the intended message without being told the answer.
- Not adopted: its documentation-specific staged interview as a mandatory biomedical workflow.

## Integrity and policy anchors

- ICMJE, current artificial-intelligence guidance: https://www.icmje.org/recommendations/browse/artificial-intelligence/
- EQUATOR Network reporting-guideline library: https://www.equator-network.org/reporting-guidelines/

These official sources are time-sensitive. The plugin links to them and instructs agents to verify current venue, institutional, funder, reporting, confidentiality, and disclosure requirements at use time rather than freezing policy text into the skill.

## Explicitly rejected practices

The plugin does not:

- optimize for or promise an AI-detector score;
- infer authorship from stylometry;
- add deliberate mistakes, anecdotes, contractions, fragments, random variation, or artificial "burstiness";
- ban individual words, passive voice, hedges, repeated technical terms, long sentences, semicolons, or dashes without context;
- treat stylistic lint as evidence validation;
- copy a voice sample's distinctive phrases or facts; or
- suppress primary, safety, null, negative, contradictory, or adverse evidence to create a smoother narrative.

## Ground-up 1.0 redesign (2026-09-05)

The new architecture and utilities were independently written after inspecting primary Agent Skills/OpenAI/Anthropic documentation and K-Dense Scientific Agent Skills, PaperQA, OpenScholar and STORM. No third-party implementation, manuscript passage, reporting checklist, or benchmark result was copied. Commit-pinned sources, license boundaries, adopted ideas and rejected patterns are documented in [agent research](docs/agent-design-research.md) and [publication standards research](docs/publication-standards-research.md). Prior adaptation attribution above is retained for preserved functionality. Comparator review is not an endorsement or evidence that their performance transfers to this suite.

The redesign uses current ICMJE/EQUATOR/CONSORT/SPIRIT/TRIPOD+AI/STARD-AI/PRISMA/Cochrane/NLM/CRediT/COPE guidance through links and independently written operational rules. Detailed source checklists remain at their official sites, subject to their own terms. Reporting and venue guidance is reverified at task time.

## Prose-register review (2026-11-10)

`references/prose-register.md` was written independently after reviewing the sources below. It adapts general editorial principles to scientific and biomedical prose in original language and with new specimens. No upstream script, pattern list or substantial passage was copied. The review is designed to be done by reading, not by a linter.

### declauding

- Source: https://github.com/oaustegard/claude-skills/tree/main/declauding (release `declauding-v0.13.0`)
- License: MIT.
- Adopted in original language: the state-versus-stage test; flat certainty as the overcorrection of a confident rewrite; compressed syntax ("shorter is not plainer"); reading the whole piece first because staged sentences carry factual errors, with contradictions reported separately; finding the one-sentence point before sentence repair; never inventing specifics; claim-carrying constructions (superlatives, scope, simultaneity, hedge conditions); slot reads by a reader who did not write the draft; the newcomer read after a change; author sample over rules; clusters and reuse over single instances.
- Not adopted: the linters, ranking and review scripts, the Stop hook, phrase lists that misfire on field-standard terms ("robust standard errors", "pivotal trial"), or treatment of discourse markers such as "Notably" as tics.

### avoid-ai-writing

- Source: https://github.com/conorbronsdon/avoid-ai-writing (v3.38.0)
- License: MIT.
- Adopted in original language: the never-inject rule for rewrites; unfilled placeholders and chat-tool citation leaks as defects; vague third-party validation; false concession; invented concept labels and contrast mirrors; the paragraph-reshuffle and cut-half tests as signs that the argument, not the sentences, needs work.
- Not adopted: detector scripts, severity tiers or authorship-evidence framing.

### humanizer_academic

- Source: https://github.com/matsuikentaro1/humanizer_academic (v2.7.0)
- License: MIT (based on blader/humanizer).
- Adopted in original language: `[DATA NEEDED: …]` placeholders with a separate unverified-candidates list; connective preservation; ", and" clause chaining and stacked comparison conditions; subject-verb compatibility for inanimate subjects; ornamental versus functional adverbs; content-free evaluation sentences; not weakening approved author opinions.
- Not adopted: the single-author voice profile, detector-score rationale for rhythm edits, the blanket em-dash ban, or author-specific word swaps.

### skill-deslop

- Source: https://github.com/stephenturner/skill-deslop
- License: MIT.
- Adopted in original language: the enumerated-limitations listicle and the "despite these limitations" pivot.
- Not adopted: examples containing invented statistics, or blanket adverb, triad and passive-voice rules.
