# Multi-round cold reads

A cold read gives a near-final artifact to readers who have never seen the project and asks what they think it says. The person who wrote a draft knows what it means and cannot see where it fails to say so. Run this workflow by default before handing over a near-final manuscript, figure, table set, supplement, cover letter or reviewer response, and whenever the author asks for fresh eyes. An artifact is near-final when it is about to be presented as a candidate for the paper, which includes a single new figure. A paragraph polish usually needs only a direct editorial read. Honor an explicit request for solo work, a fixed review budget, or review without edits.

The coordinating agent owns the scientific decisions and the final files. Readers supply interpretations and suggestions. The coordinator decides what to do with them.

## Prepare the reader's copy

Freeze a read-only version of the artifact as the audience will encounter it. Share a manuscript with its figures and legends when that is the reading experience. Give a figure-first reader the rendered figure and its actual caption, at intended print or screen size. A reviewer of a table can receive the table and footnotes alone. For correspondence, identify the recipient's role and what they already know. Use versioned copies or equivalent stable identifiers so observations locate the right draft.

Put the reader's copy in its own folder, apart from the analysis, earlier drafts and notes, and point each reader at that folder only. A reader who can browse the project is no longer cold.

## Use fresh subagents

Each reader is a new subagent with no memory of the conversation. In Claude Code, start an ordinary agent with the Agent tool; a fork inherits the whole conversation and cannot serve. In Codex and other hosts, use whatever starts a worker with a clean context. Start all readers of a round in one step so they run in parallel and cannot see one another's answers.

Supply only the artifact, the audience, the assignment and any viewing instructions. Withhold the intended message, earlier reviews, the change list and author deliberations. Reserve analytic sources for an evidence reviewer or for adjudication after first impressions. A figure reader must open the image itself. A text description of a figure, or text extracted from a PDF, tests the description and says nothing about the figure.

Use authorized processing paths for confidential or embargoed work. Subagents of the same host are normally the same path as the coordinator. A service that cannot accept the material is unavailable for that assignment.

## First round: independent interpretations

Give at least two readers different assignments, and three or four for a full manuscript. Choose perspectives that could reasonably disagree about this artifact.

| Perspective | What to ask |
|---|---|
| Clinical or field reader | What question does the study answer, for whom, against which comparator, and how would this information change your understanding? Which sentence first made that clear? |
| Methods or statistical reader | Recover the design, population, time origin, estimand or measured contrast and main inference. Identify any stronger reading the wording invites. If verifying a value, request the relevant source separately. |
| Figure-first reader | Open the figure before reading anything else. Say what one mark, interval or percentage represents, compare two groups, and state the takeaway. Point to the label or visual choice behind each interpretation. Then say whether it looks like a figure from the target journal and what, if anything, looks crowded, misaligned, clipped or decorative. |
| Reader with two minutes | Read only the title, abstract, figures and conclusion. State what the paper found, how strong the evidence is and what should change because of it. Whatever cannot be recovered from those parts is missing for most readers. |
| Journal editor or outside specialist | Explain the contribution to the intended readership, where the reasoning becomes difficult to follow, and which paragraph or panel earns less space than it receives. |
| Register reader | With the [prose register](prose-register.md) guide in hand, mark sentences that perform (a reveal, an aphorism, a narrator's summary), run loose, or carry too many contrasts to parse, and any that sound unlike the journal. Quote each one and say what it should state instead. |
| Newcomer after a revision | Read the current version only. Mark every phrase that leans on an earlier version, an abandoned analysis or a discussion the reader never saw. |
| First-time clinical reader | Read as a clinician who knows the field but not this project or, for a methods-heavy paper, this method. Mark each place where you stopped to ask what a phrase means, why the authors did something, or what a term refers to; each number or rule that looks arbitrary; and each sentence that defends against a concern you would not have had. A procedural statement this reader flags is confirmed by the methods reader before any cut. See [reader clarity](reader-friction.md). |
| Reader of a supplement, response, or handoff | Try to complete the intended task, such as locating a sensitivity result, verifying a claimed revision, or understanding what decision a coauthor needs to make. |

Use a short assignment such as the following, adapted to the artifact.

> Read this version independently as the specified audience. Open only the files in this folder. Tell me in your own words what you think it shows and what you used to reach that interpretation. Locate any passage, panel or label that could lead a reader astray, explain the consequence, and offer a concrete improvement where you have one. Add any suggestion that would make it stronger or clearer for this audience. List what you actually opened and anything you could not inspect. Return feedback only; do not edit any file.

Read the independent responses before sharing any feedback between readers. An accurate paraphrase gives more information about comprehension than a general endorsement. A reader can report that an artifact is clear. Avoid requiring a quota of criticisms.

## Adjudicate and revise

Classify each material observation by what would change for the reader. A numerical error, incorrect causal inference or mislabeled axis takes priority over a stylistic preference. Check reported errors against the source output, protocol, citation or journal instructions. A reviewer may correctly identify confusion and propose a scientifically wrong fix. Resolve the confusion while retaining the correct meaning. A single documented error warrants correction regardless of how many readers missed it.

The coordinator chooses which suggestions to use, adapt or decline. Readers tend to ask for more: another caveat, another analysis, another paragraph of background. Adopt what makes the paper more correct or easier to understand. Decline what would only make it longer, more hedged or more defensive, and do not add a caveat simply because a reader imagined an objection. A misreading, on the other hand, is evidence even when the text is technically correct: if one careful reader took a percentage to have the wrong denominator, other readers will too.

Keep a short working note with the version, location, observed misreading or suggestion, evidence, decision and artifact changed. Preserve the author's approved wording and design choices where they still serve the study. For review-only requests, leave the source intact and make the proposed remedy clear. If a revised candidate is needed for a requested second round, use a separately identified working copy within the authorized scope; otherwise run the next read independently on the same version and report the scope.

## Second round: read the delivered version afresh

Apply accepted changes, update dependent text, figures, captions and cross-references, and render the new version. Assign **new** readers from at least two relevant perspectives. Give them the revised artifact without the prior interpretations or the fixes. For example, one reader can start from the figure and another from the abstract. After collecting their unaided interpretations, the coordinator compares them with the study evidence and checks whether the first-round misunderstandings recur. The coordinator can separately request a targeted verification of an issue once the blind read is complete.

If a substantive issue persists, revise and repeat the relevant cold read with a fresh reader. Stop when the material interpretations agree with the evidence and remaining suggestions are preferential, or when evidence, authorization or resources prevent resolution. Two rounds are the usual number. Simple verified copyedits after the final read need no further panel. A changed denominator, conclusion, panel structure or other material change needs a new read of the affected version before reporting it reviewed. Continue independent in-scope work if one reader or tool is unavailable.

## Report to the author

Deliver the revised artifact first. Then say in a few lines how many rounds ran, which versions and perspectives were read, what changed as a result and what remains unresolved. List the suggestions that were declined and would change the paper's direction, emphasis or length, each with a one-line reason, so the author can overrule the decision. Minor declined preferences need no list.

A text-only reader cannot verify a figure's visual legibility. A returning reader can verify a correction but cannot supply a fresh first impression. If fresh isolated readers or visual access are unavailable, distinguish direct editorial inspection from independent review. Simulated readers provide editorial feedback. They cannot supply author approvals, independent human screening or journal peer review.
