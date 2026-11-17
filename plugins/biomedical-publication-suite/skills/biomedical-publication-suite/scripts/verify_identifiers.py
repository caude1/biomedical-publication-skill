#!/usr/bin/env python3
"""Verify bibliographic identity using PubMed/Crossref; never infer claim support."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path

SCHEMA_VERSION = "1.0"
MAX_BYTES = 4_000_000
MAX_ROWS = 10_000
OUTPUT_FIELDS = [
    "verify_status", "verified_pmid", "verified_doi", "verified_title", "verified_year",
    "verification_source", "verification_message", "verified_at", "verification_scope",
    "metadata_snapshot", "metadata_sha256", "metadata_publication_status",
]


class VerificationError(Exception):
    """A bounded, safe-to-display error, without credential-bearing request URLs."""
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def canonical_json(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(data: object) -> str:
    return hashlib.sha256(canonical_json(data)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def valid_timestamp(value: object) -> bool:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def norm_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKC", title_key(value))
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def title_key(value: str) -> str:
    """Ignore display markup, case, spacing and a final period, preserving scientific symbols."""
    text = re.sub(r"</?(?:[a-z]+:)?(?:b|i|sup|sub|strong|em|u|italic|bold|span)\b[^>]*>", "", value, flags=re.I)
    text = unicodedata.normalize("NFC", html.unescape(text)).casefold()
    text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"}))
    return " ".join(text.split()).removesuffix(".")


def norm_doi(value: str | None) -> str:
    value = value.strip() if isinstance(value, str) else ""
    if re.match(r"^https?://(?:dx\.)?doi\.org/", value, re.I):
        value = urllib.parse.unquote(re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I))
    value = re.sub(r"^doi:\s*", "", value, flags=re.I).lower()
    return value  # Trailing punctuation may be part of the DOI: never silently remove it.


def norm_pmid(value: str | None) -> str:
    value = value.strip() if isinstance(value, str) else ""
    value = re.sub(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/([0-9]+)/?$", r"\1", value, flags=re.I)
    return re.sub(r"^pmid:\s*", "", value, flags=re.I)


def valid_doi(value: str) -> bool:
    return bool(re.fullmatch(r"10\.[0-9]{4,9}/[^\s\x00-\x1f]+", value)) and len(value) <= 2048


def valid_pmid(value: str) -> bool:
    return bool(re.fullmatch(r"[1-9][0-9]{0,11}", value))


def title_similarity(left: str | None, right: str | None) -> float:
    a, b = norm_text(left), norm_text(right)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def public_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    pairs = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k not in {"api_key", "email", "mailto"}]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(pairs), ""))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VerificationError("network_error", "Unexpected redirect; verify the official endpoint manually")


class MetadataClient:
    """Sequential bounded retrieval; snapshots contain public metadata, never API keys."""
    def __init__(self, *, offline=False, snapshot=None, timeout=15, retries=2, max_age_days=30):
        self.offline = offline
        self.timeout = timeout
        self.retries = retries
        self.max_age_days = max_age_days
        self.records = {}
        self.cached = (snapshot or {}).get("records", {})
        self.last_call = {}
        self.opener = urllib.request.build_opener(NoRedirect())

    def get(self, url: str) -> dict:
        safe_url = public_url(url)
        host = urllib.parse.urlsplit(url).hostname
        if host not in {"eutils.ncbi.nlm.nih.gov", "api.crossref.org"}:
            raise VerificationError("unresolved", "Unsupported metadata host")
        if safe_url in self.records:
            return self._replay(self.records[safe_url], safe_url)
        if self.offline:
            if safe_url not in self.cached:
                raise VerificationError("unresolved", "No matching offline metadata snapshot")
            entry = self.cached[safe_url]
            self.records[safe_url] = entry
            return self._replay(entry, safe_url)
        for attempt in range(self.retries + 1):
            delay = 0.35 - (time.monotonic() - self.last_call.get(host, 0))
            if delay > 0:
                time.sleep(delay)
            self.last_call[host] = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent": "biomedical-publication-suite/1.0 identifier-verification", "Accept": "application/json"})
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise VerificationError("unresolved", "Metadata response exceeded 4 MB limit")
                try:
                    data = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeError):
                    raise VerificationError("unresolved", "Metadata endpoint returned invalid JSON") from None
                if not isinstance(data, dict):
                    raise VerificationError("unresolved", "Metadata JSON root is not an object")
                if host == "eutils.ncbi.nlm.nih.gov" and data.get("error"):
                    # A provider error may echo identifying request parameters.
                    raise VerificationError("network_error", "PubMed reported a service error; retry later")
                self.records[safe_url] = {"request_url": safe_url, "retrieved_at": utc_now(), "status": "ok", "response": data, "content_sha256": digest(data)}
                return data
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    self.records[safe_url] = {"request_url": safe_url, "retrieved_at": utc_now(), "status": "not_found", "response": None, "content_sha256": digest(None)}
                    return {}
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    wait = self._retry_delay(exc.headers.get("Retry-After"), attempt)
                    if wait > 10:
                        raise VerificationError("network_error", "Provider requested a long retry delay; retry later") from None
                    time.sleep(wait)
                    continue
                raise VerificationError("network_error", f"Metadata HTTP {exc.code}; retry later or inspect official source") from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < self.retries:
                    time.sleep(min(2 ** attempt, 4))
                    continue
                raise VerificationError("network_error", "Metadata connection failed after bounded retries") from None
        raise VerificationError("network_error", "Metadata retrieval did not complete")

    @staticmethod
    def _retry_delay(header, attempt):
        if header:
            try:
                return max(0, float(header))
            except ValueError:
                try:
                    return max(0, (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError):
                    pass
        return min(2 ** attempt, 4)

    def _replay(self, entry, url):
        if not isinstance(entry, dict) or entry.get("request_url") != url:
            raise VerificationError("unresolved", "Offline snapshot request does not match")
        if entry.get("content_sha256") != digest(entry.get("response")):
            raise VerificationError("quarantine", "Metadata snapshot hash mismatch")
        if not valid_timestamp(entry.get("retrieved_at")):
            raise VerificationError("unresolved", "Metadata snapshot has invalid or future retrieval time")
        stamp = datetime.fromisoformat(entry["retrieved_at"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - stamp).total_seconds() > self.max_age_days * 86400:
            raise VerificationError("manual_review", "Metadata snapshot is stale; refresh before current verification")
        if entry.get("status") == "not_found":
            return {}
        data = entry.get("response")
        if entry.get("status") != "ok" or not isinstance(data, dict):
            raise VerificationError("unresolved", "Metadata snapshot has unsupported status or response")
        return data


_CLIENT = None


def fetch_json(url: str, timeout: int = 20) -> dict:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = MetadataClient(timeout=timeout)
    return _CLIENT.get(url)


def years_in(value: str) -> list[str]:
    return sorted(set(re.findall(r"\b[12][0-9]{3}\b", value)))


def pubmed_esummary(pmid: str, email: str | None = None) -> dict | None:
    pmid = norm_pmid(pmid)
    if not valid_pmid(pmid):
        raise VerificationError("quarantine", "PMID must be a single valid identifier")
    params = {"db": "pubmed", "id": pmid, "retmode": "json", "tool": "biomedical_publication_suite"}
    if email or os.environ.get("NCBI_EMAIL"):
        params["email"] = email or os.environ["NCBI_EMAIL"]
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    data = fetch_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urllib.parse.urlencode(params))
    if data.get("error"):
        raise VerificationError("network_error", "PubMed reported a service error; retry later")
    result = data.get("result", {})
    record = result.get(pmid) if isinstance(result, dict) else None
    if not isinstance(record, dict):
        return None
    if record.get("error"):
        return None
    years = years_in(str(record.get("pubdate", "")) + " " + str(record.get("epubdate", "")))
    articleids = record.get("articleids") or []
    doi = next((x.get("value", "") for x in articleids if isinstance(x, dict) and x.get("idtype") == "doi"), "")
    # Inspect the relation type, since a linked article's title or note can mention an unrelated correction.
    signals = []
    update_labels = ("retract", "correct", "erratum", "concern", "updat", "republish")
    for label in record.get("pubtype") or []:
        if any(term in label.casefold() for term in update_labels):
            signals.append(label)
    for reference in record.get("references") or []:
        if isinstance(reference, dict) and any(term in str(reference.get("reftype", "")).casefold() for term in update_labels):
            signals.append(reference)
    return {"pmid": str(record.get("uid", "")), "doi": norm_doi(doi), "title": record.get("title", ""), "year": years[0] if years else "", "years": years, "source": "pubmed", "publication_signals": signals}


def crossref_work(doi: str) -> dict | None:
    doi = norm_doi(doi)
    if not valid_doi(doi):
        raise VerificationError("quarantine", "DOI syntax is invalid; do not guess or trim the identifier")
    data = fetch_json("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    if data.get("status") not in {None, "ok"}:
        raise VerificationError("unresolved", "Crossref response status was not successful")
    msg = data.get("message")
    if not isinstance(msg, dict):
        return None
    titles = msg.get("title") or []
    if not isinstance(titles, list):
        titles = []
    title = titles[0] if titles and isinstance(titles[0], str) else ""
    subtitles = msg.get("subtitle") or []
    if title and isinstance(subtitles, list) and subtitles and isinstance(subtitles[0], str):
        subtitle = subtitles[0].strip()
        if subtitle and not title_key(title).endswith(title_key(subtitle)):
            title = f"{title.rstrip(': ')}: {subtitle}"
    years = []
    for key in ("published-print", "published-online", "published", "issued"):
        dates = msg.get(key) or {}
        parts = dates.get("date-parts") if isinstance(dates, dict) else None
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            value = str(parts[0][0])
            if re.fullmatch(r"[12][0-9]{3}", value):
                years.append(value)
    years = sorted(set(years))  # Deposit/created year is not a publication year.
    signals = []
    for key in ("update-to", "updated-by"):
        if msg.get(key):
            signals.append({key: msg[key]})
    return {"pmid": "", "doi": norm_doi(msg.get("DOI", "")), "title": title, "year": years[0] if years else "", "years": years, "source": "crossref", "publication_signals": signals}


def verify_row(row: dict[str, str], title_threshold: float = 0.95, allow_year_miss: bool = False) -> dict[str, str]:
    expected_title = row.get("title") or row.get("article_title") or row.get("citation_title") or ""
    expected_year = (row.get("year") or "").strip()
    expected_doi = norm_doi(row.get("doi")) or norm_doi(row.get("DOI"))
    pmid = norm_pmid(row.get("pmid")) or norm_pmid(row.get("PMID"))
    result = {key: "" for key in OUTPUT_FIELDS}
    result.update(verify_status="unresolved", verification_scope="metadata_identity_only", metadata_publication_status="not_assessed")
    problems = []
    candidates = []

    def problem(status, message):
        problems.append((status, message))

    for field, normalize in (("doi", norm_doi), ("pmid", norm_pmid)):
        identifiers = {normalize(row.get(key)) for key in (field, field.upper())} - {""}
        if len(identifiers) > 1:
            problem("quarantine", f"Conflicting {field.upper()} columns; reconcile the source identifiers")
    if pmid and not valid_pmid(pmid):
        problem("quarantine", "Invalid PMID syntax; multiple identifiers or mixed text are not accepted")
    if expected_doi and not valid_doi(expected_doi):
        problem("quarantine", "Invalid DOI syntax; verify the source identifier")
    if problems:
        result.update(verify_status="quarantine", verification_message="; ".join(m for _, m in problems))
        return result
    if not (pmid or expected_doi):
        problem("unresolved", "No DOI/PMID supplied; resolve other source types manually")
    if not norm_text(expected_title):
        problem("unresolved", "Expected title is missing; inspect candidate metadata before completing it")
    if not re.fullmatch(r"[12][0-9]{3}", expected_year):
        problem("unresolved", "Expected publication year is missing or invalid")

    for source, identifier, lookup in (("pubmed", pmid, lambda: pubmed_esummary(pmid)), ("crossref", expected_doi, lambda: crossref_work(expected_doi))):
        if not identifier:
            continue
        try:
            record = lookup()
            if record is None:
                problem("unresolved", f"{source}: supplied identifier not resolved; not evidence that the work does not exist")
            else:
                candidates.append(record)
        except VerificationError as exc:
            problem(exc.status, f"{source}: {exc}")
        except (ValueError, TypeError, KeyError, AttributeError):
            problem("unresolved", f"{source}: malformed metadata; inspect the official record")
        except Exception:
            problem("network_error", f"{source}: lookup failed; no verification established")

    for item in candidates:
        source = item.get("source", "metadata")
        if not norm_text(item.get("title")):
            problem("unresolved", f"{source}: response title missing")
        elif norm_text(expected_title) and title_key(expected_title) != title_key(item["title"]):
            similarity = title_similarity(expected_title, item["title"])
            state = "manual_review" if similarity >= title_threshold else "quarantine"
            problem(state, f"{source}: title mismatch (similarity {similarity:.3f}); compare the complete titles")
        years = item.get("years") or ([str(item["year"])] if item.get("year") else [])
        if not years:
            problem("unresolved", f"{source}: publication year missing")
        elif expected_year and expected_year not in years:
            problem("manual_review" if allow_year_miss else "quarantine", f"{source}: publication year mismatch; inspect online/print dates")
        if source == "pubmed":
            if not item.get("pmid"):
                problem("unresolved", "pubmed: returned PMID missing")
            elif norm_pmid(item["pmid"]) != pmid:
                problem("quarantine", "pubmed: returned PMID differs from requested PMID")
            if item.get("doi") and not valid_doi(norm_doi(item["doi"])):
                problem("unresolved", "pubmed: returned DOI has invalid syntax")
        if source == "crossref" and not item.get("doi"):
            problem("unresolved", "crossref: response DOI missing; requested DOI is not verification")
        if expected_doi:
            if not item.get("doi"):
                problem("unresolved", f"{source}: DOI crosswalk missing")
            elif norm_doi(item["doi"]) != expected_doi:
                problem("quarantine", f"{source}: DOI differs from supplied DOI")
        if item.get("publication_signals"):
            problem("manual_review", f"{source}: publication-update signal requires source inspection")
    if len(candidates) > 1:
        left, right = candidates[:2]
        if left.get("doi") and right.get("doi") and norm_doi(left["doi"]) != norm_doi(right["doi"]):
            problem("quarantine", "Providers identify different DOIs; no winning candidate is selected")
        if left.get("title") and right.get("title") and title_similarity(left["title"], right["title"]) < title_threshold:
            problem("quarantine", "Provider titles conflict")
        ly = set(left.get("years") or [left.get("year")]) - {None, ""}
        ry = set(right.get("years") or [right.get("year")]) - {None, ""}
        if ly and ry and not ly & ry:
            problem("manual_review", "Provider publication years conflict")
    result["verification_source"] = ";".join(sorted({x.get("source", "") for x in candidates}))
    if candidates:
        result["metadata_publication_status"] = "signal_found" if any(x.get("publication_signals") for x in candidates) else "no_signal_in_checked_metadata"
    if problems:
        ranks = {"quarantine": 4, "network_error": 3, "unresolved": 2, "manual_review": 1}
        result["verify_status"] = max((s for s, _ in problems), key=ranks.get)
        result["verification_message"] = "; ".join(dict.fromkeys(m for _, m in problems))
    elif candidates:
        result.update(verify_status="verified", verified_pmid=pmid, verified_doi=expected_doi or norm_doi(candidates[0].get("doi")), verified_title=candidates[0]["title"], verified_year=expected_year, verified_at=utc_now(), verification_message="All supplied identifiers and title/year checks passed; claim support and publication status remain separate checks")
    return result


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if path.stat().st_size > 20_000_000:
        raise ValueError("Input CSV exceeds 20 MB")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        fields = list(reader.fieldnames or [])
        if not fields or any(not x.strip() for x in fields) or len(set(fields)) != len(fields):
            raise ValueError("CSV needs nonempty unique column names")
        rows = []
        source_ids = set()
        for row in reader:
            if len(rows) >= MAX_ROWS:
                raise ValueError("Input CSV exceeds 10,000 rows; split into bounded batches")
            if None in row or any(v is None for v in row.values()):
                raise ValueError("CSV row width does not match header")
            source_id = row.get("source_id", row.get("study_id", "")).strip()
            if source_id and source_id in source_ids:
                raise ValueError("Duplicate source_id; reconcile records before verification")
            if source_id:
                source_ids.add(source_id)
            rows.append(row)
        return fields, rows


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, stream.getvalue().encode("utf-8"))


def load_snapshot(path: Path) -> tuple[dict, str]:
    if path.stat().st_size > 100_000_000:
        raise ValueError("Snapshot exceeds 100 MB")
    content = path.read_bytes()
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("records"), dict):
        raise ValueError("Snapshot needs schema_version 1.0 and a records object")
    return data, hashlib.sha256(content).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="manuscript/literature_register.csv")
    parser.add_argument("--verified-output", help="Passing rows; default sibling verified_sources.csv")
    parser.add_argument("--quarantine-output", help="All nonpassing rows; default sibling quarantine_sources.csv")
    parser.add_argument("--register-output", help="All reconciled rows; default sibling literature_register.verified.csv")
    parser.add_argument("--snapshot-output", help="Public metadata JSON; default sibling identifier_metadata.json")
    parser.add_argument("--offline", action="store_true", help="Only replay snapshots; no network access")
    parser.add_argument("--snapshot-input", help="Snapshot JSON to replay in offline mode")
    parser.add_argument("--max-snapshot-age-days", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--title-threshold", type=float, default=0.95)
    parser.add_argument("--allow-year-miss", action="store_true", help="Route year mismatches to manual review, never auto-pass")
    parser.add_argument("--fail-on-quarantine", action="store_true", help="Exit 1 for ANY nonverified row (legacy flag name)")
    args = parser.parse_args()
    if not 0.8 <= args.title_threshold <= 1 or not 0 < args.timeout <= 30 or not 0 <= args.retries <= 3 or not 1 <= args.max_snapshot_age_days <= 3650:
        parser.error("Bounds: title threshold 0.8..1, timeout >0..30, retries 0..3, snapshot age 1..3650 days")
    if args.snapshot_input and not args.offline:
        parser.error("--snapshot-input requires --offline; live runs fetch fresh metadata")
    input_path = Path(args.input)
    parent = input_path.parent
    outputs = [Path(args.verified_output or parent / "verified_sources.csv"), Path(args.quarantine_output or parent / "quarantine_sources.csv"), Path(args.register_output or parent / "literature_register.verified.csv"), Path(args.snapshot_output or parent / "identifier_metadata.json")]
    if input_path.resolve() in {p.resolve() for p in outputs} or len({p.resolve() for p in outputs}) != len(outputs):
        parser.error("Outputs must be distinct and must not overwrite the input register")
    snapshot_input = Path(args.snapshot_input).resolve() if args.snapshot_input else None
    if snapshot_input in {p.resolve() for p in outputs[:3]}:
        parser.error("A CSV output must not overwrite the input snapshot")
    try:
        fields, rows = read_rows(input_path)
        snapshot, snapshot_hash = load_snapshot(snapshot_input) if snapshot_input else (None, "")
        global _CLIENT
        _CLIENT = MetadataClient(offline=args.offline, snapshot=snapshot, timeout=args.timeout, retries=args.retries, max_age_days=args.max_snapshot_age_days)
        merged = [{**row, **verify_row(row, args.title_threshold, args.allow_year_miss)} for row in rows]
        if outputs[3].resolve() != snapshot_input:
            bundle = {"schema_version": SCHEMA_VERSION, "records": _CLIENT.records}
            blob = canonical_json(bundle)
            snapshot_hash = hashlib.sha256(blob).hexdigest()
            atomic_write(outputs[3], blob)
        for row in merged:
            row["metadata_snapshot"] = str(outputs[3].resolve())
            row["metadata_sha256"] = snapshot_hash
        fields += [field for field in OUTPUT_FIELDS if field not in fields]
        verified = [r for r in merged if r["verify_status"] == "verified"]
        pending = [r for r in merged if r["verify_status"] != "verified"]
        for path, subset in zip(outputs[:3], (verified, pending, merged)):
            write_rows(path, fields, subset)
        counts = {status: sum(r["verify_status"] == status for r in merged) for status in ("verified", "quarantine", "unresolved", "network_error", "manual_review")}
        print(json.dumps({"counts": counts, "scope": "metadata_identity_only", "register_output": str(outputs[2]), "snapshot_output": str(outputs[3])}, sort_keys=True))
        return 1 if pending and args.fail_on_quarantine else 0
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Identifier verifier input/output error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
