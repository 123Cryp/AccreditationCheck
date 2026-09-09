# DESIGN_DECISIONS.md

This document records the deliberate design choices this project asked to
be made explicitly rather than accidentally, plus a few more that came up
during implementation. Each entry states the decision, the alternative(s)
considered, and why the chosen option won.

## What makes this project not "materially duplicative"

Prior GenLayer corroboration-style contracts (referenced generically here,
not named, per Portal review norms) have used one of two verdict
strategies: **purely LLM-judged** ("does this page seem to confirm X?")
or **purely structural** (domain-count/domain-diversity thresholds with no
content-level gate at all). AccreditationCheck's novel mechanic is a
**deterministic content gate that sits between fetch and LLM judgment**:
before any LLM call, pure string logic decides whether the claimed
credential ID literally appears on the page, and pages that fail this gate
are permanently excluded from corroboration regardless of how favorably an
LLM might otherwise have judged their prose. This is not a "different
topic wrapped around the same corroboration skeleton" — it introduces a
new pipeline stage (deterministic fact-extraction) that didn't exist in
either prior strategy, and the entire per-evidence verdict vocabulary
(`CredentialIdNotFound` in particular) exists specifically to represent
its outcome. See `tests/test_contract_integration.py::TestDeterministicIdGate`
for the test that would fail if this gate were silently bypassed or
ignored.

## ID matching: normalized substring, line-scoped

**Decision:** normalize both the claimed ID and each line of page text by
stripping all non-alphanumeric characters and lowercasing, then check
substring containment — applied per line, not to the whole document
collapsed into one string.

**Alternatives considered:**
- *Exact substring match, no normalization.* Rejected: real license/
  certificate numbers are formatted inconsistently across sources
  (`AB-123-456` vs `AB123456` vs `AB 123 456`), and exact matching would
  produce false negatives for the exact scenario this contract exists to
  catch — an ID that IS present but formatted differently than the
  caller typed it.
- *Word-boundary-aware normalized matching* (e.g. requiring the match not
  be immediately preceded/followed by another alphanumeric character).
  Rejected for this version: real-world ID formats vary enough (some
  licenses embed the number directly adjacent to a prefix/suffix with no
  separator) that boundary heuristics risked introducing false negatives
  at least as often as they'd prevent false positives, for a check whose
  entire value proposition is being simple and auditable. Documented as
  an accepted limitation in SECURITY.md rather than "fixed" with fragile
  heuristics.
- *Document-wide normalization* (strip all whitespace/punctuation from the
  entire page text as one string, then substring-match). Rejected:
  this creates a specific, worse false-positive mode where numbers from
  entirely unrelated sentences can become adjacent once all whitespace is
  removed. Line-scoped normalization was chosen as a mitigation — it
  doesn't eliminate false positives entirely (see SECURITY.md) but
  meaningfully narrows the blast radius of the concatenation failure mode
  to within a single line/paragraph fragment rather than an entire
  document.

**Boundary tests covering this decision directly** (not incidental):
`test_id_matching.py::test_formatting_variant_dashes_vs_none`,
`test_credential_id_with_dashes_matches_plain_page`,
`test_partial_id_does_not_match`,
`test_id_split_across_lines_does_not_match`,
`test_id_as_substring_of_longer_token_still_matches`.

## Verdict vocabulary placement of `CredentialIdNotFound`

**Decision:** include `CredentialIdNotFound` directly in the per-evidence
`verdict` fixed vocabulary (alongside `IndicatesValid`,
`IndicatesRevokedOrExpired`, `Unclear`, `NoEvidence`), rather than
representing "ID not found" purely via the `contains_credential_id: False`
flag plus a `fetch_status` value.

**Alternative considered:** leave `verdict` unset/null for pages that fail
the ID gate, and require every consumer to check
`contains_credential_id` first before looking at `verdict` at all.

**Why the chosen option won:** every per-evidence record is now
self-describing from a single field. `aggregate_verdict` (and any future
consumer — a UI, an analytics query, another contract) only needs to
inspect `verdict` to know what happened for that source; it never needs to
branch on `contains_credential_id` to know whether `verdict` is even
meaningful. The tradeoff is a small amount of redundancy
(`contains_credential_id: False` and `verdict: "CredentialIdNotFound"`
both encode the same underlying fact) — accepted deliberately in exchange
for a single source of truth for downstream logic.

## Final verdict aggregation rule

**Decision (see `aggregate_verdict` in `contract.py`):**

1. If both a corroborating (`IndicatesValid`) and a revoking
   (`IndicatesRevokedOrExpired`) domain exist → `Disputed`, regardless of
   how many of each.
2. Else if any revoking domain exists → `LikelyRevokedOrExpired`, even
   just one.
