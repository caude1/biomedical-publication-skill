# Identifier verification

This helper is optional. Manual authoritative identifier/source checks are equally valid; do not run a script merely to satisfy a workflow.

Read this when resolving DOI/PMID records or running `scripts/verify_identifiers.py`.
The script checks **bibliographic identity only**. Source-content inspection, claim
support, risk of bias, evidence quality, and full publication-status checks are separate.
A passing identity check does not justify a sentence in the manuscript.

## Input and identity rules

CSV input needs `title`, four-digit publication `year`, and at least one of `doi` or
`pmid`. Accepted aliases include `article_title`/`citation_title`, `DOI` and `PMID`.
Conflicting lowercase and uppercase versions of an identifier require reconciliation.
`source_id` (or legacy `study_id` when the `source_id` column is absent) is strongly recommended. Nonempty duplicate
IDs are rejected. Additional columns are preserved. Blank identifiers remain unresolved;
books, websites, registry entries, and non-Crossref DOIs can be verified manually with
appropriate authoritative records instead of inventing identifiers.

- Each supplied identifier must resolve and match the expected title/year. If both
  DOI and PMID are supplied, both providers are queried and the PubMed DOI crosswalk
  must match. A correct Crossref record cannot override a contradictory PubMed record.
- PMID parsing accepts one numeric identifier, `PMID:` prefix, or a PubMed URL. It
  never combines digits from mixed text. DOI prefixes and doi.org URLs are normalized;
  potentially meaningful trailing punctuation is retained.
- The response UID/DOI is checked; the requested identifier is not echoed as proof.
- Automatic verification requires title agreement after normalizing display markup, case,
  spacing, typographic quotes and a final period. Crossref may supply the subtitle separately. A close match
  at or above the similarity threshold (default 0.95) requires manual review. A more
  distant match is quarantined. A single changed digit or receptor sign can identify
  a different report. Inspect authors, journal, article type and identifiers when
  adjudicating a variant, translation or generic title.
- The expected title/year and returned title/year must be present. Missing fields
  never count as agreement. Crossref publication dates may include print, online,
  published, and issued dates; deposit/creation dates are excluded. A supplied year
  matching a recorded publication year can pass.
- `--allow-year-miss` is retained for CLI compatibility but now routes a mismatch to
  manual review; it cannot make missing or mismatched years pass.
- Update/retraction/correction signals found in the checked metadata require manual
  inspection. Absence of a signal is recorded narrowly and is never a safety verdict.

## Run and use the reconciled output

Run from the project directory; replace `<skill-dir>` with the installed skill folder:

```bash
python3 <skill-dir>/scripts/verify_identifiers.py \
  --input manuscript/literature_register.csv \
  --fail-on-quarantine
```

Default outputs are beside the input:

| File | Contents |
|---|---|
| `literature_register.verified.csv` | **All input rows** with fresh identity status and provenance; use this reconciled register in downstream audits |
| `verified_sources.csv` | Rows passing bibliographic-identity checks |
| `quarantine_sources.csv` | All nonpassing rows, with distinct status/reason; the legacy filename does not imply all are contradictions |
| `identifier_metadata.json` | Public provider responses with retrieval times, sanitized request URLs, and content hashes |

Custom destinations: `--register-output`, `--verified-output`, `--quarantine-output`,
`--snapshot-output`. Output paths must be distinct and must not overwrite the input.
Writes replace each derived file atomically. Keep run outputs together or archive them
before rerunning; a later run can replace these derived files. No manuscript, claim
register, or original literature register is silently rewritten.

