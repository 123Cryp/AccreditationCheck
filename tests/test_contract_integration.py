import json

import conftest  # noqa: F401
import pytest

from genlayer import gl, Address
from genlayer.gl import stub_control
from contract import AccreditationCheck


@pytest.fixture(autouse=True)
def reset_stub():
    stub_control.reset()
    yield
    stub_control.reset()


def make_contract():
    return AccreditationCheck()


def set_page(url, text):
    stub_control.web_pages[url] = text


def set_page_failure(url, exc=None):
    stub_control.web_pages[url] = exc or RuntimeError("simulated fetch failure")


def set_llm_response(substring_matcher, response):
    stub_control.llm_responses.append((substring_matcher, response))


# --------------------------------------------------------------------------
# Pre-flight validation
# --------------------------------------------------------------------------

class TestPreflightValidation:
    def test_empty_subject_name_rejected(self):
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.submit_check("", "AB123456", ["https://a.com"])

    def test_whitespace_only_subject_name_rejected(self):
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.submit_check("   ", "AB123456", ["https://a.com"])

    def test_empty_credential_id_rejected(self):
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.submit_check("Jane Doe", "", ["https://a.com"])

    def test_empty_evidence_urls_rejected(self):
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.submit_check("Jane Doe", "AB123456", [])

    def test_too_many_evidence_urls_rejected(self):
        c = make_contract()
        urls = [f"https://site{i}.com" for i in range(11)]
        with pytest.raises(gl.vm.UserError):
            c.submit_check("Jane Doe", "AB123456", urls)

    def test_preflight_rejects_before_any_fetch(self):
        # No web_pages configured at all — if the contract tried to fetch
        # anything before validating, the stub would raise a *different*
        # (RuntimeError) exception instead of UserError.
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.submit_check("", "", [])


# --------------------------------------------------------------------------
# Deterministic ID gate excluding sources — the core novel mechanic
# --------------------------------------------------------------------------

class TestDeterministicIdGate:
    def test_source_without_id_is_excluded_even_with_favorable_llm_configured(self):
        c = make_contract()
        set_page("https://a.gov", "Jane Doe holds license AB123456, status active.")
        set_page("https://b.com", "Jane Doe is a wonderful, highly qualified professional.")
        # Configure the LLM to be maximally favorable for ANY prompt — if the
        # gate were broken, b.com's glowing-but-ID-less text would still
        # count.
        set_llm_response(lambda prompt: True, "IndicatesValid")

        check_id = c.submit_check("Jane Doe", "AB123456", [
            "https://a.gov", "https://b.com",
        ])
        record = json.loads(c.get_check(check_id))
        evidence_by_url = {e["url"]: e for e in record["evidence"]}

        assert evidence_by_url["https://a.gov"]["contains_credential_id"] is True
        assert evidence_by_url["https://a.gov"]["verdict"] == "IndicatesValid"

        assert evidence_by_url["https://b.com"]["contains_credential_id"] is False
        assert evidence_by_url["https://b.com"]["verdict"] == "CredentialIdNotFound"

        # A single corroborating domain is Unverified, not Confirmed — and
        # critically, b.com contributed nothing despite the favorable LLM.
        assert record["final_verdict"] == "Unverified"

    def test_two_id_matching_domains_confirm_while_non_matching_third_is_ignored(self):
        c = make_contract()
        set_page("https://a.gov", "License AB123456 — status: active.")
        set_page("https://b.org", "Certificate AB-123-456 currently valid.")
        set_page("https://c.com", "This person seems very credible and trustworthy.")
        set_llm_response(lambda p: "AB123456" in p or "AB-123-456" in p, "IndicatesValid")

        check_id = c.submit_check("Jane Doe", "AB123456", [
            "https://a.gov", "https://b.org", "https://c.com",
        ])
        record = json.loads(c.get_check(check_id))
        assert record["final_verdict"] == "CredentialConfirmed"

        c_record = next(e for e in record["evidence"] if e["url"] == "https://c.com")
        assert c_record["contains_credential_id"] is False
        assert c_record["verdict"] == "CredentialIdNotFound"


# --------------------------------------------------------------------------
# "ID present but revoked" scenario — guardrail's specific documented case
# --------------------------------------------------------------------------

class TestIdPresentButRevoked:
    def test_id_on_a_revocation_list_is_not_treated_as_valid(self):
        c = make_contract()
        url = "https://board.gov/revoked-licenses"
        set_page(url, "Revoked license list includes: AB123456, CD999999, EF000111.")
        set_llm_response(lambda p: "AB123456" in p, "IndicatesRevokedOrExpired")

        check_id = c.submit_check("Jane Doe", "AB123456", [url])
        record = json.loads(c.get_check(check_id))
        evidence = record["evidence"][0]

        assert evidence["contains_credential_id"] is True
        assert evidence["verdict"] == "IndicatesRevokedOrExpired"
        assert record["final_verdict"] == "LikelyRevokedOrExpired"


# --------------------------------------------------------------------------
# Fetch failure / invalid URL handling
# --------------------------------------------------------------------------

