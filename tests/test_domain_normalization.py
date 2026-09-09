import conftest  # noqa: F401
from contract import normalize_host, registrable_domain


class TestNormalizeHost:
    def test_basic_https_url(self):
        assert normalize_host("https://www.example.com/path?q=1") == "www.example.com"

    def test_basic_http_url(self):
        assert normalize_host("http://example.com") == "example.com"

    def test_scheme_missing_defaults_to_http(self):
        assert normalize_host("example.com/some/path") == "example.com"

    def test_strips_port(self):
        assert normalize_host("https://example.com:8443/x") == "example.com"

    def test_strips_userinfo(self):
        assert normalize_host("https://user:pass@example.com/x") == "example.com"

    def test_lowercases(self):
        assert normalize_host("HTTPS://EXAMPLE.COM/Path") == "example.com"

    def test_strips_trailing_dot(self):
        assert normalize_host("https://example.com./x") == "example.com"

    def test_ipv6_literal(self):
        assert normalize_host("https://[2001:db8::1]:443/x") == "2001:db8::1"

    def test_empty_string_invalid(self):
        assert normalize_host("") is None

    def test_whitespace_only_invalid(self):
        assert normalize_host("   ") is None

    def test_non_string_invalid(self):
        assert normalize_host(None) is None
        assert normalize_host(12345) is None

    def test_no_host_invalid(self):
        assert normalize_host("https:///just/a/path") is None

    def test_overlong_host_invalid(self):
        overlong = "a" * 300 + ".com"
        assert normalize_host(f"https://{overlong}/x") is None

    def test_invalid_characters_rejected(self):
        assert normalize_host("https://exa mple.com/x") is None

    def test_subdomain_preserved(self):
        assert normalize_host("https://api.sub.example.com/x") == "api.sub.example.com"


class TestRegistrableDomain:
    def test_simple_two_label_host(self):
        assert registrable_domain("example.com") == "example.com"

    def test_subdomain_reduces_to_two_labels(self):
        assert registrable_domain("www.example.com") == "example.com"

    def test_deep_subdomain_reduces_to_two_labels(self):
        assert registrable_domain("api.sub.example.com") == "example.com"

    def test_known_multi_part_suffix_co_uk(self):
        assert registrable_domain("www.bbc.co.uk") == "bbc.co.uk"

    def test_known_multi_part_suffix_com_au(self):
        assert registrable_domain("shop.example.com.au") == "example.com.au"

    def test_known_multi_part_suffix_gov_uk(self):
        assert registrable_domain("data.nhs.gov.uk") == "nhs.gov.uk"

    def test_bare_multi_part_suffix_host_with_two_labels(self):
        # "co.uk" itself, with no registrable label in front, has only 2
        # labels so the <=2-label short-circuit applies and it is returned
        # as-is; this is a known, documented edge case (see
        # DESIGN_DECISIONS.md) since a bare public suffix should never
        # legitimately be presented as evidence.
        assert registrable_domain("co.uk") == "co.uk"

    def test_single_label_host(self):
        assert registrable_domain("localhost") == "localhost"

    def test_gov_domain_two_labels(self):
        assert registrable_domain("www.cpsc.gov") == "cpsc.gov"

    def test_non_string_passthrough(self):
        assert registrable_domain(None) is None
        assert registrable_domain("") == ""
