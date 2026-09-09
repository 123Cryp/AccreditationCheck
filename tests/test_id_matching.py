import conftest  # noqa: F401  (sets up sys.path)
from contract import normalize_id_fragment, text_contains_credential_id


class TestNormalizeIdFragment:
    def test_lowercases(self):
        assert normalize_id_fragment("ABC123") == "abc123"

    def test_strips_dashes(self):
        assert normalize_id_fragment("AB-123-456") == "ab123456"

    def test_strips_spaces(self):
        assert normalize_id_fragment("AB 123 456") == "ab123456"

    def test_strips_mixed_punctuation(self):
        assert normalize_id_fragment("AB.123_456#") == "ab123456"

    def test_empty_string(self):
        assert normalize_id_fragment("") == ""

    def test_non_string_returns_empty(self):
        assert normalize_id_fragment(None) == ""
        assert normalize_id_fragment(12345) == ""

    def test_pure_punctuation_collapses_to_empty(self):
        assert normalize_id_fragment("---   ...") == ""

    def test_unicode_letters_stripped_non_ascii(self):
        # Non a-z0-9 characters (including accented letters) are stripped by design.
        assert normalize_id_fragment("Café-123") == "caf123"


class TestTextContainsCredentialId:
    def test_exact_match(self):
        page = "This contractor holds license AB123456 in good standing."
        assert text_contains_credential_id(page, "AB123456") is True

    def test_no_match(self):
        page = "This contractor holds license XY999999 in good standing."
        assert text_contains_credential_id(page, "AB123456") is False

    def test_formatting_variant_dashes_vs_none(self):
        page = "License number: AB-123-456, status active."
        assert text_contains_credential_id(page, "AB123456") is True

    def test_formatting_variant_spaces_vs_dashes(self):
        page = "License number: AB 123 456, status active."
        assert text_contains_credential_id(page, "AB-123-456") is True

    def test_credential_id_with_dashes_matches_plain_page(self):
        page = "Certificate ID AB123456 issued 2019."
        assert text_contains_credential_id(page, "AB-123-456") is True

    def test_case_insensitive(self):
        page = "certificate id ab123456 issued 2019."
        assert text_contains_credential_id(page, "AB123456") is True

    def test_partial_id_does_not_match(self):
        page = "License number: AB123 only, nothing further."
        assert text_contains_credential_id(page, "AB123456") is False

    def test_id_split_across_lines_does_not_match(self):
        # Deliberate boundary: normalization is line-scoped (see
        # DESIGN_DECISIONS.md), so an ID whose digits are split across two
        # separate lines must NOT match — this is the documented mitigation
        # against cross-sentence false positives.
        page = "License number: AB123\n456 continued elsewhere"
        assert text_contains_credential_id(page, "AB123456") is False

    def test_id_within_single_long_line_matches(self):
        page = "Random preamble text License AB-123-456 more text on same line"
        assert text_contains_credential_id(page, "AB123456") is True

    def test_empty_page_text(self):
        assert text_contains_credential_id("", "AB123456") is False

    def test_empty_credential_id_never_matches(self):
        # An empty/whitespace-only ID must never "match" everything.
        assert text_contains_credential_id("any page text at all", "") is False
        assert text_contains_credential_id("any page text at all", "   ") is False

    def test_non_string_page_text(self):
        assert text_contains_credential_id(None, "AB123456") is False

    def test_non_string_credential_id(self):
        assert text_contains_credential_id("some text", None) is False

    def test_id_appearing_multiple_times(self):
        page = "AB123456 mentioned once.\nAB123456 mentioned again."
        assert text_contains_credential_id(page, "AB123456") is True

    def test_id_as_substring_of_longer_token_still_matches(self):
        # Documented limitation: normalization is substring-based, so an ID
        # that happens to be a substring of a longer alphanumeric run will
        # match. This is intentionally accepted and documented in
        # SECURITY.md rather than silently "fixed" with brittle boundary
        # heuristics.
        page = "Reference code XAB123456Y appears here."
        assert text_contains_credential_id(page, "AB123456") is True