3. Else if at least **two** independent corroborating domains exist →
   `CredentialConfirmed`.
4. Else if exactly one corroborating domain exists → `Unverified`.
5. Else → `InsufficientEvidence`.

**Why revocation outweighs corroboration asymmetrically (step 1 vs. a
simple majority vote):** a false "confirmed" (telling someone a revoked
credential is valid) is more costly than a false "disputed" (telling
someone to look closer at a credential that's actually fine). Two sources
saying "valid" plus one saying "revoked" is `Disputed`, not
`CredentialConfirmed` — the presence of ANY revocation signal is treated
as sufficient reason to stop short of full confirmation, even when
outnumbered. Tested directly:
`test_aggregation.py::test_two_valid_plus_one_revoked_is_still_disputed`.

**Why two independent domains, not one, for `CredentialConfirmed`:** a
single source — however clearly worded — could be wrong, outdated, or
itself downstream of the same original (possibly false) claim. Requiring
two *independent registrable domains* (not just two URLs, which could be
two pages on the same site) is the corroboration bar. A lone corroborating
domain resolves to `Unverified`, not `CredentialConfirmed`, so that a
one-source "valid" reads honestly as "not yet independently corroborated"
rather than as full confirmation. Tested directly:
`test_aggregation.py::test_single_valid_domain_is_unverified_not_confirmed`
and `test_same_domain_twice_does_not_double_count`.

## Registrable-domain suffix list scope

**Decision:** use a small, hardcoded set of ~25 well-known multi-part
suffixes rather than depending on the full Mozilla Public Suffix List (a
frequently-updated external data file with several thousand entries).

**Why:** this project's single-file, no-external-dependency deployment
model (`contract.py`, deployable as-is, a single pinned
`{"Depends": "py-genlayer:<hash>"}` header, no other files) is a deliberate constraint. Vendoring or fetching the full PSL would
either bloat the single file dramatically or require a network fetch at
contract-load time, neither of which fits a Portal Builder track
submission whose evidence sources are themselves already `.gov`/major news
domains that are well covered by the hardcoded set. The gap this leaves is
documented honestly in SECURITY.md rather than silently accepted.

## Fixed-vocabulary LLM parsing: scan every line, exact match only

**Decision:** `parse_llm_verdict` scans every line of the raw LLM response
(not just the first non-empty line) for a case-insensitive,
whitespace-collapsed **exact** match against the three allowed LLM
verdicts, and falls back to `Unclear` — the most conservative available
category — on anything unparseable, including near-misses like
`"IndicatesValid."` (trailing punctuation) which are deliberately *not*
fuzzy-matched.

**Why not the first line only:** LLMs sometimes preface a one-word answer
with a short reasoning line despite explicit instructions not to. Scanning
every line makes parsing robust to that without requiring a stricter (and
more fragile) prompt.

**Why not fuzzy/substring matching against the vocabulary:** a
closed-vocabulary output is only as trustworthy as its parser. Fuzzy
matching (e.g. accepting `"valid"` as a match for `"IndicatesValid"`)
reintroduces exactly the kind of ambiguity the fixed-vocabulary pattern
exists to eliminate — it would make it possible for LLM output that never
actually said any of the three exact allowed strings to still get
categorized as if it had. Tested directly:
`test_llm_verdict_parsing.py::test_extra_punctuation_on_line_does_not_match`.

## Pre-flight validation before any `gl.nondet.*` call

**Decision:** `submit_check` validates `subject_name`,
`claimed_credential_id`, and `evidence_urls` (non-empty, within a max
count) with plain deterministic Python, and raises `gl.vm.UserError`
immediately on failure, *before* any fetch or LLM call for any URL.

**Why:** an obviously-insufficient submission (empty subject name, no
evidence URLs, too many URLs) should never cost validators a single fetch
or LLM call. This is not a formatting hard requirement (it doesn't govern
determinism), it's a cost-and-ergonomics decision that costs nothing to
implement and is directly testable offline with zero stub configuration
(`test_contract_integration.py::TestPreflightValidation`,
including `test_preflight_rejects_before_any_fetch`, which would fail
loudly if validation order were ever accidentally reversed).

## Storage schema: JSON string, not nested storage types

Covered in full in ARCHITECTURE.md's "Storage schema discipline" section;
summarized here as a decision record: given a confirmed real-GenVM
limitation that `DynArray[T]` cannot be user-constructed under any
circumstance (including nested inside another dataclass built fresh in
memory), the per-check "list of evidence records" relationship is
represented as a single `str` field holding `json.dumps(...)` of a plain
list of dicts, read back with `json.loads(...)` in view methods. `str` has
no such construction restriction. This was decided at schema-design time,
before writing `contract.py`, specifically to avoid discovering the
limitation only after the fact.
