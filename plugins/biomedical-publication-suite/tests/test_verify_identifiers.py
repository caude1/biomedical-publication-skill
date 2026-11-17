"""Offline regression tests for bibliographic identity and retrieval failure semantics."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/biomedical-publication-suite/scripts/verify_identifiers.py'
spec = importlib.util.spec_from_file_location('verify_identifiers', SCRIPT)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

TITLE = 'A randomized trial of blood pressure management in older adults'
ROW = {'source_id': 'S1', 'title': TITLE, 'year': '2025', 'pmid': '12345678', 'doi': '10.1234/example'}
PUBMED = {'source': 'pubmed', 'pmid': '12345678', 'doi': '10.1234/example', 'title': TITLE, 'year': '2025', 'years': ['2025']}
CROSSREF = {**PUBMED, 'source': 'crossref', 'pmid': ''}
PM_DATA = {'result': {'uids': ['12345678'], '12345678': {'uid': '12345678', 'title': TITLE, 'pubdate': '2025 Jun', 'articleids': [{'idtype': 'doi', 'value': '10.1234/example'}]}}}
CR_DATA = {'status': 'ok', 'message': {'DOI': '10.1234/example', 'title': [TITLE], 'published-print': {'date-parts': [[2025, 6]]}}}
PM_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345678&retmode=json&tool=biomedical_publication_suite'
CR_URL = 'https://api.crossref.org/works/10.1234%2Fexample'


def snapshot_entry(url, response, age=0):
    return {'request_url': url, 'status': 'ok', 'retrieved_at': (datetime.now(timezone.utc) - timedelta(days=age)).isoformat(), 'response': response, 'content_sha256': v.digest(response)}


class IdentityTests(unittest.TestCase):
    def check(self, row=None, pubmed=None, crossref=None, **kwargs):
        with patch.object(v, 'pubmed_esummary', return_value=PUBMED if pubmed is None else pubmed), patch.object(v, 'crossref_work', return_value=CROSSREF if crossref is None else crossref):
            return v.verify_row(row or ROW, kwargs.get('threshold', .95), kwargs.get('allow_year_miss', False))

    def test_concordant_metadata(self):
        r = self.check()
        self.assertEqual(r['verify_status'], 'verified')
        self.assertEqual(r['verification_scope'], 'metadata_identity_only')
        self.assertEqual(r['metadata_publication_status'], 'no_signal_in_checked_metadata')

    def test_contrary_pmid_not_ignored_for_better_doi_candidate(self):
        r = self.check(pubmed={**PUBMED, 'doi': '10.1234/another'})
        self.assertEqual(r['verify_status'], 'quarantine')
        self.assertEqual(r['verified_doi'], '')

    def test_wrong_returned_pmid(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'pmid': '87654321'})['verify_status'], 'quarantine')

    def test_missing_returned_pmid(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'pmid': ''})['verify_status'], 'unresolved')

    def test_missing_returned_crossref_doi(self):
        self.assertEqual(self.check(crossref={**CROSSREF, 'doi': ''})['verify_status'], 'unresolved')

    def test_missing_pubmed_crosswalk(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'doi': ''})['verify_status'], 'unresolved')

    def test_expected_title_missing(self):
        self.assertEqual(self.check(row={**ROW, 'title': ''})['verify_status'], 'unresolved')

    def test_expected_year_missing(self):
        self.assertEqual(self.check(row={**ROW, 'year': ''})['verify_status'], 'unresolved')

    def test_expected_year_malformed_not_truncated(self):
        self.assertNotEqual(self.check(row={**ROW, 'year': '2025 garbage'})['verify_status'], 'verified')

    def test_response_title_missing(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'title': ''})['verify_status'], 'unresolved')

    def test_response_year_missing(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'year': '', 'years': []})['verify_status'], 'unresolved')

    def test_non_string_title_is_missing(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'title': {}})['verify_status'], 'unresolved')

    def test_year_flag_cannot_auto_verify_mismatch(self):
        self.assertEqual(self.check(row={**ROW, 'year': '2024'}, allow_year_miss=True)['verify_status'], 'manual_review')

    def test_valid_online_print_year(self):
        self.assertEqual(self.check(pubmed={**PUBMED, 'years': ['2024', '2025']}, crossref={**CROSSREF, 'years': ['2024', '2025']})['verify_status'], 'verified')

    def test_title_substring_is_not_perfect_match(self):
        self.assertLess(v.title_similarity('Blood pressure', TITLE), .5)
        self.assertEqual(self.check(row={**ROW, 'title': 'Blood pressure'})['verify_status'], 'quarantine')

    def test_punctuation_and_unicode_normalization(self):
        self.assertEqual(v.title_similarity('Cardiac α–blockade.', 'Cardiac α blockade'), 1.0)

    def test_close_match_cannot_verify_a_different_followup_or_receptor_group(self):
        for manuscript, provider in [('24 months', '12 months'), ('HER2+', 'HER2-')]:
            expected = f'Longitudinal analysis of treatment response and patient outcomes in cohort {manuscript}'
            actual = expected.replace(manuscript, provider)
            result = self.check(row={**ROW, 'title': expected, 'pmid': ''}, crossref={**CROSSREF, 'title': actual})
            self.assertEqual(result['verify_status'], 'manual_review')
            self.assertFalse(result['verified_doi'])

    def test_case_spacing_markup_and_terminal_period_preserve_title_identity(self):
        result = self.check(row={**ROW, 'title': 'a study of “<i>sleep</i>”.', 'pmid': ''},
                            crossref={**CROSSREF, 'title': 'A Study   of "Sleep"'})
        self.assertEqual(result['verify_status'], 'verified')

    def test_both_identifier_spellings_are_honored(self):
        result = self.check(row={**ROW, 'pmid': '', 'doi': ' ', 'DOI': ROW['doi'].upper()})
        self.assertEqual(result['verified_doi'], ROW['doi'])
        for alias, value in [('PMID', '34567890'), ('DOI', '10.1234/another')]:
            with self.subTest(alias=alias), patch.object(v, 'fetch_json') as lookup:
                self.assertEqual(v.verify_row({**ROW, alias: value})['verify_status'], 'quarantine')
                lookup.assert_not_called()

    def test_source_email_is_never_used_as_the_callers_contact(self):
        with patch.object(v, 'pubmed_esummary', return_value=PUBMED) as lookup:
            v.verify_row({**ROW, 'doi': '', 'email': 'corresponding-author@example.test'})
        lookup.assert_called_once_with(ROW['pmid'])

    def test_bad_secondary_doi_from_pubmed_stays_unresolved(self):
        self.assertEqual(self.check(row={**ROW, 'doi': ''}, pubmed={**PUBMED, 'doi': 'unassigned'})['verify_status'], 'unresolved')

    def test_invalid_pmid_not_digit_stripped(self):
        with patch.object(v, 'pubmed_esummary') as lookup:
            r = v.verify_row({**ROW, 'pmid': '12345678 and 123'})
        lookup.assert_not_called()
        self.assertEqual(r['verify_status'], 'quarantine')

    def test_recognized_pmid_url_only(self):
        self.assertEqual(v.norm_pmid('https://pubmed.ncbi.nlm.nih.gov/12345678/'), '12345678')
        self.assertFalse(v.valid_pmid(v.norm_pmid('https://example.com/12345678')))

    def test_doi_punctuation_not_silently_trimmed(self):
        self.assertEqual(v.norm_doi('doi:10.1234/Test.'), '10.1234/test.')

    def test_no_identifiers(self):
        self.assertEqual(self.check(row={'title': TITLE, 'year': '2025'})['verify_status'], 'unresolved')

    def test_publication_signal_requires_inspection(self):
        r = self.check(pubmed={**PUBMED, 'publication_signals': ['Retracted Publication']})
        self.assertEqual((r['verify_status'], r['metadata_publication_status']), ('manual_review', 'signal_found'))

    def test_one_failed_provider_cannot_be_silently_ignored(self):
        with patch.object(v, 'pubmed_esummary', side_effect=v.VerificationError('network_error', 'timeout')), patch.object(v, 'crossref_work', return_value=CROSSREF):
            self.assertEqual(v.verify_row(ROW)['verify_status'], 'network_error')

    def test_not_found_is_unresolved(self):
        with patch.object(v, 'pubmed_esummary', return_value=None), patch.object(v, 'crossref_work', return_value=CROSSREF):
            self.assertEqual(v.verify_row(ROW)['verify_status'], 'unresolved')

    def test_single_identifier_valid(self):
        self.assertEqual(self.check(row={**ROW, 'pmid': ''})['verify_status'], 'verified')

    def test_full_fields_preserved(self):
        self.assertEqual(set(self.check()), set(v.OUTPUT_FIELDS))


class ParserTests(unittest.TestCase):
    def test_crossref_subtitle_retains_report_role(self):
        for main_title in ('The ORBIT trial', 'The ORBIT trial: Study protocol'):
            data = {'message': {**CR_DATA['message'], 'title': [main_title], 'subtitle': ['Study protocol']}}
            with patch.object(v, 'fetch_json', return_value=data):
                self.assertEqual(v.crossref_work(ROW['doi'])['title'], 'The ORBIT trial: Study protocol')

    def test_pubmed_uses_relationship_type_for_linked_updates(self):
        update = {'reftype': 'Update in', 'pmid': 30000000}
        comment = {'reftype': 'Comment in', 'note': 'A comment concerning measurement error'}
        data = {'result': {ROW['pmid']: {**PM_DATA['result'][ROW['pmid']], 'references': [comment, update]}}}
        with patch.object(v, 'fetch_json', return_value=data):
            self.assertEqual(v.pubmed_esummary(ROW['pmid'])['publication_signals'], [update])

    def test_pubmed_uses_response_uid(self):
        data = {'result': {'12345678': {'uid': '33333333', 'title': TITLE, 'pubdate': '2025'}}}
        with patch.object(v, 'fetch_json', return_value=data):
            self.assertEqual(v.pubmed_esummary('12345678')['pmid'], '33333333')

    def test_crossref_uses_response_doi(self):
        data = {'message': {'DOI': '10.1234/wrong', 'title': [TITLE], 'issued': {'date-parts': [[2025]]}}}
        with patch.object(v, 'fetch_json', return_value=data):
            self.assertEqual(v.crossref_work(ROW['doi'])['doi'], '10.1234/wrong')

    def test_created_date_is_not_publication_year(self):
        data = {'message': {'DOI': ROW['doi'], 'title': [TITLE], 'created': {'date-parts': [[2025]]}}}
        with patch.object(v, 'fetch_json', return_value=data):
            self.assertEqual(v.crossref_work(ROW['doi'])['year'], '')

    def test_update_policy_alone_not_retraction_signal(self):
        data = {'message': {**CR_DATA['message'], 'update-policy': 'https://example.test/policy'}}
        with patch.object(v, 'fetch_json', return_value=data):
            self.assertEqual(v.crossref_work(ROW['doi'])['publication_signals'], [])

    def test_actual_update_signal_preserved(self):
        data = {'message': {**CR_DATA['message'], 'update-to': [{'type': 'correction', 'DOI': '10.1234/a'}]}}
        with patch.object(v, 'fetch_json', return_value=data):
            self.assertTrue(v.crossref_work(ROW['doi'])['publication_signals'])

    def test_pubmed_service_error_distinct_from_no_record(self):
        with patch.object(v, 'fetch_json', return_value={'error': 'API key secret'}):
            with self.assertRaises(v.VerificationError) as cm:
                v.pubmed_esummary('12345678')
        self.assertEqual(cm.exception.status, 'network_error')
        self.assertNotIn('secret', str(cm.exception))

    def test_crossref_unsuccessful_status(self):
        with patch.object(v, 'fetch_json', return_value={'status': 'failed', 'message': {}}):
            with self.assertRaises(v.VerificationError):
                v.crossref_work(ROW['doi'])


class NetworkAndSnapshotTests(unittest.TestCase):
    def test_offline_never_calls_network(self):
        client = v.MetadataClient(offline=True, snapshot={'records': {CR_URL: snapshot_entry(CR_URL, CR_DATA)}})
        with patch.object(client.opener, 'open', side_effect=AssertionError('network called')):
            self.assertEqual(client.get(CR_URL), CR_DATA)

    def test_offline_missing_stays_unresolved(self):
        client = v.MetadataClient(offline=True)
        with self.assertRaises(v.VerificationError) as cm:
            client.get(CR_URL)
        self.assertEqual(cm.exception.status, 'unresolved')

    def test_tampered_hash_quarantined(self):
        entry = snapshot_entry(CR_URL, CR_DATA)
        entry['content_sha256'] = '0' * 64
        client = v.MetadataClient(offline=True, snapshot={'records': {CR_URL: entry}})
        with self.assertRaises(v.VerificationError) as cm:
            client.get(CR_URL)
        self.assertEqual(cm.exception.status, 'quarantine')

    def test_stale_snapshot_manual(self):
        client = v.MetadataClient(offline=True, snapshot={'records': {CR_URL: snapshot_entry(CR_URL, CR_DATA, age=31)}})
        with self.assertRaises(v.VerificationError) as cm:
            client.get(CR_URL)
        self.assertEqual(cm.exception.status, 'manual_review')

    def test_future_snapshot_rejected(self):
        client = v.MetadataClient(offline=True, snapshot={'records': {CR_URL: snapshot_entry(CR_URL, CR_DATA, age=-1)}})
        with self.assertRaises(v.VerificationError):
            client.get(CR_URL)

    def test_credential_query_not_persisted(self):
        self.assertEqual(v.public_url(PM_URL + '&api_key=secret&email=private%40x.test'), PM_URL)

    def test_pubmed_service_error_body_is_never_cached(self):
        client = v.MetadataClient()
        body = io.BytesIO(b'{"error":"Invalid API key","api-key":"not-a-real-key"}')
        with patch.object(client.opener, 'open', return_value=body), self.assertRaises(v.VerificationError):
            client.get(PM_URL)
        self.assertEqual(client.records, {})

    def test_unsupported_host_rejected(self):
        with self.assertRaises(v.VerificationError):
            v.MetadataClient().get('https://attacker.test/file')

    def test_retry_after_long_wait_does_not_busy_retry(self):
        client = v.MetadataClient(retries=2)
        error = urllib.error.HTTPError(CR_URL, 429, 'rate limited', {'Retry-After': '60'}, None)
        with patch.object(client.opener, 'open', side_effect=error) as mocked, patch.object(v.time, 'sleep') as sleep:
            with self.assertRaises(v.VerificationError):
                client.get(CR_URL)
        self.assertEqual(mocked.call_count, 1)
        sleep.assert_not_called()

    def test_timeout_bounded_and_secret_not_echoed(self):
        client = v.MetadataClient(retries=2)
        with patch.object(client.opener, 'open', side_effect=urllib.error.URLError('api_key=secret')) as mocked, patch.object(v.time, 'sleep'):
            with self.assertRaises(v.VerificationError) as cm:
                client.get(CR_URL)
        self.assertEqual(mocked.call_count, 3)
        self.assertNotIn('secret', str(cm.exception))

    def test_invalid_json_is_unresolved_not_network_error(self):
        client = v.MetadataClient()
        with patch.object(client.opener, 'open', return_value=io.BytesIO(b'not JSON')):
            with self.assertRaises(v.VerificationError) as cm:
                client.get(CR_URL)
        self.assertEqual(cm.exception.status, 'unresolved')

    def test_oversized_response_rejected(self):
        client = v.MetadataClient()
        with patch.object(client.opener, 'open', return_value=io.BytesIO(b'x' * (v.MAX_BYTES + 1))):
            with self.assertRaises(v.VerificationError):
                client.get(CR_URL)

    def test_404_snapshot_replays_as_not_found(self):
        client = v.MetadataClient()
        with patch.object(client.opener, 'open', side_effect=urllib.error.HTTPError(CR_URL, 404, 'not found', {}, None)):
            self.assertEqual(client.get(CR_URL), {})
        self.assertEqual(client.records[CR_URL]['status'], 'not_found')
        self.assertEqual(v.MetadataClient(offline=True, snapshot={'records': client.records}).get(CR_URL), {})


class CliTests(unittest.TestCase):
    def test_replaying_only_one_source_preserves_the_original_multisource_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'literature_register.csv'
            v.write_rows(source, list(ROW), [{**ROW, 'pmid': ''}])
            snapshot = root / 'identifier_metadata.json'
            entries = {PM_URL: snapshot_entry(PM_URL, PM_DATA), CR_URL: snapshot_entry(CR_URL, CR_DATA)}
            before = json.dumps({'schema_version': '1.0', 'records': entries}, indent=2).encode()
            snapshot.write_bytes(before)
            args = [str(SCRIPT), '--input', str(source), '--offline', '--snapshot-input', str(snapshot)]
            with patch.object(sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(v.main(), 0)
            self.assertEqual(snapshot.read_bytes(), before)
            row = v.read_rows(root / 'literature_register.verified.csv')[1][0]
            self.assertEqual(row['verify_status'], 'verified')
            self.assertEqual(row['metadata_sha256'], hashlib.sha256(before).hexdigest())
            with patch.object(sys, 'argv', args + ['--register-output', str(snapshot)]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    v.main()
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(snapshot.read_bytes(), before)

    def test_offline_reconciled_register_snapshot_and_input_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'literature_register.csv'
            checked_row = {**ROW, 'publication_status': 'corrected', 'status_source': 'manually inspected publisher notice'}
            v.write_rows(source, list(checked_row), [checked_row, {**checked_row, 'source_id': 'S2', 'title': 'Wrong title'}])
            before = source.read_bytes()
            snapshot = root / 'source.json'
            snapshot.write_bytes(v.canonical_json({'schema_version': '1.0', 'records': {PM_URL: snapshot_entry(PM_URL, PM_DATA), CR_URL: snapshot_entry(CR_URL, CR_DATA)}}))
            with patch.object(sys, 'argv', [str(SCRIPT), '--input', str(source), '--offline', '--snapshot-input', str(snapshot), '--fail-on-quarantine']), contextlib.redirect_stdout(io.StringIO()):
                code = v.main()
            self.assertEqual(code, 1)
            self.assertEqual(source.read_bytes(), before)
            fields, rows = v.read_rows(root / 'literature_register.verified.csv')
            self.assertEqual([r['verify_status'] for r in rows], ['verified', 'quarantine'])
            self.assertEqual(len(v.read_rows(root / 'verified_sources.csv')[1]), 1)
            self.assertEqual(len(v.read_rows(root / 'quarantine_sources.csv')[1]), 1)
            self.assertEqual(rows[0]['metadata_sha256'], hashlib.sha256((root / 'identifier_metadata.json').read_bytes()).hexdigest())
            self.assertIn('verified_at', fields)
            self.assertEqual(rows[0]['publication_status'], 'corrected')
            self.assertEqual(rows[0]['status_source'], 'manually inspected publisher notice')
            self.assertEqual(rows[0]['metadata_publication_status'], 'no_signal_in_checked_metadata')

    def test_offline_no_snapshot_useful_unresolved_rows(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'input.csv'
            v.write_rows(source, list(ROW), [ROW])
            with patch.object(sys, 'argv', [str(SCRIPT), '--input', str(source), '--offline']), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(v.main(), 0)
            self.assertEqual(v.read_rows(Path(d) / 'literature_register.verified.csv')[1][0]['verify_status'], 'unresolved')

    def test_duplicate_source_id_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'in.csv'
            v.write_rows(path, list(ROW), [ROW, ROW])
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                v.read_rows(path)

    def test_malformed_csv_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'in.csv'
            path.write_text('title,title\na,b\n')
            with self.assertRaises(ValueError):
                v.read_rows(path)

    def test_malformed_row_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'in.csv'
            path.write_text('title,year\na\n')
            with self.assertRaises(ValueError):
                v.read_rows(path)

    def test_output_cannot_overwrite_source(self):
        with patch.object(sys, 'argv', [str(SCRIPT), '--input', 'same.csv', '--register-output', 'same.csv']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                v.main()
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
