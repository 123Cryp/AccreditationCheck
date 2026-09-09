# PROJECT_OVERVIEW.md

One-page summary — if you only read one file in this repository besides
README.md, read this one.

## What it is

A GenLayer Intelligent Contract, `AccreditationCheck`, that verifies a
claimed professional credential (license number, certification ID,
accreditation number) against independent web evidence.

## What problem it solves

A claimant asserting "I hold license #AB123456" has every incentive to
just say so. A verification check that only asks an LLM "does this page
seem to confirm the claim?" can be talked past by confident, vague prose
that never actually cites the specific ID. AccreditationCheck adds a hard
requirement: the specific claimed ID must literally appear on a page
(verified by deterministic string matching, not an LLM) before that page
can count toward corroboration at all.

## How it works, in one paragraph

For each evidence URL supplied alongside a `subject_name` and
`claimed_credential_id`, the contract fetches the page, then — with pure
string logic, no LLM — checks whether the claimed ID appears on it
(normalized for common formatting variants like dashes vs. spaces). Only
pages that pass this gate go on to an LLM judgment step, which decides
whether the page indicates the credential is currently valid, revoked/
expired, or unclear. A final verdict is computed deterministically from
the set of independent (by registrable domain) corroborating vs. revoking
sources: two or more independent domains indicating validity with no
revocation signal is `CredentialConfirmed`; any revocation signal at all
caps the result at `LikelyRevokedOrExpired` or `Disputed`; anything less
than two independent corroborating domains and no revocation signal is
`Unverified` or `InsufficientEvidence`.

## Interface

```python
submit_check(subject_name: str, claimed_credential_id: str, evidence_urls: list[str]) -> str
get_check(check_id: str) -> str
get_verdict(check_id: str) -> str
total_checks() -> int
```

## What's novel about it (vs. other GenLayer corroboration contracts)

The deterministic content gate itself — not "corroboration across
domains" in general (that pattern exists elsewhere), but specifically the
idea that an LLM is never even consulted about a page unless a fixed,
auditable, un-gameable string check has already confirmed the page
contains the specific fact being verified. See `DESIGN_DECISIONS.md` for
the full argument and `REVIEWER_GUIDE.md` for the fastest test to run to
confirm it's real, not just described.

## Current status

- **Code:** complete, single-file `contract.py`, deployable as-is.
- **Offline tests:** 117 passed, 0 failed, across 8 test files.
- **Documentation:** complete (this 12-file suite plus `tests/README.md`).
- **Live deployment:** live-verified. Deployed at
  `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d`, with finalized
  transactions demonstrating four of five final-verdict categories:
  `CredentialConfirmed` (two independent real sources both affirming an
  FDIC certificate number), `LikelyRevokedOrExpired` (the deterministic
  ID-gate excluding a non-matching real-world source), `Unverified` (a
  single real corroborating source, deliberately not enough for full
  confirmation), and `InsufficientEvidence` (real, accessible sources
  that simply don't mention the claimed ID). `Disputed` was actively
  investigated for a live example and none was found — see README.md's
  "Live deployment status" and CHANGELOG.md `[0.1.6]` for the full
  record; the category remains covered by offline tests only, which is
  a documented conclusion rather than an open task.

## Key design tradeoffs (see SECURITY.md and DESIGN_DECISIONS.md for full detail)

- ID matching proves the ID is *present*, not that the page is
  *authoritative* — the LLM step, not the gate, is responsible for
  catching context like "this page is a revocation list."
- ID matching is substring-based and line-scoped, not word-boundary-aware
  — a deliberate simplicity/auditability tradeoff.
- Registrable-domain detection uses a small hardcoded suffix list, not the
  full Public Suffix List.
- No Sybil-resistance across genuinely different domains controlled by the
  same operator — domain-identity corroboration is a proxy, not a proof,
  of independence.

## File map

See README.md's "Files in this repository" section for the complete
listing.