Do not manually copy a `verified` flag into an older register while losing provenance.
Review the reconciled file, resolve errors with evidence, and supply it to the downstream
citation audit (or deliberately promote the complete file in the project's workflow).
An audit must not mistake `verify_status=verified` for claim-level support.

Exit codes: `0` = run completed (may include nonpassing rows); `1` = nonpassing rows
exist with `--fail-on-quarantine`; `2` = malformed input, invalid arguments, or filesystem
failure. Always read the status counts. The final stdout item is a compact JSON summary.

## States and added columns

| `verify_status` | Meaning / next action |
|---|---|
| `verified` | All supplied identity checks passed; inspect content and publication status separately |
| `quarantine` | Contradictory identity, malformed identifier, or snapshot integrity failure; inspect original source before correcting |
| `unresolved` | Missing/incomplete metadata, no record, invalid response, unsupported type, or unavailable snapshot; discover or inspect an authoritative source |
| `network_error` | Lookup failed, provider service error, unexpected redirect, or rate limiting; retry later or use another documented authoritative route |
| `manual_review` | Close title variant, stale snapshot, date discrepancy under the optional flag, or publication-update signal. Inspect and document the resolution. |

When several problems coexist, status precedence is quarantine → network_error →
unresolved → manual_review. `verification_message` retains all reported problems.

Additional output columns (existing columns are overwritten with fresh check results):

- `verified_pmid`, `verified_doi`, `verified_title`, `verified_year`: populated only on
  pass; candidate metadata remains inspectable in the snapshot on failure.
- `verification_source`: providers that yielded candidate metadata.
- `verification_message`: concise identity findings, never credential-bearing URLs.
- `verified_at`: UTC time of this verification run for passing rows; source retrieval
  times remain in the snapshot. Offline replay does not assert live freshness.
- `verification_scope`: always `metadata_identity_only`.
- `metadata_snapshot`: absolute location of the persisted JSON bundle.
- `metadata_sha256`: SHA-256 of the exact persisted snapshot bytes.
- `metadata_publication_status`: `signal_found`, `no_signal_in_checked_metadata`, or
  `not_assessed`. These are metadata observations, not a comprehensive status check. Existing manually recorded `publication_status` and its source/date are preserved; inspect any new signal against that decision.

The snapshot schema is `{ "schema_version": "1.0", "records": { <sanitized URL>:
<entry> } }`. An entry contains `request_url`, timezone-aware `retrieved_at`, `status`
(`ok` or `not_found`), `response` (provider JSON or null), and `content_sha256` (SHA-256
of canonical JSON: UTF-8, sorted keys, compact separators, non-ASCII retained).
Hashes detect modifications; they do not authenticate a manually created snapshot or
prove that its contents were issued by a provider. Preserve trusted retrieval lineage.

## Offline verification and limits

```bash
python3 <skill-dir>/scripts/verify_identifiers.py \
  --input manuscript/literature_register.csv \
  --offline --snapshot-input manuscript/identifier_metadata.json \
  --fail-on-quarantine
```

Offline mode makes no network calls. Without a matching snapshot, rows remain unresolved.
When the snapshot input and destination are the same file (as in this example), the
register points to its original bytes and hash. Replaying a subset of references
preserves all other records in that archive. Specify a different `--snapshot-output`
to write a bundle containing just the requests used in the replay.
Replay checks request identity, content hash, timezone-aware nonfuture retrieval date,
and age (default 30 days, a **local operating default**, not a publication standard).
Older snapshots become manual review; refresh live for current submission work.
`--max-snapshot-age-days` adjusts the local threshold. Identical snapshots and inputs
produce the same identity decisions; run timestamps and output locations may differ.

Live runs fetch fresh metadata; `--snapshot-input` is only accepted with `--offline`.
Requests use only official HTTPS PubMed ESummary and Crossref work endpoints; redirects
are blocked. Each host is paced at a minimum 0.35 seconds between starts. Each request
has a 15-second timeout by default, at most two retries, a 4 MB response cap, and short
bounded backoff for connection failures and HTTP 429/500/502/503/504. Long `Retry-After`
requests stop the lookup for later retry. CLI bounds are timeout >0–30 seconds, retries
0–3, and snapshot age 1–3650 days. Input is capped at 20 MB/10,000 rows and snapshot input
at 100 MB. The limits apply to one process; multiple simultaneous runs must coordinate
aggregate provider rate limits. Use appropriate batch retrieval for very large reviews.

Each lookup sends the supplied identifier to its provider. Set optional `NCBI_EMAIL`
to the caller's contact address and `NCBI_API_KEY` to use an NCBI API key. The
verifier never uses an address from a bibliography row as the caller's contact. Credentials and
email parameters are removed from persisted request URLs and error messages. No key is
required; the script does not send manuscript text, datasets, or a credential bundle.
Provider responses are public bibliographic metadata; respect any applicable content
terms when redistributing snapshots.

## Manual completion and known boundaries

A reference outside PubMed/Crossref, a provider outage, or a real title/date variation
is not proof of fabrication. Open the publisher, DOI registration agency, NLM, or other
authoritative record; record the exact URL/identifier, access date, identity fields,
reason for the discrepancy, verifier, and source locator in the project's evidence
record. Correct the input only from that evidence and rerun the check when applicable.
Keep manual identity confirmation distinct from the automated status and from semantic
claim support. There is no force-verified override in this tool.

PubMed ESummary and the returned Crossref update fields do not cover every correction,
retraction, expression of concern, version, or notice. Before relying on an important
source, inspect its current publisher/PubMed pages and linked notices, using fuller
records or appropriate additional services as available. A 404 can mean this provider
has no record; it does not establish that the identifier is globally nonexistent.

## Primary implementation references

Checked 2026-11-17. NCBI describes caller identification, a general rate limit of
three requests per second without a key, and linked citation types such as errata and
updated reports. [NCBI usage guidance](https://www.ncbi.nlm.nih.gov/books/NBK25497/) and [PubMed linked citations](https://pubmed.ncbi.nlm.nih.gov/help/#comment-correction).
Crossref documents rate limiting and the coverage of publisher and Retraction Watch
updates. [Crossref API tips](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/) and [Retraction Watch data](https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/).
Public metadata can have copyright or reuse constraints:
[NCBI disclaimer](https://www.ncbi.nlm.nih.gov/home/about/policies/).
