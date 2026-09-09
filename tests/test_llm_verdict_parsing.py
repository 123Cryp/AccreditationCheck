import conftest  # noqa: F401
from contract import parse_llm_verdict


class TestParseLlmVerdict:
    def test_exact_match_valid(self):
        assert parse_llm_verdict("IndicatesValid") == "IndicatesValid"

    def test_exact_match_revoked(self):
        assert parse_llm_verdict("IndicatesRevokedOrExpired") == "IndicatesRevokedOrExpired"

    def test_exact_match_unclear(self):
        assert parse_llm_verdict("Unclear") == "Unclear"

    def test_case_insensitive(self):
        assert parse_llm_verdict("indicatesvalid") == "IndicatesValid"
        assert parse_llm_verdict("INDICATESVALID") == "IndicatesValid"

    def test_whitespace_collapsed(self):
        assert parse_llm_verdict("  IndicatesValid  ") == "IndicatesValid"

    def test_scans_every_line_not_just_first(self):
        raw = "Here is my reasoning about the page.\nIndicatesRevokedOrExpired\n"
        assert parse_llm_verdict(raw) == "IndicatesRevokedOrExpired"

    def test_scans_last_line(self):
        raw = "Line one is filler.\nLine two is also filler.\nUnclear"
        assert parse_llm_verdict(raw) == "Unclear"

    def test_prefers_first_matching_line_when_multiple_present(self):
        raw = "IndicatesValid\nIndicatesRevokedOrExpired"
        assert parse_llm_verdict(raw) == "IndicatesValid"

    def test_unparseable_defaults_to_unclear(self):
        assert parse_llm_verdict("I cannot determine this from the page.") == "Unclear"

    def test_empty_string_defaults_to_unclear(self):
        assert parse_llm_verdict("") == "Unclear"

    def test_none_defaults_to_unclear(self):
        assert parse_llm_verdict(None) == "Unclear"

    def test_non_string_defaults_to_unclear(self):
        assert parse_llm_verdict(12345) == "Unclear"

    def test_extra_punctuation_on_line_does_not_match(self):
        # A close-but-not-exact line (with trailing punctuation) is treated
        # as unparseable for that line rather than fuzzy-matched, per the
        # fixed-vocabulary design (see DESIGN_DECISIONS.md).
        raw = "IndicatesValid."
        assert parse_llm_verdict(raw) == "Unclear"

    def test_never_returns_a_value_outside_llm_vocab(self):
        from contract import LLM_VERDICTS
        for candidate in ["", None, "garbage", "CredentialIdNotFound", "NoEvidence"]:
            assert parse_llm_verdict(candidate) in LLM_VERDICTS
