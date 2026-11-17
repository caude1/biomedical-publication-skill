from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "biomedical-publication-suite"
    / "scripts"
    / "revision_invariants.py"
)
SPEC = importlib.util.spec_from_file_location("revision_invariants", SCRIPT)
assert SPEC and SPEC.loader
revision_invariants = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = revision_invariants
SPEC.loader.exec_module(revision_invariants)


class RevisionInvariantTests(unittest.TestCase):
    def test_preserved_scientific_anchors_pass(self) -> None:
        source = (
            "Burnout was associated with intention to leave among 1,204 nurses "
            "(adjusted OR 2.10, 95% CI 1.72-2.57; P=.08) [12]. "
            "Events occurred in 62 of 200 participants (31%) over 12 weeks."
        )
        revised = (
            "Among 1,204 nurses, burnout was associated with intention to leave "
            "(adjusted OR 2.10, 95% CI 1.72-2.57; P=.08) [12]. "
            "Over 12 weeks, events occurred in 62 of 200 participants (31%)."
        )
        report = revision_invariants.compare_texts(source, revised)
        self.assertEqual([], report["protected_differences"])
        self.assertEqual([], report["semantic_risk_differences"])
        self.assertEqual(0, revision_invariants.exit_code(report))

    def test_swapping_arm_values_in_a_table_reports_actual_labels_and_locations(self) -> None:
        original = "| Outcome | Standard care | Intervention |\n| --- | ---: | ---: |\n| Readmission | 13 | 27 |\n"
        changed = original.replace("13 | 27", "27 | 13")
        report = revision_invariants.compare_texts(original, changed)
        differences = report["protected_differences"]
        self.assertEqual({item.category for item in differences}, {"labeled_table_numbers"})
        removed = next(item for item in differences if item.value == "Readmission | Standard care | 13")
        self.assertEqual((removed.source_count, removed.revised_count), (1, 0))
        self.assertEqual((removed.source_locations[0].line, removed.source_locations[0].column), (3, 17))

    def test_unsupported_row_does_not_hide_a_later_value_swap(self):
        for label in ("Language `R`", r"Readmission \| transfer"):
            with self.subTest(label=label):
                source = f"| Outcome | Arm A | Arm B |\n| --- | --- | --- |\n| {label} | 5 | 7 |\n| Death | 1 | 3 |\n"
                revised = source.replace("Death | 1 | 3", "Death | 3 | 1")
                report = revision_invariants.compare_texts(source, revised)
                changed = {d.value for d in report["protected_differences"] if d.category == "labeled_table_numbers"}
                self.assertEqual(changed, {"Death | Arm A | 1", "Death | Arm A | 3", "Death | Arm B | 1", "Death | Arm B | 3"})

    def test_ascii_pdf_cannot_pass_as_comparable_publication_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opaque"
            path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF")
            with self.assertRaisesRegex(ValueError, "export UTF-8"):
                revision_invariants.read_text(path)

    def test_reordering_intact_table_rows_and_columns_preserves_anchors(self) -> None:
        original = "Outcome | Treatment | Control\n--- | --- | ---\nDeath | 2 | 7\nReadmission | 9 | 14\n"
        reordered = "Outcome | Control | Treatment\n--- | --- | ---\nReadmission | 14 | 9\nDeath | 7 | 2\n"
        self.assertEqual(revision_invariants.exit_code(revision_invariants.compare_texts(original, reordered)), 0)

    def test_table_inequality_swaps_even_when_all_numbers_survive(self) -> None:
        original = "| Test | Arm A | Arm B |\n| --- | --- | --- |\n| P | <=0.05 | >0.05 |"
        revised = original.replace("<=0.05 | >0.05", ">0.05 | <=0.05")
        report = revision_invariants.compare_texts(original, revised)
        self.assertEqual({d.category for d in report["protected_differences"]}, {"labeled_table_numbers"})

    def test_changed_sign_is_protected_difference(self) -> None:
        report = revision_invariants.compare_texts(
            "The risk difference was -8% (95% CI -17% to 1%).",
            "The risk difference was 8% (95% CI -17% to 1%).",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("numbers", categories)
        self.assertEqual(1, revision_invariants.exit_code(report))

    def test_repeated_values_use_multiset_counts(self) -> None:
        report = revision_invariants.compare_texts(
            "Ten participants received 10 mg; another 10 received placebo.",
            "Ten participants received 10 mg; another group received placebo.",
        )
        number_differences = [
            item for item in report["protected_differences"] if item.category == "numbers"
        ]
        self.assertTrue(any(item.value == "10" and item.source_count == 2 for item in number_differences))

    def test_citations_equations_and_cross_references_are_protected(self) -> None:
        source = r"The model $y = 2x + 1$ is shown in Figure 2 \cite{smith2025}."
        revised = r"Figure 3 shows the model $y = 2x + 1$ \cite{jones2025}."
        report = revision_invariants.compare_texts(source, revised)
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("citations_and_identifiers", categories)
        self.assertIn("cross_references", categories)
        self.assertNotIn("equations", categories)

    def test_semantic_marker_change_returns_manual_review_code(self) -> None:
        report = revision_invariants.compare_texts(
            "The exposure may be associated with the outcome.",
            "The exposure caused the outcome.",
        )
        self.assertEqual([], report["protected_differences"])
        categories = {item.category for item in report["semantic_risk_differences"]}
        self.assertIn("modality", categories)
        self.assertIn("causal_language", categories)
        self.assertEqual(2, revision_invariants.exit_code(report))

    def test_citation_numbers_are_not_double_counted_as_results(self) -> None:
        report = revision_invariants.compare_texts(
            "The association was reported previously [12].",
            "The association was reported previously [13].",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertEqual({"citations_and_identifiers"}, categories)

    def test_narrative_author_year_citation_is_protected(self) -> None:
        report = revision_invariants.compare_texts(
            "Smith et al. (2024) reported the association.",
            "Jones et al. (2024) reported the association.",
        )
        citation_differences = [
            item
            for item in report["protected_differences"]
            if item.category == "citations_and_identifiers"
        ]
        self.assertTrue(citation_differences)

    def test_multi_author_parenthetical_citation_is_protected(self) -> None:
        report = revision_invariants.compare_texts(
            "The association was reported previously (Smith & Jones, 2024).",
            "The association was reported previously (Smith & Jones, 2025).",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertEqual({"citations_and_identifiers"}, categories)

    def test_unit_change_is_reported(self) -> None:
        report = revision_invariants.compare_texts(
            "Participants received 5 mg daily for 7 days.",
            "Participants received 5 g daily for 7 days.",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("number_unit_pairs", categories)

    def test_common_biomedical_compound_unit_changes_are_reported(self) -> None:
        cases = [
            ("10 IU", "10 U"),
            ("20 mEq", "20 mmol"),
            ("10 cells/µL", "10 cells/mL"),
            ("200 kcal", "200 kJ"),
            ("5 mg/kg/day", "5 mg/kg/h"),
            ("2 L/min", "2 mL/min"),
        ]
        for source, revised in cases:
            with self.subTest(source=source, revised=revised):
                report = revision_invariants.compare_texts(source, revised)
                categories = {item.category for item in report["protected_differences"]}
                self.assertIn("number_unit_pairs", categories)

    def test_inequality_direction_change_is_reported(self) -> None:
        report = revision_invariants.compare_texts(
            "Eligibility required age >65 years and P<=.05.",
            "Eligibility required age <65 years and P>=.05.",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("inequalities", categories)
        self.assertIn("statistical_spans", categories)

    def test_reagent_version_and_doi_are_protected(self) -> None:
        report = revision_invariants.compare_texts(
            "Reagent L3000001 was analyzed with software v2.4.1 (doi:10.1000/example.1).",
            "Reagent L3000002 was analyzed with software v2.4.2 (doi:10.1000/example.2).",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("citations_and_identifiers", categories)
        self.assertIn("registry_and_version_identifiers", categories)

    def test_overlapping_identifier_patterns_are_not_double_counted(self) -> None:
        report = revision_invariants.compare_texts(
            "The protocol was registered as NCT01234567.",
            "The protocol was registered as NCT01234568.",
        )
        nct_differences = [
            item
            for item in report["protected_differences"]
            if item.category == "registry_and_version_identifiers"
            and item.value.startswith("NCT")
        ]
        self.assertEqual(2, len(nct_differences))
        self.assertTrue(all(max(item.source_count, item.revised_count) == 1 for item in nct_differences))

    def test_terminal_doi_punctuation_is_not_part_of_identifier(self) -> None:
        report = revision_invariants.compare_texts(
            "The report is available at 10.1000/example.1.",
            "The report is available at 10.1000/example.1; see the supplement.",
        )
        self.assertFalse(
            any(
                item.category == "citations_and_identifiers"
                for item in report["protected_differences"]
            )
        )

    def test_unmatched_parenthesis_around_doi_is_not_part_of_identifier(self) -> None:
        report = revision_invariants.compare_texts(
            "The report is available (doi:10.1000/example.1).",
            "The report is available at 10.1000/example.1.",
        )
        self.assertFalse(
            any(
                item.category == "citations_and_identifiers"
                for item in report["protected_differences"]
            )
        )

    def test_contracted_negation_change_requires_manual_review(self) -> None:
        report = revision_invariants.compare_texts(
            "The estimate wasn't precise.",
            "The estimate was precise.",
        )
        categories = {item.category for item in report["semantic_risk_differences"]}
        self.assertIn("negation", categories)

    def test_sentence_final_number_forms_are_fully_preserved(self) -> None:
        text = "Counts were 10. The estimate was 1.5. Rates were 10% and 1.5%."
        numbers, _ = revision_invariants.inventory(text)["numbers"]
        self.assertEqual(1, numbers["10"])
        self.assertEqual(1, numbers["1.5"])
        self.assertEqual(1, numbers["10%"])
        self.assertEqual(1, numbers["1.5%"])

    def test_changed_sentence_final_decimal_is_detected(self) -> None:
        report = revision_invariants.compare_texts(
            "The estimate was 1.5.",
            "The estimate was 1.6.",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("numbers", categories)

    def test_plural_and_range_cross_references_are_protected(self) -> None:
        report = revision_invariants.compare_texts(
            "Figures 2 and 3 and Figure 4A–C show the results.",
            "Figures 2 and 4 and Figure 4A–D show the results.",
        )
        categories = {item.category for item in report["protected_differences"]}
        self.assertIn("cross_references", categories)

    def test_terminal_cross_reference_punctuation_is_not_protected_content(self) -> None:
        report = revision_invariants.compare_texts(
            "The result is shown in Figure 2A–C.",
            "The result is shown in Figure 2A–C; see the supplement.",
        )
        self.assertFalse(
            any(
                item.category == "cross_references"
                for item in report["protected_differences"]
            )
        )

    def test_literal_scientific_style_is_not_a_semantic_change(self) -> None:
        text = (
            "Robust standard errors were used in the pivotal trial. "
            "The exposure was associated with antibody-mediated rejection—"
            "a prespecified secondary outcome."
        )
        report = revision_invariants.compare_texts(text, text)
        self.assertEqual(0, revision_invariants.exit_code(report))


if __name__ == "__main__":
    unittest.main()
