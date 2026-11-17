from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "biomedical-publication-suite"
    / "scripts"
    / "publication_qc.py"
)
SPEC = importlib.util.spec_from_file_location("publication_qc", SCRIPT)
assert SPEC and SPEC.loader
publication_qc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = publication_qc
SPEC.loader.exec_module(publication_qc)


class PublicationQCTests(unittest.TestCase):
    def make_blank_package(self, root: Path) -> None:
        package = root / "manuscript"
        package.mkdir()
        (package / "publication_context.yaml").write_text("causal_language_allowed: false\n", encoding="utf-8")
        (package / "study_facts.md").write_text("# Study Facts\n", encoding="utf-8")
        (package / "open_items.md").write_text("# Open Items\n", encoding="utf-8")
        (package / "narrative_brief.md").write_text("# Narrative Brief\n", encoding="utf-8")
        (package / "manuscript.md").write_text("# Manuscript\n", encoding="utf-8")

    def test_blank_scaffold_is_allowed_at_scaffold_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_blank_package(root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(root),
                    "--stage",
                    "scaffold",
                    "--no-write-report",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_blank_draft_is_rejected_at_draft_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_blank_package(root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(root),
                    "--stage",
                    "draft",
                    "--no-write-report",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("requires substantive content", result.stdout)

    def write_register(self, directory, name, headers, **values):
        with (directory / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerow(values)

    def test_linked_claims_expose_missing_ledgers_and_allow_local_only_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            for external, result_id in ((True, ""), (False, "R2"), (False, "")):
                with self.subTest(external=external, result_id=result_id):
                    self.write_register(package, "claim_register.csv", publication_qc.CLAIM_HEADER,
                                        claim_id="C1", status="supported", source_file="" if external else "results.csv",
                                        support_type="external_citation" if external else "repo_result",
                                        source_id="S1" if external else "", result_id=result_id)
                    findings = publication_qc.check_registers(package, require_claims=True, blocking=True)
                    self.assertEqual(any(f.level == "ERROR" for f in findings), bool(external or result_id))

    def test_local_result_needs_local_provenance_even_with_a_verified_citation(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            self.write_register(package, "literature_register.csv", publication_qc.LITERATURE_HEADER,
                                source_id="S1", verify_status="verified")
            claim = dict(claim_id="C1", status="supported", support_type="repo_result", source_id="S1")
            self.write_register(package, "claim_register.csv", publication_qc.CLAIM_HEADER, **claim)
            issues = publication_qc.check_registers(package, require_claims=True, blocking=True)
            self.assertEqual([item.level for item in issues], ["ERROR"])
            self.write_register(package, "results_ledger.csv", publication_qc.RESULTS_HEADER, result_id="R1")
            self.write_register(package, "claim_register.csv", publication_qc.CLAIM_HEADER, result_id="R1", **claim)
            self.assertEqual(publication_qc.check_registers(package, require_claims=True, blocking=True), [])

    def test_ragged_csv_becomes_a_located_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            path = package / "results_ledger.csv"
            path.write_text(",".join(publication_qc.RESULTS_HEADER) + "\nR1\n")
            findings = publication_qc.check_registers(package, require_claims=False, blocking=False)
            self.assertEqual([(f.level, f.target) for f in findings], [("ERROR", str(path))])

    def test_documented_extraction_quote_exception_remains_an_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            self.write_register(package, "literature_register.csv", publication_qc.LITERATURE_HEADER,
                                source_id="S1", verify_status="verified")
            self.write_register(package, "extraction_ledger.csv",
                                publication_qc.EXTRACTION_HEADER + ["quote_unavailable_reason", "source_version"],
                                extraction_id="E1", source_id="S1", status="verified", field_name="method",
                                field_value="masked review", source_locator="Figure 2",
                                source_version="published PDF", quote_unavailable_reason="Image only",
                                notes="Read the masking label in the figure.")
            findings = publication_qc.check_registers(package, require_claims=False, blocking=True)
            self.assertEqual([f.level for f in findings], ["WARN"])

    def test_single_file_requires_readable_nonempty_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact"
            for contents in (b"PK\x00\xff", b"PK\x00\x00", b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF", b"  "):
                with self.subTest(contents=contents):
                    path.write_bytes(contents)
                    result = subprocess.run([sys.executable, str(SCRIPT), "--file", str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(str(path), result.stdout)
                    self.assertEqual("", result.stderr)

    def test_report_cannot_replace_source_through_a_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_blank_package(root)
            source = root / "manuscript" / "manuscript.md"
            original = source.read_bytes()
            (source.parent / "qc_report.md").symlink_to(source)
            result = subprocess.run([sys.executable, str(SCRIPT), "--repo-root", str(root), "--stage", "scaffold"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("symlink", result.stdout)
            self.assertEqual(source.read_bytes(), original)

    def test_nonsignificance_does_not_establish_equivalence(self) -> None:
        findings = publication_qc.lint_publication_text(
            "The nonsignificant result (P=.12) demonstrated that the treatments were equivalent.",
            "manuscript.md",
            observational=False,
        )
        self.assertTrue(
            any(item.level == "ERROR" and "Nonsignificance" in item.message for item in findings)
        )

    def test_nonsignificance_does_not_establish_similarity(self) -> None:
        findings = publication_qc.lint_publication_text(
            "The groups were similar because the difference was nonsignificant (P=.72).",
            "manuscript.md",
            observational=False,
        )
        self.assertTrue(
            any(item.level == "ERROR" and "Nonsignificance" in item.message for item in findings)
        )

    def test_explicit_non_equivalence_caveat_is_not_flagged(self) -> None:
        findings = publication_qc.lint_publication_text(
            "The estimate was not statistically significant (P = .26); this result did not establish equivalence.",
            "manuscript.md",
            observational=False,
        )
        self.assertFalse(any("Nonsignificance" in item.message for item in findings))

    def test_observational_transitive_outcome_verb_is_flagged(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nEarly mobilization reduced delirium in the adjusted analysis.",
            "manuscript.md",
            observational=True,
        )
        self.assertTrue(
            any(item.level == "ERROR" and "Causal language" in item.message for item in findings)
        )

    def test_present_tense_observational_causal_verb_is_flagged(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nThe exposure increases readmission in the adjusted analysis.",
            "manuscript.md",
            observational=True,
        )
        self.assertTrue(
            any(item.level == "ERROR" and "Causal language" in item.message for item in findings)
        )

    def test_plural_subject_base_causal_verb_is_flagged(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nThe exposures increase readmission risk.",
            "manuscript.md",
            observational=True,
        )
        self.assertTrue(
            any(item.level == "ERROR" and "Causal language" in item.message for item in findings)
        )

    def test_external_randomized_evidence_is_allowed_in_introduction(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Introduction\nA randomized trial showed that early mobilization reduced delirium [1].",
            "manuscript.md",
            observational=True,
        )
        self.assertFalse(any("Causal language" in item.message for item in findings))

    def test_prior_randomized_evidence_is_allowed_in_discussion(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Discussion\nPrior randomized trials found that treatment reduced mortality [1,2].",
            "manuscript.md",
            observational=True,
        )
        self.assertFalse(any("Causal language" in item.message for item in findings))

    def test_current_observational_study_causal_claim_in_discussion_is_error(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Discussion\nOur study showed that early mobilization reduced delirium.",
            "manuscript.md",
            observational=True,
        )
        self.assertTrue(
            any(item.level == "ERROR" and "current study" in item.message for item in findings)
        )

    def test_ambiguous_discussion_causal_claim_is_warning(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Discussion\nEarly mobilization reduced delirium.",
            "manuscript.md",
            observational=True,
        )
        matching = [item for item in findings if "Causal language" in item.message]
        self.assertEqual(1, len(matching))
        self.assertEqual("WARN", matching[0].level)

    def test_intransitive_change_over_time_is_not_automatically_causal(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nScores improved over time in both groups.",
            "manuscript.md",
            observational=True,
        )
        self.assertFalse(any("Causal language" in item.message for item in findings))

    def test_association_with_reduced_outcome_is_not_a_causal_error(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nThe exposure was associated with reduced mortality.",
            "manuscript.md",
            observational=True,
        )
        self.assertFalse(any("Causal language" in item.message for item in findings))

    def test_attributive_reduced_model_is_not_a_causal_error(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nThe reduced model included age and sex.",
            "manuscript.md",
            observational=True,
        )
        self.assertFalse(any("Causal language" in item.message for item in findings))

    def test_reporting_verbs_before_participles_are_not_causal_errors(self) -> None:
        examples = [
            "The cohort has improved survival.",
            "Exposure predicted increased risk.",
            "The analysis found reduced mortality.",
            "The model estimated reduced risk.",
            "Higher exposure corresponded to increased risk.",
        ]
        for example in examples:
            with self.subTest(example=example):
                findings = publication_qc.lint_publication_text(
                    f"## Results\n{example}",
                    "manuscript.md",
                    observational=True,
                )
                self.assertFalse(any("Causal language" in item.message for item in findings))

    def test_single_evidence_tied_hedge_is_not_warned(self) -> None:
        findings = publication_qc.lint_publication_text(
            "## Results\nThe wide interval suggests substantial uncertainty in the estimate.",
            "manuscript.md",
            observational=False,
        )
        self.assertFalse(any("Hedging found" in item.message for item in findings))

    def test_stacked_hedge_remains_warning(self) -> None:
        findings = publication_qc.lint_publication_text(
            "These data may potentially suggest a difference.",
            "manuscript.md",
            observational=False,
        )
        self.assertTrue(any("Stacked hedging" in item.message for item in findings))

    def test_style_signal_is_advisory_info(self) -> None:
        findings = publication_qc.lint_publication_text(
            "The literature shows that the result is important, underscoring its value.",
            "manuscript.md",
            observational=False,
        )
        messages = [item for item in findings if item.level == "INFO"]
        self.assertTrue(any("Vague attribution" in item.message for item in messages))
        self.assertTrue(any("Trailing inference" in item.message for item in messages))

    def test_single_contextual_lexical_signal_is_not_a_warning(self) -> None:
        findings = publication_qc.lint_publication_text(
            "The intervention was evaluated within the local care ecosystem.",
            "manuscript.md",
            observational=False,
        )
        self.assertTrue(any("Candidate formulaic-language" in item.message for item in findings))
        self.assertFalse(any(item.level == "WARN" for item in findings))

    def test_common_citation_styles_satisfy_citation_enforcement(self) -> None:
        examples = [
            "Prior work supports this claim (Smith et al., 2024).",
            r"Prior work supports this claim \cite{smith2024}.",
            "Prior work supports this claim [@smith2024].",
        ]
        for example in examples:
            with self.subTest(example=example):
                findings = publication_qc.check_citations(example, "manuscript.md", True)
                self.assertFalse(any(item.level == "ERROR" for item in findings))

    def test_literal_terms_do_not_create_new_style_failures(self) -> None:
        findings = publication_qc.lint_publication_text(
            "Robust standard errors were used in the pivotal trial. "
            "The exposure was associated with antibody-mediated rejection.",
            "manuscript.md",
            observational=False,
        )
        self.assertFalse(any(item.level == "ERROR" for item in findings))
        self.assertFalse(any("Formulaic or generic prose" in item.message for item in findings))

    def test_reviewer_response_allows_revision_language(self) -> None:
        findings = publication_qc.lint_publication_text(
            "We revised the model and updated the analysis in response to the reviewer.",
            "response_to_reviewers.md",
            observational=False,
        )
        self.assertFalse(any("analysis-history leakage" in item.message for item in findings))

    def test_reviewer_response_still_flags_internal_agent_language(self) -> None:
        findings = publication_qc.lint_publication_text(
            "The agent log and skill output were added to the response.",
            "response_to_reviewers.md",
            observational=False,
        )
        self.assertTrue(any("internal process language" in item.message for item in findings))

    def test_equivalence_design_requires_manual_verification_not_automatic_rejection(self) -> None:
        findings = publication_qc.lint_publication_text(
            "In this equivalence trial, the nonsignificant difference supported equivalence within the prespecified equivalence margin.",
            "manuscript.md",
            observational=False,
        )
        matching = [item for item in findings if "Equivalence or noninferiority" in item.message]
        self.assertEqual(1, len(matching))
        self.assertEqual("WARN", matching[0].level)

    def test_multiline_display_title_is_checked(self) -> None:
        text = (
            "# Display Text\n\n## Figure 1\n\nTitle:\n"
            "This title contains far more than fifteen words because it explains the entire analysis and all of its caveats\n\n"
            "Subtitle:\nCohort description\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "display_text.md"
            path.write_text(text, encoding="utf-8")
            findings = publication_qc.check_display_text(path)
        self.assertTrue(any("title is long" in item.message for item in findings))

    def test_discourse_markers_are_not_flagged(self) -> None:
        text = (
            "Notably, missed visits were more frequent during low staffing (odds ratio 1.42; 95% CI 1.12 to 1.80). "
            "Importantly, the association persisted after adjustment. Moreover, it was similar in both sexes. "
            "However, the estimate changed little when travel time was added."
        )
        findings = publication_qc.lint_publication_text(text, "manuscript.md", observational=True)
        messages = " ".join(item.message for item in findings)
        self.assertNotIn("importance-language", messages)
        self.assertNotIn("formulaic transitions", messages)


if __name__ == "__main__":
    unittest.main()
