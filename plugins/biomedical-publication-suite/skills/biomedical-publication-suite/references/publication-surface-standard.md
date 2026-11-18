# Publication surfaces, displays, and integrity

Publication text must make sense without internal task history. Keep author questions, missing facts, QC output, and drafting choices in control notes. Preserve actual methods rationale, required protocol-change disclosure, reproducibility links/versions, registrations, and reviewer revision descriptions. These are scientific content, not leakage.

## Displays

Default to a short informative title plus only the caption/footnote text needed for standalone interpretation. Tables often need only a title and essential footnotes. Do not require every display to have a subtitle, panel narrative, design rationale, limitations paragraph, model exposition or Results summary.

Titles identify the question or comparison. Axes/column headers carry variables and units. Add population, denominator, timepoint, interval definition, adjustment or abbreviation information only when the display would otherwise be ambiguous. Explain non-obvious encodings; do not describe visible colors, axes or panel geography the reader can already see. Avoid repeating information already clear in the title, labels, table or shared Methods.

For example, an appropriate table title may simply be “Baseline characteristics by exposure status.” A figure caption may be “Adjusted odds of readmission by exposure. Bars indicate 95% confidence intervals.” Add adjustment details or a denominator only when needed and absent from the display/shared legend. These are illustrative forms, not facts or a fixed template. The right length is the shortest that preserves scientific interpretation and verified venue requirements.

Keep interpretive discussion in the manuscript and detailed methods in Methods or a supplement. Use a concise note for any restriction actually necessary to interpret the display; do not turn every caption into a defensive methods report.

Reconcile the display inventory in both directions: every manuscript Figure/Table/Supplement reference resolves to the intended artifact, and every mapped artifact is cited or explicitly excluded from publication. Trace plotted values and table cells to source data/output. Check group/timepoint ordering, axis transforms, interval type, reference category, and exact panel/file cross-references. Counts and suppression thresholds come from actual policy/output; illustrative examples never establish a project's rule. Do not silently alter values for aesthetics.

Use perceptually legible labels, accessible contrasts and encodings beyond color alone, honest scales, and explicit truncation/transformation. Define graphical summaries as conceptual or data-based. A generated illustration must not masquerade as microscopy, radiology, experimental evidence, or measured results. Preserve image provenance and verify current journal image/AI rules. Respect licenses and permissions.

For final visual or formatted files, render and inspect all affected pages/slides/panels for clipping, overlap, resolution, labels, reference fields, and reading order. If rendering is unavailable, distinguish content verification from unperformed visual validation. Use appropriate document/figure tools; drafting a caption does not mean the figure was changed.

## Figure design

Begin with the question a reader should be able to answer from the figure, and hold the result to the standard of the target journal's best figures: a reader should not be able to tell it from professionally produced artwork. The [figure house style](figure-house-style.md) is the default starting point, with print-scale typography, a restrained palette, a reusable ggplot2 theme, and working conventions for forest plots, trajectories, heat maps and diagrams. Use the parts that help this figure. An established manuscript design, the journal's artwork instructions or a clearer representation of the data takes precedence.

Consider what the reader sees first. Give the main comparison enough space and contrast. Direct labels can save a trip to a legend, while a shared key can clear space in a crowded panel. If readers must subtract two curves to see the central contrast, a directly estimated difference with uncertainty may earn its own panel. If a table already communicates a small set of results clearly, a second display may add little.

Give each figure one job. A figure that shows how groups were defined shows what defines them; validation, stability, and reproducibility belong in the text or a table. A small table of a few numbers rarely earns a figure, and two figures that answer the same question should become one. Every display choice needs a reason a reader would accept, among them the measure plotted, the chart form, offsets between groups, end labels, and whether panels sit side by side or stacked. Weigh the alternatives for this figure and tell the author why one was chosen.

When asked to choose a layout or add information such as P values, consider the tradeoff for this particular figure and recommend one option. For a venue-specific choice, distinguish published examples from verified submission requirements.

## Tables

The main table should let the reader see the cohort and the contrast the paper is about; add a column or a second main table when it carries a result the argument depends on, not for completeness. In a baseline table of a randomized trial, significance tests of baseline differences are discouraged (CONSORT); in observational comparisons, standardized differences or P values follow the journal's custom, and the choice should be stated to the author as a recommendation. Footnotes define abbreviations and anything a reader cannot infer; they do not narrate methods.

Lay a table out for reading. Use horizontal rules only, at the top, under the column heads and at the bottom. Put each group size under its bold group name in the header, indent subcategories under their variable, and right-align numbers so the digits line up under a centered head. Make columns wide enough that numbers do not wrap, keep range punctuation consistent with the journal, and give every measure its unit. Order rows by the framework or logic the paper uses, and when the paper defines groups, mark with footnote letters the variables that defined them. Whether to add tests of differences between groups depends on the design and the journal; recommend one option.

## Supplement economy

A supplement is not an archive of everything that was run. Many good papers have a short one. Start from the central claim and include what a reader needs to evaluate or reproduce it: the methods detail behind the main analysis, the sensitivity analyses that answer the first objections, and whatever the protocol, reporting guideline or venue requires. Give each item a main-text pointer; some venues also require checklists or files that have no in-text callout. Leave out analyses that are superseded, peripheral or redundant with another item. They can be added if a reviewer asks, and the paper should not promise access the authors have not agreed to give. When pruning, rethink the set from the central claim outward instead of deleting item by item.

Leanness never removes evidence that changes the inference. Keep material contrary findings, explain them, and name the population or model difference behind an apparent discrepancy with the main result. An item that only looks contradictory because its display is unclear needs a better display or a sentence of explanation.

## Missing facts and sensitive content

Omit optional unsupported details. For a provisional draft, use an essential visible blank only when it helps the author complete the artifact, and explain the gap outside publication prose. Submission artifacts cannot retain unresolved blanks or unsupported declarations. When the authors confirm that an optional detail is unavailable, leave it out without a placeholder or a hint, and list the omission for them. When the detail is one a reader needs to interpret a result, such as how an outcome was ascertained, say in a clause that it was not recorded. A reporting-checklist item left incomplete is marked as not available, with the reason, on the checklist itself. Administrative statements the authors already approved, such as ethics approval, contributions, and funding, are reused unless the authors say something changed, adapted to the elements the new journal requires and rechecked when the authors, funding, or scope change.

Check direct and indirect patient identifiers, especially rare cases and images. Do not invent dates to de-identify an account. Generalize only when scientifically appropriate and flag any effect on interpretation. Supplied consent or author statements do not authorize arbitrary external uploads. See [evidence control](evidence-and-claim-control.md).
