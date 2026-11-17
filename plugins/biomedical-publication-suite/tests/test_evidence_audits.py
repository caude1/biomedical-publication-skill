"""Offline regression fixtures for evidence gates, provenance failures, and statistical edge cases."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/biomedical-publication-suite/scripts"

def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded

citation = module("citation_audit")
extraction = module("extraction_audit")
results = module("results_audit")

class EvidenceAudits(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.literature = dict(source_id="S1", verify_status="verified", publication_status="current", status_source="https://publisher.example/article", status_checked_at="2026-01-01", source_version="version of record")
        self.claim = dict(artifact="manuscript.md", claim_id="C1", support_type="external_citation", source_id="S1", status="supported", content_status="supported", support_role="direct", source_locator="Results, paragraph 2", checked_by="reviewer-A", checked_at="2026-01-01", claim_text="The estimate was 1.2.")
        self.extracted = dict(extraction_id="E1", source_id="S1", field_group="results", field_name="hazard ratio", field_value="1.2", source_locator="Table 2", source_quote="Hazard ratio 1.2", status="verified", denominator="200 patients", unit="ratio", timepoint="1 year", comparison="A versus B")
        self.result = dict(result_id="R1", estimate_type="HR", estimate="1.2", ci_lower="0.9", ci_upper="1.6", p_value=".20", n_total="200", n_events="20", source_file="results.csv", source_locator="row 2", outcome_name="readmission", population="analytic cohort")

    def csv(self, name, rows, headers=None):
        path = self.root / name
        headers = headers or list(dict.fromkeys(key for row in rows for key in row))
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def cite(self, claim=None, literature=None, **kwargs):
        claims = self.csv("claims.csv", [claim or self.claim])
        sources = self.csv("sources.csv", [literature or self.literature])
        return citation.audit(claims, sources, **kwargs)

    def errors(self, findings):
        return [f for f in findings if f.level == "ERROR"]

    def test_strict_supported_claim_passes(self):
        self.assertEqual(self.cite(strict=True), [])

    def test_identity_alone_does_not_establish_support(self):
        claim = dict(self.claim, content_status="")
        self.assertTrue(self.errors(self.cite(claim, strict=True)))
        self.assertEqual(self.cite(claim), [])

    def test_contradicted_claim_fails_even_draft(self):
        self.assertTrue(self.errors(self.cite(dict(self.claim, content_status="contradicted"))))

    def test_duplicate_sources_cannot_be_overwritten(self):
        sources = self.csv("sources.csv", [dict(self.literature, verify_status="quarantine"), self.literature])
        claims = self.csv("claims.csv", [self.claim])
        findings = citation.audit(claims, sources)
        self.assertTrue(any("Duplicate" in f.message for f in findings))
        self.assertTrue(any("not identity verified" in f.message for f in findings))

    def test_blank_duplicate_claim_ids_fail(self):
        sources = self.csv("sources.csv", [self.literature])
        claims = self.csv("claims.csv", [self.claim, self.claim, dict(self.claim, claim_id="")])
        self.assertEqual(len(self.errors(citation.audit(claims, sources))), 2)

    def test_unknown_status_fails(self):
        self.assertTrue(self.errors(self.cite(literature=dict(self.literature, verify_status="probably_real"))))

    def test_retracted_source_not_affirmative_evidence(self):
        self.assertTrue(self.errors(self.cite(literature=dict(self.literature, publication_status="retracted"), strict=True)))

    def test_retraction_can_be_discussed_as_notice(self):
        self.assertEqual(self.cite(dict(self.claim, support_role="retraction_notice"), dict(self.literature, publication_status="retracted"), strict=True), [])

    def test_withdrawn_source_cannot_affirm_a_finding_in_a_draft(self):
        findings = self.cite(literature=dict(self.literature, publication_status="withdrawn"))
        self.assertTrue(self.errors(findings))

    def test_claim_and_extraction_must_refer_to_the_version_reviewed(self):
        claim = dict(self.claim, source_version="Corrected PDF", extraction_id="E1")
        source = dict(self.literature, source_version="corrected PDF", publication_status="corrected")
        old = self.csv("extraction.csv", [dict(self.extracted, source_version="Original PDF")])
        self.assertTrue(self.errors(self.cite(claim, source, strict=True, extraction_ledger=old)))
        current = self.csv("extraction.csv", [dict(self.extracted, source_version="Corrected PDF")])
        self.assertEqual(self.cite(claim, source, strict=True, extraction_ledger=current), [])

    def test_family_id_cannot_substitute_for_a_missing_report_id(self):
        source = dict(self.literature, source_id="", study_id="S1")
        self.assertTrue(self.errors(self.cite(literature=source, strict=True)))
        del source["source_id"]
        self.assertEqual(self.cite(literature=source, strict=True), [])

    def test_strict_mode_rejects_empty_and_misclassified_claims(self):
        claims = self.csv("claims.csv", [], headers=["claim_id"])
        self.assertTrue(self.errors(citation.audit(claims, self.root / "absent.csv", strict=True)))
        typo = dict(self.claim, support_type="externl_citation", source_id="", source_file="copied.docx")
        self.assertTrue(self.errors(self.cite(typo, strict=True)))

    def test_status_check_and_locator_required(self):
        self.assertTrue(self.errors(self.cite(dict(self.claim, source_locator=""), dict(self.literature, status_source=""), strict=True)))

    def test_future_dates_rejected(self):
        self.assertTrue(self.errors(self.cite(dict(self.claim, checked_at="2999-01-01"), strict=True)))

    def test_orphan_extraction_and_result_rejected(self):
        extracts = self.csv("extraction.csv", [self.extracted])
        result_file = self.csv("results.csv", [self.result])
        findings = self.cite(dict(self.claim, extraction_id="E2", result_id="R2"), extraction_ledger=extracts, results_ledger=result_file)
        self.assertEqual(len(self.errors(findings)), 2)

    def test_extraction_source_mismatch_rejected(self):
        extracts = self.csv("extraction.csv", [dict(self.extracted, source_id="S2")])
        self.assertTrue(self.errors(self.cite(dict(self.claim, extraction_id="E1"), extraction_ledger=extracts)))

    def test_missing_pointer_ledger_rejected_in_strict_mode(self):
        self.assertTrue(self.errors(self.cite(dict(self.claim, result_id="R1"), strict=True)))

    def test_missing_header_and_ragged_csv_fail_closed(self):
        for contents in ("source_id,source_id\nS1,S1\n", "source_id,verify_status\nS1,verified,extra\n", "source_id,verify_status\nS1\n"):
            path = self.root / "bad.csv"
            path.write_text(contents)
            claims = self.csv("claims.csv", [self.claim])
            self.assertTrue(self.errors(citation.audit(claims, path)))

    def test_no_literature_file_required_for_local_claims(self):
        claims = self.csv("claims.csv", [dict(claim_id="C1", claim_text="Readmission hazard ratio was 1.2.", artifact="manuscript.md", support_type="repo_result", status="supported", source_file="results.csv", source_locator="row 2", result_id="R1")])
        result_file = self.csv("results.csv", [self.result])
        self.assertEqual(citation.audit(claims, self.root / "absent.csv", strict=True, results_ledger=result_file), [])

    def test_external_reference_cannot_stand_in_for_repository_evidence(self):
        for kind in ("repo_result", "repo_method", "repo_documentation"):
            with self.subTest(kind=kind):
                linked = dict(self.claim, support_type=kind)
                self.assertTrue(self.errors(self.cite(linked, strict=True)))
                self.assertEqual(self.cite(linked), [])
                grounded = dict(linked, source_file="analysis.md", source_locator="Section 2; S1 Table 3")
                self.assertEqual(self.cite(grounded, strict=True), [])
                self.assertTrue(self.errors(self.cite(dict(grounded, source_locator=""), strict=True)))
                self.assertTrue(self.errors(self.cite(grounded, dict(self.literature, verify_status="quarantine"), strict=True)))

    def test_direct_result_locator_is_sufficient_without_an_optional_ledger(self):
        local = dict(self.claim, support_type="repo_result", source_id="", source_file="model.csv", source_locator="readmission, adjusted model")
        self.assertEqual(self.cite(local, strict=True), [])
        self.assertTrue(self.errors(self.cite(dict(local, result_id="R1"), strict=True)))

    def test_verifier_failure_states_are_valid_but_not_citable(self):
        for state in ("unresolved", "network_error"):
            findings = self.cite(literature=dict(self.literature, verify_status=state))
            self.assertTrue(any("not identity verified" in f.message for f in findings))
            self.assertFalse(any("Invalid or blank verify_status" in f.message for f in findings))

    def test_metadata_signal_alone_does_not_clear_publication_status(self):
        self.assertTrue(self.errors(self.cite(literature=dict(self.literature, publication_status="no_signal_in_checked_metadata"), strict=True)))
        self.assertEqual(self.cite(literature=dict(self.literature, publication_status="no_notice_found"), strict=True), [])

    def test_malformed_date_suffix_rejected(self):
        self.assertTrue(self.errors(self.cite(dict(self.claim, checked_at="2026-01-01invalid"), strict=True)))

    def test_grounded_extraction_passes(self):
        path = self.csv("extraction.csv", [self.extracted])
        self.assertEqual(extraction.audit(path, strict=True), [])

    def test_missingness_does_not_become_zero(self):
        path = self.csv("extraction.csv", [dict(self.extracted, status="not_reported", field_value="0")])
        self.assertTrue(self.errors(extraction.audit(path)))
        path = self.csv("extraction.csv", [dict(self.extracted, status="not_reported", field_value="", source_quote="")])
        self.assertEqual(extraction.audit(path), [])

    def test_unanchored_value_fails(self):
        path = self.csv("extraction.csv", [dict(self.extracted, source_quote="", source_locator="")])
        self.assertEqual(len(self.errors(extraction.audit(path))), 2)

    def test_documented_unavailable_quote_is_manual_warning(self):
        row = dict(self.extracted, source_quote="", quote_unavailable_reason="Scanned table; exact text extraction unavailable", source_version="publisher PDF, Table 2", notes="Checked the rendered PDF table and column headings")
        path = self.csv("extraction.csv", [row])
        findings = extraction.audit(path, strict=True)
        self.assertEqual(self.errors(findings), [])
        self.assertTrue(any(f.level == "WARN" for f in findings))
        path = self.csv("extraction.csv", [dict(row, source_version="")])
        self.assertTrue(self.errors(extraction.audit(path)))

    def test_derived_values_require_reproducible_derivation(self):
        row = dict(self.extracted, value_origin="derived")
        path = self.csv("extraction.csv", [row])
        self.assertEqual(self.errors(extraction.audit(path)), [])
        self.assertTrue(self.errors(extraction.audit(path, strict=True)))
        path = self.csv("extraction.csv", [dict(row, derivation_source="analysis/derive.py:42; outputs/derived.csv:row 2")])
        self.assertEqual(extraction.audit(path, strict=True), [])

    def test_invalid_value_origin_rejected(self):
        path = self.csv("extraction.csv", [dict(self.extracted, value_origin="estimated_from_memory")])
        self.assertTrue(self.errors(extraction.audit(path)))

    def test_strict_claim_must_name_artifact_and_claim(self):
        self.assertTrue(self.errors(self.cite(dict(self.claim, artifact="", claim_text=""), strict=True)))

    def test_extraction_blank_id_and_status_not_skipped_for_missing_values(self):
        path = self.csv("extraction.csv", [dict(self.extracted, extraction_id="", field_value="", status="")])
        self.assertTrue(self.errors(extraction.audit(path)))

    def test_duplicate_extraction_fails(self):
        path = self.csv("extraction.csv", [self.extracted, self.extracted])
        self.assertTrue(self.errors(extraction.audit(path)))

    def test_extraction_cross_register_orphan_fails(self):
        path = self.csv("extraction.csv", [dict(self.extracted, source_id="S2")])
        literature = self.csv("sources.csv", [self.literature])
        self.assertTrue(self.errors(extraction.audit(path, literature_register=literature)))

    def test_partial_extract_allowed_draft_but_blocks_strict(self):
        path = self.csv("extraction.csv", [dict(self.extracted, status="partial")])
        self.assertEqual(self.errors(extraction.audit(path)), [])
        self.assertTrue(self.errors(extraction.audit(path, strict=True)))

    def test_empty_extraction_scaffold_passes(self):
        path = self.csv("empty.csv", [], extraction.REQUIRED_COLUMNS)
        self.assertEqual(extraction.audit(path), [])

    def test_valid_result_with_inequality_p_passes(self):
        for p in ("<.001", "P ≤ 0.05", "1e-8", "0.2", "1"):
            path = self.csv("results.csv", [dict(self.result, p_value=p)])
            self.assertEqual(results.audit(path, strict=True), [], p)

    def test_invalid_p_values_fail(self):
        for p in ("-0.1", "1.2", "<0", ">1", "NaN", "inf", "P<.03 rubbish"):
            path = self.csv("results.csv", [dict(self.result, p_value=p)])
            self.assertTrue(self.errors(results.audit(path)), p)

    def test_reversed_ci_and_negative_ratio_fail(self):
        path = self.csv("results.csv", [dict(self.result, estimate="-1", ci_lower="1.5", ci_upper="1.1")])
        self.assertEqual(len(self.errors(results.audit(path))), 2)

    def test_zero_risk_ratio_and_exact_unbounded_endpoint(self):
        row = dict(self.result, estimate_type="RR", estimate="0", ci_lower="0", ci_upper="+∞")
        findings = results.audit(self.csv("results.csv", [row]), strict=True)
        self.assertEqual(self.errors(findings), [])
        self.assertTrue(any("zero" in f.message for f in findings))
        unbounded = self.csv("results.csv", [dict(row, estimate="Inf")])
        self.assertEqual([f.level for f in results.audit(unbounded)], ["WARN"])
        for field, value in (("estimate", "-inf"), ("n_total", "inf"), ("ci_upper", "-∞"), ("ci_lower", "+infinity")):
            with self.subTest(field=field):
                path = self.csv("results.csv", [dict(row, **{field: value})])
                self.assertTrue(self.errors(results.audit(path)))

    def test_approximate_bounds_differ_from_impossible_point_estimate(self):
        row = dict(self.result, estimate_type="proportion", estimate="0.02", ci_lower="-0.01", ci_upper="0.05")
        findings = results.audit(self.csv("results.csv", [row]))
        self.assertEqual([f.level for f in findings], ["WARN"])
        path = self.csv("results.csv", [dict(row, estimate="-0.005")])
        self.assertTrue(self.errors(results.audit(path)))

    def test_adjusted_ratio_and_absolute_risk_reduction_have_different_scales(self):
        for measure in ("aOR", "adjusted hazard ratio", "ARR", "log HR"):
            with self.subTest(measure=measure):
                row = dict(self.result, estimate_type=measure, estimate="-.3", ci_lower="-.5", ci_upper="-.1")
                errors = self.errors(results.audit(self.csv("results.csv", [row])))
                self.assertEqual(bool(errors), measure in {"aOR", "adjusted hazard ratio"})

    def test_unavailable_result_states_preserve_absence_and_counts(self):
        row = dict(self.result, estimate="", ci_lower="", ci_upper="", p_value="", n_events="", n_total="")
        self.assertTrue(self.errors(results.audit(self.csv("results.csv", [row]), strict=True)))
        denominators_only = self.csv("results.csv", [dict(row, n_total="200")])
        self.assertTrue(self.errors(results.audit(denominators_only, strict=True)))
        count_only = self.csv("results.csv", [dict(row, estimate_type="count", n_total="200")])
        self.assertEqual(results.audit(count_only, strict=True), [])
        for state in ("not_estimable", "not_reported", "suppressed"):
            with self.subTest(state=state):
                missing = dict(row, result_state=state, notes="See suppression footnote.", n_total="200")
                self.assertEqual(results.audit(self.csv("results.csv", [missing]), strict=True), [])
                for replacement in (dict(estimate="0"), dict(notes=""), dict(result_state="unknown")):
                    path = self.csv("results.csv", [dict(missing, **replacement)])
                    self.assertTrue(self.errors(results.audit(path, strict=True)))

    def test_counts_alone_do_not_report_continuous_or_absolute_effect_estimates(self):
        row = dict(self.result, estimate="", ci_lower="", ci_upper="", p_value="", n_total="200")
        for measure in ("mean difference", "adjusted risk difference", "beta", "β", "regression coefficient", "SMD", "log HR"):
            with self.subTest(measure=measure):
                incomplete = dict(row, estimate_type=measure)
                self.assertTrue(self.errors(results.audit(self.csv("results.csv", [incomplete]), strict=True)))
                complete = dict(incomplete, estimate="-0.75")
                self.assertEqual(results.audit(self.csv("results.csv", [complete]), strict=True), [])
        for measure in ("", "count", "number at risk", "event count"):
            with self.subTest(measure=measure):
                self.assertEqual(results.audit(self.csv("results.csv", [dict(row, estimate_type=measure)]), strict=True), [])

    def test_derived_results_trace_to_calculation(self):
        row = dict(self.result, value_origin="derived")
        path = self.csv("results.csv", [row])
        self.assertEqual([f.level for f in results.audit(path)], ["WARN"])
        self.assertTrue(self.errors(results.audit(path, strict=True)))
        path = self.csv("results.csv", [dict(row, derivation_source="analysis.R, chunk 4")])
        self.assertEqual(results.audit(path, strict=True), [])

    def test_empty_strict_audits_disclose_zero_coverage(self):
        for auditor, headers in ((results, ["result_id"]), (extraction, extraction.REQUIRED_COLUMNS)):
            path = self.csv("empty.csv", [], headers)
            self.assertEqual(auditor.audit(path), [])
            self.assertEqual([f.level for f in auditor.audit(path, strict=True)], ["WARN"])

    def test_legacy_extraction_absence_survives_without_implying_zero(self):
        row = dict(self.extracted, status="not_found", field_value="", source_quote="")
        findings = extraction.audit(self.csv("extract.csv", [row]), strict=True)
        self.assertEqual([f.level for f in findings], ["WARN"])
        path = self.csv("extract.csv", [dict(row, field_value="0")])
        self.assertTrue(self.errors(extraction.audit(path)))

    def test_bootstrap_ci_outside_estimate_is_advisory(self):
        path = self.csv("results.csv", [dict(self.result, estimate="1.7")])
        findings = results.audit(path)
        self.assertEqual(self.errors(findings), [])
        self.assertTrue(any(f.level == "WARN" for f in findings))

    def test_recurrent_event_counts_are_not_patient_counts(self):
        path = self.csv("results.csv", [dict(self.result, n_total="10", n_events="20", event_count_type="recurrent_events")])
        self.assertEqual(results.audit(path), [])

    def test_negative_fractional_nonfinite_counts_fail(self):
        for n in ("-1", "1.1", "NaN", "Infinity"):
            path = self.csv("results.csv", [dict(self.result, n_total=n)])
            self.assertTrue(self.errors(results.audit(path)), n)

    def test_log_ratio_may_be_negative(self):
        path = self.csv("results.csv", [dict(self.result, estimate_type="log HR", estimate="-.3", ci_lower="-.5", ci_upper="-.1")])
        self.assertEqual(results.audit(path), [])

    def test_proportion_scale_is_explicit(self):
        path = self.csv("results.csv", [dict(self.result, estimate_type="sensitivity", estimate="80", ci_lower="70", ci_upper="90", unit="%")])
        self.assertEqual(results.audit(path), [])
        path = self.csv("results.csv", [dict(self.result, estimate_type="sensitivity", estimate="80", ci_lower="70", ci_upper="90", unit="proportion")])
        self.assertTrue(self.errors(results.audit(path)))

    def test_duplicate_blank_result_ids_and_missing_columns_fail(self):
        path = self.csv("results.csv", [self.result, dict(self.result, result_id="")])
        self.assertTrue(self.errors(results.audit(path)))
        path = self.csv("results.csv", [self.result, self.result])
        self.assertTrue(self.errors(results.audit(path)))
        path = self.csv("results.csv", [dict(estimate="1")])
        self.assertTrue(self.errors(results.audit(path)))

    def test_json_output_and_missing_file_exit_are_stable(self):
        for script, args in (("citation_audit", ["--claim-register", str(self.root / "missing.csv")]), ("extraction_audit", ["--input", str(self.root / "missing.csv")]), ("results_audit", ["--input", str(self.root / "missing.csv")])):
            completed = subprocess.run([sys.executable, str(SCRIPTS / f"{script}.py"), *args, "--json"], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 1)
            self.assertGreater(json.loads(completed.stdout)["errors"], 0)
            self.assertEqual(completed.stderr, "")

if __name__ == "__main__":
    unittest.main()
