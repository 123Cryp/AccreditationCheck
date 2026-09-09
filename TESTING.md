# TESTING.md

## Current status

**Offline: 117 tests passed, 0 failed**, across 8 test files.
**Live: verified.** Deployed to GenLayer Studio at
`0xC9E10e8212685F5767126C6AEE715E2B046F5A8d`, with finalized
`submit_check` transactions covering four different final-verdict
categories: `CredentialConfirmed`, `LikelyRevokedOrExpired` (also
specifically demonstrating the deterministic ID-gate excluding a
non-matching source), `Unverified`, and `InsufficientEvidence`. See
README.md's "Live deployment status" section for the full transaction
detail and JSON output — that section is the single source of truth for
live-verification claims.

Only `Disputed` remains offline-tested only at this point — and this is
now a confirmed, investigated conclusion rather than a pending task. See
"Coverage gaps acknowledged, not hidden" below and CHANGELOG.md `[0.1.6]`
for the investigation record.

## How to run

```bash
pip install pytest
cd AccreditationCheck
pytest tests/ -v
```

`tests/conftest.py` inserts `tests/genlayer_stub/` onto `sys.path` ahead
of everything else, so `contract.py`'s `from genlayer import *` resolves
to the offline stub rather than requiring a real GenVM environment. No
network access, GenLayer Studio, or live validator set is required to run
this suite.

## Test files and what each one covers

| File | Tests | What it covers |
|---|---|---|
| `test_id_matching.py` | 23 | `normalize_id_fragment` and `text_contains_credential_id` — exact match, no match, formatting-variant matches (dashes/spaces/punctuation, in both directions), case-insensitivity, the line-scoped-normalization boundary case, empty/None inputs, and the documented substring-false-positive limitation. |
| `test_domain_normalization.py` | 25 | `normalize_host` (scheme handling, port/userinfo stripping, IPv6 literals, trailing dots, overlong/invalid input) and `registrable_domain` (two-label hosts, subdomain reduction, known multi-part suffixes, edge cases). |
| `test_llm_verdict_parsing.py` | 14 | `parse_llm_verdict`'s fixed-vocabulary scanning: exact match, case-insensitivity, whitespace collapsing, scanning every line (not just the first), safe fallback to `Unclear` on anything unparseable including near-miss punctuation. |
| `test_aggregation.py` | 13 | `aggregate_verdict`'s five-branch rule in isolation, including the asymmetric revocation-outweighs-corroboration case, the same-domain-doesn't-double-count case, and the single-domain-is-Unverified-not-Confirmed case. |
| `test_stub_hardening.py` | 12 | The offline `genlayer` stub **itself** — Address double-wrap rejection, `dataclass` absence from the stub's star-export surface, `DynArray`/`TreeMap` direct-construction rejection, and the `inmem_allocate` DynArray-vs-TreeMap quirk. These are meta-tests: if any fail, the rest of the suite's guarantees about matching live GenVM behavior are suspect. |
| `test_lint_e022.py` | 4 | Static AST inspection of `contract.py` confirming no `@classmethod`/`@staticmethod` decorators anywhere and that every method on the contract class has `self` as its first parameter (GenVM lint rule E022). |
| `test_runner_header.py` | 3 | Static check that the `{"Depends": ...}` runner header uses a pinned hash, not an alias tag like `:latest`/`:test` — added after this exact issue was found live in Studio (see CHANGELOG.md `[0.1.1]`). |
| `test_contract_integration.py` | 23 | Full `submit_check`/`get_check`/`get_verdict`/`total_checks` pipeline: pre-flight validation, the deterministic-ID-gate-excludes-a-source case (with a deliberately favorable-LLM-configured non-matching source, to prove the gate — not luck — is what excludes it), the "ID present but revoked" scenario, fetch failure and invalid-URL handling, duplicate-domain detection, and view-method behavior including unknown-`check_id` errors and storage isolation across instances. |

See `tests/README.md` for the same table with individual test names, kept
in sync as a coverage index.

## What the offline stub does and does not verify

**Does verify** (because it's hardened to reproduce the exact documented
GenVM behavior, not because it's a full GenVM reimplementation):
- `Address(gl.message.sender_address)` double-wrapping raises the same
  `TypeError` real GenVM raises.
- `dataclass` is not silently available if the explicit
  `from dataclasses import dataclass` import were ever removed from
  `contract.py`.
- Direct construction of `DynArray[T]`/`TreeMap[K, V]` (with or without
  arguments) raises the same class of `TypeError` real GenVM raises, and
  `gl.storage.inmem_allocate` reproduces the documented DynArray-specific
  quirk.
- Top-level `DynArray[str]`/`TreeMap[str, str]` contract fields are usable
  immediately without explicit construction, matching the documented
  correct pattern.

**Does not, and cannot, verify:**
- Actual multi-validator consensus behavior for `gl.eq_principle.strict_eq`
  (the stub simply calls the wrapped function once — there is no simulated
  disagreement between validators, because there is only one "validator"
  offline).
- Real network fetch behavior of `gl.nondet.web.render` for any actual
  URL, including the documented unreliability of specific domains (see
  SECURITY.md #4) — `stub_control.web_pages` is entirely test-configured.
- Real LLM output for `gl.nondet.exec_prompt` — `stub_control.llm_responses`
  is entirely test-configured pattern-matching, not a real model call.
- Gas/cost behavior, actual transaction rollback formatting in Studio, or
  any of the Studio UI-layer behaviors described in the guardrails
  (schema-panel caching bug, view-vs-write error display differences).
  These can only be confirmed live.
- Runner/dependency-header validity (`{"Depends": "py-genlayer:<tag>"}`) —
  the stub has no concept of GenVM runners at all. `test_runner_header.py`
  adds a cheap static regex check (not an alias tag) after this exact
  class of failure was found live once already; it cannot verify the
  pinned hash actually resolves, only that it isn't an alias.

This gap is exactly why README.md is explicit that offline pass count and
live-verification status are two separate, independently-tracked claims —
117/117 offline is a real, checkable number, and it is now backed by one
real, finalized live transaction (see README.md's "Live deployment
status"), but the two remain independently tracked: a future offline-only
regression wouldn't be caught by the existing live transaction, and a
future live-only GenVM behavior change wouldn't be caught by the existing
offline suite alone.

## Coverage gaps acknowledged, not hidden

Per guardrail #12: finding a real, live web page that cleanly demonstrates
a genuine `Disputed` verdict (independent sources actively disagreeing
about the same underlying fact, not merely differing on scope/detail) is
harder than finding sources that merely corroborate each other. **This
was tested, not just anticipated.** A real investigation was carried out
(see CHANGELOG.md `[0.1.6]`): real FDIC certificate numbers of banks
closed by regulators (checking whether any stale third-party directory
still cited the same certificate as currently valid) and real CPSC/FDA
recall numbers republished on secondary sites (checking whether any
retailer or blog cited the same recall number with a positive framing).
Neither produced a genuine disagreement — sources that cite a specific
credential ID at all overwhelmingly trace back to one canonical issuing
authority and agree with it, rather than contradicting it; sources that
disagree in tone (e.g. a retailer still marketing a product positively)
essentially never cite the specific ID string in their text, so the
deterministic gate excludes them regardless of tone. `Disputed` remains
covered only by the offline tests in `test_aggregation.py` and
`test_contract_integration.py`, and that is now a documented, evidenced
conclusion rather than an open task.