class TestFetchFailureHandling:
    def test_inaccessible_page_recorded_as_no_evidence(self):
        c = make_contract()
        set_page_failure("https://reuters.com/some-article")

        check_id = c.submit_check("Jane Doe", "AB123456", ["https://reuters.com/some-article"])
        record = json.loads(c.get_check(check_id))
        evidence = record["evidence"][0]

        assert evidence["fetch_status"] == "inaccessible"
        assert evidence["contains_credential_id"] is False
        assert evidence["verdict"] == "NoEvidence"
        assert record["final_verdict"] == "InsufficientEvidence"

    def test_invalid_url_recorded_without_attempting_fetch(self):
        c = make_contract()
        check_id = c.submit_check("Jane Doe", "AB123456", ["not a url at all ???"])
        record = json.loads(c.get_check(check_id))
        evidence = record["evidence"][0]

        assert evidence["domain"] is None
        assert evidence["fetch_status"] == "invalid_url"
        assert evidence["verdict"] == "NoEvidence"

    def test_empty_page_text_treated_as_no_evidence(self):
        c = make_contract()
        set_page("https://a.com", "   ")
        check_id = c.submit_check("Jane Doe", "AB123456", ["https://a.com"])
        record = json.loads(c.get_check(check_id))
        assert record["evidence"][0]["verdict"] == "NoEvidence"

    def test_mixed_success_and_failure_sources(self):
        c = make_contract()
        set_page("https://a.gov", "License AB123456 active and valid.")
        set_page_failure("https://ftc.gov/broken")
        set_llm_response(lambda p: True, "IndicatesValid")

        check_id = c.submit_check("Jane Doe", "AB123456", [
            "https://a.gov", "https://ftc.gov/broken",
        ])
        record = json.loads(c.get_check(check_id))
        by_url = {e["url"]: e for e in record["evidence"]}
        assert by_url["https://a.gov"]["verdict"] == "IndicatesValid"
        assert by_url["https://ftc.gov/broken"]["fetch_status"] == "inaccessible"


# --------------------------------------------------------------------------
# Duplicate domain detection
# --------------------------------------------------------------------------

class TestDuplicateDomainDetection:
    def test_first_occurrence_not_flagged_second_is(self):
        c = make_contract()
        set_page("https://a.com/page1", "License AB123456 active.")
        set_page("https://a.com/page2", "License AB123456 active.")
        set_llm_response(lambda p: True, "IndicatesValid")

        check_id = c.submit_check("Jane Doe", "AB123456", [
            "https://a.com/page1", "https://a.com/page2",
        ])
        record = json.loads(c.get_check(check_id))
        assert record["evidence"][0]["is_duplicate_domain"] is False
        assert record["evidence"][1]["is_duplicate_domain"] is True

    def test_two_pages_same_domain_do_not_confirm_alone(self):
        c = make_contract()
        set_page("https://a.com/page1", "License AB123456 active.")
        set_page("https://a.com/page2", "License AB123456 active.")
        set_llm_response(lambda p: True, "IndicatesValid")

        check_id = c.submit_check("Jane Doe", "AB123456", [
            "https://a.com/page1", "https://a.com/page2",
        ])
        record = json.loads(c.get_check(check_id))
        # Only one independent domain despite two matching pages.
        assert record["final_verdict"] == "Unverified"


# --------------------------------------------------------------------------
# get_check / get_verdict / total_checks
# --------------------------------------------------------------------------

class TestViewMethods:
    def test_get_check_unknown_id_raises(self):
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.get_check("check-does-not-exist")

    def test_get_verdict_unknown_id_raises(self):
        c = make_contract()
        with pytest.raises(gl.vm.UserError):
            c.get_verdict("check-does-not-exist")

    def test_get_verdict_matches_get_check_final_verdict(self):
        c = make_contract()
        set_page("https://a.gov", "License AB123456 active.")
        set_page("https://b.org", "Certificate AB123456 valid.")
        set_llm_response(lambda p: True, "IndicatesValid")

        check_id = c.submit_check("Jane Doe", "AB123456", ["https://a.gov", "https://b.org"])
        assert c.get_verdict(check_id) == json.loads(c.get_check(check_id))["final_verdict"]
        assert c.get_verdict(check_id) == "CredentialConfirmed"

    def test_total_checks_starts_at_zero(self):
        c = make_contract()
        assert c.total_checks() == 0

    def test_total_checks_increments_per_submission(self):
        c = make_contract()
        set_page("https://a.com", "irrelevant text")
        c.submit_check("Jane Doe", "AB123456", ["https://a.com"])
        assert c.total_checks() == 1
        c.submit_check("John Roe", "CD999999", ["https://a.com"])
        assert c.total_checks() == 2

    def test_check_ids_are_distinct_and_sequential(self):
        c = make_contract()
        set_page("https://a.com", "irrelevant text")
        id1 = c.submit_check("Jane Doe", "AB123456", ["https://a.com"])
        id2 = c.submit_check("John Roe", "CD999999", ["https://a.com"])
        assert id1 != id2

    def test_submitted_by_records_sender_address(self):
        c = make_contract()
        set_page("https://a.com", "irrelevant text")
        custom_sender = Address("0x" + "42" * 20)
        stub_control.sender_address = custom_sender

        check_id = c.submit_check("Jane Doe", "AB123456", ["https://a.com"])
        record = json.loads(c.get_check(check_id))
        assert record["submitted_by"] == str(custom_sender)


# --------------------------------------------------------------------------
# Storage isolation between separate contract instances (sanity check that
# top-level DynArray/TreeMap zero-init doesn't leak shared mutable state
# across instances)
# --------------------------------------------------------------------------

class TestStorageIsolation:
    def test_two_contract_instances_do_not_share_storage(self):
        set_page("https://a.com", "irrelevant text")
        c1 = make_contract()
        c2 = make_contract()
        c1.submit_check("Jane Doe", "AB123456", ["https://a.com"])
        assert c1.total_checks() == 1
        assert c2.total_checks() == 0
