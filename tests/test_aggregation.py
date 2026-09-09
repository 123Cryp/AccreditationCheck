import conftest  # noqa: F401
from contract import aggregate_verdict, FINAL_VERDICTS


def rec(domain, verdict, contains=True):
    return {"domain": domain, "verdict": verdict, "contains_credential_id": contains}


class TestAggregateVerdict:
    def test_two_independent_valid_domains_confirms(self):
        records = [
            rec("a.com", "IndicatesValid"),
            rec("b.gov", "IndicatesValid"),
        ]
        assert aggregate_verdict(records) == "CredentialConfirmed"

    def test_single_valid_domain_is_unverified_not_confirmed(self):
        records = [rec("a.com", "IndicatesValid")]
        assert aggregate_verdict(records) == "Unverified"

    def test_same_domain_twice_does_not_double_count(self):
        # Two records from the SAME domain both saying valid must not
        # satisfy the two-independent-domain requirement.
        records = [
            rec("a.com", "IndicatesValid"),
            rec("a.com", "IndicatesValid"),
        ]
        assert aggregate_verdict(records) == "Unverified"

    def test_any_revocation_with_no_valid_is_likely_revoked(self):
        records = [rec("a.com", "IndicatesRevokedOrExpired")]
        assert aggregate_verdict(records) == "LikelyRevokedOrExpired"

    def test_revocation_and_valid_together_is_disputed(self):
        records = [
            rec("a.com", "IndicatesValid"),
            rec("b.com", "IndicatesRevokedOrExpired"),
        ]
        assert aggregate_verdict(records) == "Disputed"

    def test_two_valid_plus_one_revoked_is_still_disputed(self):
        # Revocation signal outweighs corroborating valid signals even
        # when valid sources outnumber revoking ones — see
        # DESIGN_DECISIONS.md for the asymmetric-risk rationale.
        records = [
            rec("a.com", "IndicatesValid"),
            rec("b.com", "IndicatesValid"),
            rec("c.com", "IndicatesRevokedOrExpired"),
        ]
        assert aggregate_verdict(records) == "Disputed"

    def test_no_signal_at_all_is_insufficient_evidence(self):
        records = [
            rec("a.com", "Unclear"),
            rec("b.com", "NoEvidence", contains=False),
        ]
        assert aggregate_verdict(records) == "InsufficientEvidence"

    def test_empty_evidence_list_is_insufficient_evidence(self):
        assert aggregate_verdict([]) == "InsufficientEvidence"

    def test_credential_id_not_found_records_never_contribute(self):
        # Even many CredentialIdNotFound records across many domains must
        # never push the result toward CredentialConfirmed — this is the
        # core "deterministic gate" property, tested at the aggregation
        # layer directly.
        records = [
            rec("a.com", "CredentialIdNotFound", contains=False),
            rec("b.com", "CredentialIdNotFound", contains=False),
            rec("c.com", "CredentialIdNotFound", contains=False),
        ]
        assert aggregate_verdict(records) == "InsufficientEvidence"

    def test_records_with_no_domain_are_ignored(self):
        records = [
            {"domain": None, "verdict": "IndicatesValid", "contains_credential_id": True},
            rec("b.com", "IndicatesValid"),
        ]
        assert aggregate_verdict(records) == "Unverified"

    def test_mixed_unclear_and_one_valid_is_unverified(self):
        records = [
            rec("a.com", "IndicatesValid"),
            rec("b.com", "Unclear"),
            rec("c.com", "CredentialIdNotFound", contains=False),
        ]
        assert aggregate_verdict(records) == "Unverified"

    def test_three_valid_domains_confirms(self):
        records = [
            rec("a.com", "IndicatesValid"),
            rec("b.com", "IndicatesValid"),
            rec("c.gov", "IndicatesValid"),
        ]
        assert aggregate_verdict(records) == "CredentialConfirmed"

    def test_result_is_always_within_fixed_vocabulary(self):
        scenarios = [
            [],
            [rec("a.com", "IndicatesValid")],
            [rec("a.com", "IndicatesValid"), rec("b.com", "IndicatesValid")],
            [rec("a.com", "IndicatesRevokedOrExpired")],
            [rec("a.com", "Unclear")],
        ]
        for records in scenarios:
            assert aggregate_verdict(records) in FINAL_VERDICTS
