# v0.1.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
AccreditationCheck — a GenLayer Intelligent Contract.

Verifies a claimed professional credential/license/accreditation against
independent web evidence, using a two-stage pipeline per evidence URL:

  1. DETERMINISTIC gate (pure Python, no LLM): does the claimed credential ID
     literally appear (normalized) in the fetched page text? This is
     auditable, un-gameable by confident-sounding prose, and computed the
     same way every time for the same inputs.
  2. LLM judgment (only for pages that pass the gate): does the page indicate
     the credential is currently valid, or revoked/expired, or is it unclear?

Pages that fail the deterministic gate can never contribute to a
"CredentialConfirmed" verdict, no matter how favorable an LLM might have been
about their prose. See DESIGN_DECISIONS.md for the full rationale, and
SECURITY.md for known limitations of this approach.

Storage schema note (see guardrail #17 in the project history / ARCHITECTURE.md):
every persistent field on this contract is either a plain scalar, a top-level
TreeMap, or a top-level DynArray[str]. Full check records (including the list
of per-evidence sub-records) are stored as a single JSON string per check.
This deliberately avoids ever constructing a DynArray[dataclass] or
TreeMap[K, dataclass] in user code, which is not supported by current GenVM
builds for nested/custom dataclass element types.
"""

from genlayer import *
from dataclasses import dataclass
import json
import re
from urllib.parse import urlsplit


# --------------------------------------------------------------------------
# Constants / fixed vocabularies
# --------------------------------------------------------------------------

MAX_EVIDENCE_URLS = 10
MAX_PAGE_TEXT_CHARS_FOR_PROMPT = 4000
MIN_CONFIRMING_DOMAINS = 2
MAX_HOST_LEN = 253

# Per-evidence verdict vocabulary. CredentialIdNotFound is included here
# (rather than represented only via the contains_credential_id flag) so that
# every downstream consumer of a per-evidence record has a single field to
# read for "what happened here" — see DESIGN_DECISIONS.md, "Verdict vocabulary
# placement of CredentialIdNotFound".
EVIDENCE_VERDICTS = (
    "IndicatesValid",
    "IndicatesRevokedOrExpired",
    "Unclear",
    "NoEvidence",
    "CredentialIdNotFound",
)

# Subset of EVIDENCE_VERDICTS that the LLM is actually allowed to return.
# NoEvidence and CredentialIdNotFound are assigned deterministically and the
# LLM is never asked to produce them.
LLM_VERDICTS = ("IndicatesValid", "IndicatesRevokedOrExpired", "Unclear")

FINAL_VERDICTS = (
    "CredentialConfirmed",
    "LikelyRevokedOrExpired",
    "Disputed",
    "Unverified",
    "InsufficientEvidence",
)

# Small hardcoded set of known multi-part public suffixes. Not exhaustive —
# see DESIGN_DECISIONS.md for why a full public-suffix-list dependency was
# deliberately avoided for this project.
MULTI_PART_SUFFIXES = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "sch.uk", "me.uk",
    "co.jp", "ne.jp", "or.jp",
    "co.nz", "org.nz", "govt.nz",
    "co.za", "org.za", "gov.za",
    "com.au", "net.au", "org.au", "gov.au",
    "com.br", "gov.br",
    "co.in", "org.in", "gov.in",
    "co.kr", "or.kr", "go.kr",
}


# --------------------------------------------------------------------------
# Internal (non-storage) helper dataclass.
#
# NOTE: `dataclass` is not exported by `from genlayer import *` in current
# GenVM builds, hence the explicit `from dataclasses import dataclass` above.
# This particular dataclass is a plain in-memory helper — it is never used as
# a contract field, never wrapped in DynArray/TreeMap, and never touches
# GenVM storage, so it is not subject to the DynArray/TreeMap construction
# restrictions described in ARCHITECTURE.md.
# --------------------------------------------------------------------------

@dataclass
class LLMJudgment:
    verdict: str
    raw_response: str


# --------------------------------------------------------------------------
# Pure, deterministic helper functions (module-level, not contract methods —
# GenVM lint rule E022 only constrains methods defined on the gl.Contract
# subclass itself, but keeping these as free functions makes the "no I/O,
# fully deterministic" property obvious and lets them be unit-tested
# directly with zero GenVM/stub involvement).
# --------------------------------------------------------------------------

def normalize_id_fragment(s: str) -> str:
    """Lowercase and strip everything except letters/digits."""
    if not isinstance(s, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def text_contains_credential_id(page_text: str, credential_id: str) -> bool:
    """
    Deterministic, pure-string membership check — no LLM involved.

    Design decision (documented per project requirements, see
    DESIGN_DECISIONS.md "ID matching: normalized substring, line-scoped"):
    we normalize by stripping all non-alphanumeric characters and
    lowercasing, so formatting variants of the same ID (e.g. "AB-123-456",
    "AB 123 456", "ab123456") all match. Normalization is applied per LINE
    of the page text (not to the whole document at once) to avoid the
    known failure mode where unrelated numbers from different sentences
    could be concatenated into a false match once whitespace is stripped
    document-wide. This is a mitigation, not a complete fix — see
    SECURITY.md for the residual risk.
    """
    if not isinstance(page_text, str) or not isinstance(credential_id, str):
        return False
    norm_id = normalize_id_fragment(credential_id)
    if not norm_id:
        return False
    for line in page_text.splitlines():
        if norm_id in normalize_id_fragment(line):
            return True
    return False


def normalize_host(url: str):
    """
    Strip scheme/path/query/userinfo/port from a URL and return a lowercase
    hostname, or None if the input is not a plausible URL.

    Handles IPv6 literals (via urlsplit's bracket-aware hostname parsing),
    strips a trailing DNS root dot, and rejects empty/overlong/invalid-char
    hosts.
    """
    if not isinstance(url, str):
        return None
    candidate = url.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = "http://" + candidate
    try:
        parts = urlsplit(candidate)
        host = parts.hostname
    except (ValueError, UnicodeError):
        return None
    if not host:
        return None
    host = host.rstrip(".")
    if not host or len(host) > MAX_HOST_LEN:
        return None
    if not re.match(r"^[a-z0-9:.\-]+$", host):
        return None
    return host


def registrable_domain(host: str) -> str:
    """
    Reduce a hostname to an approximate registrable domain (eTLD+1) using a
    small hardcoded set of known multi-part suffixes for cases where the
    last two labels alone are not enough (e.g. "bbc.co.uk", not "co.uk").
    """
    if not isinstance(host, str) or not host:
        return host
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    last_two = ".".join(labels[-2:])
    if last_two in MULTI_PART_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last_two


def parse_llm_verdict(raw: str) -> str:
    """
    Fixed-vocabulary parser (see DESIGN_DECISIONS.md "Fixed-vocabulary LLM
    parsing"): scans EVERY line of the raw LLM response (not just the
    first) for a case-insensitive, whitespace-collapsed exact match against
    LLM_VERDICTS, and defaults to the most conservative category ("Unclear")
    on anything unparseable.
    """
    if not isinstance(raw, str) or not raw.strip():
        return "Unclear"
    for line in raw.splitlines():
        collapsed = " ".join(line.split()).strip().lower()
        for verdict in LLM_VERDICTS:
            if collapsed == verdict.lower():
                return verdict
    return "Unclear"


def build_judgment_prompt(subject_name: str, credential_id: str, page_text: str) -> str:
    excerpt = page_text[:MAX_PAGE_TEXT_CHARS_FOR_PROMPT]
    return (
        "You are verifying a professional credential / license / accreditation claim.\n"
        f"Subject name: {subject_name}\n"
        f"Claimed credential or license ID: {credential_id}\n"
        "\n"
        "The credential ID above has already been confirmed, by exact deterministic "
        "string matching, to appear somewhere in the page text below. Your job is NOT "
        "to check whether the ID appears — that is already established. Your job is to "
        "read the page text and decide what it says about the CURRENT status of that "
        "credential for the named subject.\n"
        "\n"
        "Respond with EXACTLY ONE of the following words, alone on its own line, and "
        "nothing else:\n"
        "IndicatesValid\n"
        "IndicatesRevokedOrExpired\n"
        "Unclear\n"
        "\n"
        "Use IndicatesValid only if the page affirmatively indicates the credential is "
        "currently active/valid/in good standing for this subject.\n"
        "Use IndicatesRevokedOrExpired if the page indicates the credential has been "
        "revoked, suspended, expired, or is otherwise not currently valid — including "
        "cases where the ID merely appears on a revocation/suspension list.\n"
        "Use Unclear if the page's relevance is ambiguous, the ID appears in an "
        "unrelated context (e.g. a long list of unrelated IDs with no status "
        "information), or the page does not clearly speak to current status either way.\n"
        "\n"
        f"Page text:\n{excerpt}"
    )


def aggregate_verdict(evidence_records: list) -> str:
    """
    Pure, deterministic aggregation over already-computed per-evidence
    records. See DESIGN_DECISIONS.md "Final verdict aggregation rule" for
    the rationale behind each branch, in particular why any independent
    revocation signal outweighs corroborating "valid" signals (Disputed
    rather than CredentialConfirmed) and why a lone corroborating domain is
    Unverified rather than Confirmed.
    """
    valid_domains = set()
    revoked_domains = set()
    for record in evidence_records:
        domain = record.get("domain")
        if not domain:
            continue
        verdict = record.get("verdict")
        if verdict == "IndicatesValid":
            valid_domains.add(domain)
        elif verdict == "IndicatesRevokedOrExpired":
            revoked_domains.add(domain)

    if valid_domains and revoked_domains:
        return "Disputed"
    if revoked_domains:
        return "LikelyRevokedOrExpired"
    if len(valid_domains) >= MIN_CONFIRMING_DOMAINS:
        return "CredentialConfirmed"
    if len(valid_domains) == 1:
        return "Unverified"
    return "InsufficientEvidence"


# --------------------------------------------------------------------------
# The contract
# --------------------------------------------------------------------------

class AccreditationCheck(gl.Contract):
    # Top-level storage fields only — see the module docstring and
    # ARCHITECTURE.md for why nothing here is a nested DynArray/TreeMap of a
    # custom dataclass. Both fields below zero-initialize automatically at
    # contract creation; they are only ever read or appended/assigned to,
    # never constructed directly.
    checks: TreeMap[str, str]
    check_ids: DynArray[str]

    def __init__(self):
        # TreeMap[str, str] and DynArray[str] top-level fields are
        # zero-initialized by the runtime; nothing to do here.
        pass

    # ----------------------------------------------------------------
    # Write methods
    # ----------------------------------------------------------------

    @gl.public.write
    def submit_check(
        self,
        subject_name: str,
        claimed_credential_id: str,
        evidence_urls: list[str],
    ) -> str:
        subject_name = (subject_name or "").strip()
        claimed_credential_id = (claimed_credential_id or "").strip()

        # Pre-flight, fully-deterministic validation before any gl.nondet.*
        # call — reject obviously-insufficient submissions before spending
        # any fetch/LLM cost.
        if not subject_name:
            raise gl.vm.UserError("subject_name must not be empty")
        if not claimed_credential_id:
            raise gl.vm.UserError("claimed_credential_id must not be empty")
        if not evidence_urls:
            raise gl.vm.UserError("evidence_urls must not be empty")
        if len(evidence_urls) > MAX_EVIDENCE_URLS:
            raise gl.vm.UserError(
                f"too many evidence_urls (max {MAX_EVIDENCE_URLS}, got {len(evidence_urls)})"
            )

        # gl.message.sender_address is ALREADY an Address instance at
        # runtime — never wrap it in Address(...) again.
        caller = gl.message.sender_address

        check_id = f"check-{len(self.check_ids)}"

        seen_domains = set()
        evidence_records = []

        for raw_url in evidence_urls:
            url = (raw_url or "").strip()
            host = normalize_host(url)

            if host is None:
                evidence_records.append({
                    "url": url,
                    "domain": None,
                    "is_duplicate_domain": False,
                    "contains_credential_id": False,
                    "fetch_status": "invalid_url",
                    "verdict": "NoEvidence",
                })
                continue

            domain = registrable_domain(host)
            is_duplicate_domain = domain in seen_domains
            seen_domains.add(domain)

            pipeline_result = self._process_evidence_url(
                url, subject_name, claimed_credential_id
            )

            evidence_records.append({
                "url": url,
                "domain": domain,
                "is_duplicate_domain": is_duplicate_domain,
                "contains_credential_id": pipeline_result["contains_credential_id"],
                "fetch_status": pipeline_result["fetch_status"],
                "verdict": pipeline_result["verdict"],
            })

        final_verdict = aggregate_verdict(evidence_records)

        check_record = {
            "check_id": check_id,
            "subject_name": subject_name,
            "claimed_credential_id": claimed_credential_id,
            "submitted_by": str(caller),
            "evidence": evidence_records,
            "final_verdict": final_verdict,
        }

        self.checks[check_id] = json.dumps(check_record)
        self.check_ids.append(check_id)
        return check_id

    # ----------------------------------------------------------------
    # View methods
    # ----------------------------------------------------------------

    @gl.public.view
    def get_check(self, check_id: str) -> str:
        if check_id not in self.checks:
            raise gl.vm.UserError(f"unknown check_id: {check_id}")
        return self.checks[check_id]

    @gl.public.view
    def get_verdict(self, check_id: str) -> str:
        if check_id not in self.checks:
            raise gl.vm.UserError(f"unknown check_id: {check_id}")
        record = json.loads(self.checks[check_id])
        return record["final_verdict"]

    @gl.public.view
    def total_checks(self) -> int:
        return len(self.check_ids)

    # ----------------------------------------------------------------
    # Internal instance methods (still plain instance methods with `self`
    # as required by GenVM lint rule E022 — never @classmethod/@staticmethod
    # anywhere in this file).
    # ----------------------------------------------------------------

    def _process_evidence_url(self, url: str, subject_name: str, credential_id: str) -> dict:
        """
        Runs the fetch -> deterministic ID-gate -> (conditional) LLM
        judgment pipeline for one evidence URL, as a single nondet unit.

        Design decision: the fetch itself, and the raw page text, live
        entirely INSIDE the nondet closure and are never compared for
        validator consensus directly (raw fetched HTML/text can differ
        slightly between validators' independent fetches). Only the small
        final JSON blob (fetch_status / contains_credential_id / verdict)
        is required to match across validators via gl.eq_principle.strict_eq.
        See ARCHITECTURE.md "Equivalence principle usage" for the full
        rationale.
        """

        def pipeline() -> str:
            try:
                page_text = gl.nondet.web.render(url, mode="text")
            except Exception:
                return json.dumps({
                    "fetch_status": "inaccessible",
                    "contains_credential_id": False,
                    "verdict": "NoEvidence",
                })

            if not isinstance(page_text, str) or not page_text.strip():
                return json.dumps({
                    "fetch_status": "empty",
                    "contains_credential_id": False,
                    "verdict": "NoEvidence",
                })

            contains_id = text_contains_credential_id(page_text, credential_id)
            if not contains_id:
                # Deterministic gate fails closed: no LLM call is made at
                # all for pages that don't contain the ID, saving
                # validator cost and guaranteeing this class of page can
                # never be swayed by favorable-sounding prose.
                return json.dumps({
                    "fetch_status": "ok",
                    "contains_credential_id": False,
                    "verdict": "CredentialIdNotFound",
                })

            prompt = build_judgment_prompt(subject_name, credential_id, page_text)
            raw_response = gl.nondet.exec_prompt(prompt)
            judgment = LLMJudgment(
                verdict=parse_llm_verdict(raw_response),
                raw_response=raw_response if isinstance(raw_response, str) else "",
            )
            return json.dumps({
                "fetch_status": "ok",
                "contains_credential_id": True,
                "verdict": judgment.verdict,
            })

        result_json = gl.eq_principle.strict_eq(pipeline)
        return json.loads(result_json)
