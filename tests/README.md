# tests/README.md — coverage index

**Current result: 117 passed, 0 failed** (run `pytest tests/ -v` from the
project root to reproduce; re-run before trusting this number if
`contract.py` has changed since this file was last updated).

This file lists every test, grouped by file, as a coverage index for
reviewers and future contributors. See `../TESTING.md` for the narrative
version (what each file covers and why) and `../ARCHITECTURE.md` for how
the offline `genlayer` stub in `genlayer_stub/` works.

## test_id_matching.py (23 tests)

`TestNormalizeIdFragment`: lowercasing, dash stripping, space stripping,
mixed-punctuation stripping, empty string, non-string input, pure
punctuation, non-ASCII letter stripping.

`TestTextContainsCredentialId`: exact match, no match, formatting-variant
matches (dashes→plain, spaces→dashes, dashes→plain reversed),
case-insensitivity, partial-ID non-match, cross-line non-match (line-scope
boundary), same-line match with surrounding text, empty page text, empty/
whitespace-only credential ID never matches, non-string page text,
non-string credential ID, ID appearing multiple times, substring-of-
longer-token match (documented limitation, tested deliberately).

## test_domain_normalization.py (25 tests)

`TestNormalizeHost`: basic https/http URLs, missing scheme, port
stripping, userinfo stripping, lowercasing, trailing-dot stripping, IPv6
literal, empty string, whitespace-only, non-string input, no-host input,
overlong host, invalid characters, subdomain preservation.

`TestRegistrableDomain`: simple two-label host, subdomain reduction (one
and multiple levels), known multi-part suffixes (`co.uk`, `com.au`,
`gov.uk`), bare-suffix edge case, single-label host, two-label `.gov`
domain, non-string/empty passthrough.

## test_llm_verdict_parsing.py (14 tests)

`TestParseLlmVerdict`: exact match for each of the three LLM verdicts,
case-insensitivity, whitespace collapsing, scanning every line (not just
first, not just last), preferring the first matching line when multiple
are present, unparseable/empty/None/non-string input defaulting to
`Unclear`, punctuation-suffixed near-miss not fuzzy-matched, and a
property test confirming output is always within `LLM_VERDICTS`.

## test_aggregation.py (13 tests)

`TestAggregateVerdict`: two independent valid domains confirms; a single
valid domain is `Unverified` not `CredentialConfirmed`; the same domain
appearing twice doesn't double-count; any revocation with no valid signal
is `LikelyRevokedOrExpired`; revocation + valid together is `Disputed`;
two valid + one revoked is *still* `Disputed` (asymmetric rule); no signal
at all is `InsufficientEvidence`; empty evidence list is
`InsufficientEvidence`; many `CredentialIdNotFound` records never
contribute; records with no domain are ignored; mixed unclear + one valid
is `Unverified`; three valid domains confirms; a property test confirming
output is always within `FINAL_VERDICTS`.

## test_stub_hardening.py (12 tests)

Tests of the offline stub **itself**, not contract logic — see
`../TESTING.md`'s "What the offline stub does and does not verify"
section for why these are treated as first-class tests.

`TestAddressHardening`: wrapping an `Address` raises `TypeError`;
constructing from a hex string works; constructing from bytes works;
constructing from an invalid type raises `TypeError`.

`TestDataclassNotExported`: `dataclass` is absent from `genlayer`'s
module namespace / `__all__`.

`TestDynArrayConstructionRestrictions`: zero-arg construction raises;
one-arg construction raises; `gl.storage.inmem_allocate` raises the
documented DynArray-specific internal error.

`TestTreeMapConstructionRestrictions`: zero-arg construction raises;
one-arg construction raises; `gl.storage.inmem_allocate` *works* for
TreeMap (confirming the stub doesn't over-block).

`TestContractTopLevelZeroInit`: a sample `gl.Contract` subclass's
top-level `DynArray`/`TreeMap` fields are immediately usable
(`.append()`/`[key] =`) with no explicit construction.

## test_lint_e022.py (4 tests)

`TestLintRuleE022`: the contract class (`AccreditationCheck`, subclassing
`gl.Contract`) is found via AST; no method anywhere in `contract.py` uses
`@classmethod`/`@staticmethod`; every method defined directly on the
contract class has `self` as its first parameter; none of the seven
module-level pure helper functions were accidentally defined inside the
class body without `self`.

## test_runner_header.py (3 tests)

`TestRunnerHeaderIsPinned`: line 2 of `contract.py` is a `{"Depends": ...}`
header containing `py-genlayer:`; the tag after the colon is not the
alias `latest` or `test` (GenVM rejects these outside Debug mode — found
live, see `../CHANGELOG.md` `[0.1.1]`); the tag is long enough to plausibly
be a pinned hash rather than a short alias typo.

## test_contract_integration.py (23 tests)

Full pipeline tests against the offline stub, with `stub_control` reset
before and after every test via an autouse fixture.

`TestPreflightValidation` (6): empty/whitespace-only subject name rejected,
empty credential ID rejected, empty evidence URLs rejected, too-many
evidence URLs rejected, and confirmation that validation happens *before*
any fetch attempt (would raise a different exception type if fetch were
attempted first).

`TestDeterministicIdGate` (2): a non-matching source is excluded from
corroboration even with a stub LLM configured to answer favorably for any
prompt; two matching domains confirm while a non-matching third
contributes nothing.

`TestIdPresentButRevoked` (1): an ID appearing on a revocation-list page
correctly produces `IndicatesRevokedOrExpired` at the per-evidence level
and `LikelyRevokedOrExpired` at the final-verdict level — not
`CredentialConfirmed`.

`TestFetchFailureHandling` (4): inaccessible page → `NoEvidence`/
`InsufficientEvidence`; invalid URL recorded without attempting fetch;
empty page text treated as `NoEvidence`; mixed success/failure sources in
one submission.

`TestDuplicateDomainDetection` (2): first occurrence not flagged, second
occurrence on the same domain is; two same-domain matching pages don't
satisfy the two-independent-domain confirmation requirement.

`TestViewMethods` (7): `get_check`/`get_verdict` on an unknown ID both
raise `gl.vm.UserError`; `get_verdict` matches `get_check`'s
`final_verdict`; `total_checks` starts at zero and increments correctly;
check IDs are distinct; `submitted_by` correctly records the configured
sender address.

`TestStorageIsolation` (1): two separate contract instances do not share
mutable storage state.
