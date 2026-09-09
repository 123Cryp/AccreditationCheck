# AccreditationCheck

[![Offline test suite](https://github.com/123Cryp/AccreditationCheck/actions/workflows/tests.yml/badge.svg)](https://github.com/123Cryp/AccreditationCheck/actions/workflows/tests.yml)

A GenLayer Intelligent Contract that verifies a claimed professional
credential (a license number, certification ID, or accreditation number)
against independent web evidence — using a **deterministic content gate**
that runs *before* any LLM judgment, so a page's confident-sounding prose
can never substitute for the claimed ID actually appearing on it.

Submitted for the GenLayer Portal Builder track, Intelligent Contracts
category.

**Repository:** https://github.com/123Cryp/AccreditationCheck

## The problem

Someone claims "ISO 9001 certified," or "licensed contractor #AB123456," or
"board-certified, license #XYZ." They have every incentive to just assert
it. A purely LLM-driven "does this page seem to confirm the credential?"
check can be talked past by vague, confident-sounding text that never
actually cites the specific ID being claimed.

## The novel mechanic

**Deterministic fact-extraction gating, before any LLM call.** For every
evidence URL, the contract:

1. Fetches the page.
2. Checks — with pure, auditable string logic, no LLM involved — whether
   the caller's claimed credential ID literally appears on the page
   (case-insensitive, formatting-normalized).
3. **Only if the ID is found** does it ask an LLM whether the page
   indicates the credential is currently valid, revoked/expired, or
   unclear.

A page that never mentions the ID is recorded as `CredentialIdNotFound` and
can never contribute to a "confirmed" verdict — no matter how favorably an
LLM might have judged its prose. This is structurally different from a
purely-LLM-judged corroboration check or a purely domain-based exclusion
rule: it's a deterministic *content* gate sitting between fetch and LLM
judgment. See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for the full
rationale and how this differs from prior corroboration-style contracts.

## Public interface

```python
submit_check(subject_name: str, claimed_credential_id: str, evidence_urls: list[str]) -> str   # returns check_id
get_check(check_id: str) -> str      # full JSON record, including per-evidence detail
get_verdict(check_id: str) -> str    # just the final verdict string
total_checks() -> int
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full data model and
[SECURITY.md](SECURITY.md) for known limitations.

## Files in this repository

```
contract.py                          # the contract — single file, deployable as-is
tests/
  conftest.py                        # wires the offline stub onto sys.path
  genlayer_stub/genlayer/            # offline genlayer SDK stub (see ARCHITECTURE.md)
  test_id_matching.py
  test_domain_normalization.py
  test_llm_verdict_parsing.py
  test_aggregation.py
  test_stub_hardening.py
  test_lint_e022.py
  test_runner_header.py
  test_contract_integration.py
  README.md                          # coverage index
README.md                            # this file
ARCHITECTURE.md
SECURITY.md
DESIGN_DECISIONS.md
TESTING.md
CHANGELOG.md
ROADMAP.md
CONTRIBUTING.md
REVIEWER_GUIDE.md
PROJECT_OVERVIEW.md
SUBMISSION_CHECKLIST.md
LICENSE
```

## Running the tests

```bash
pip install pytest
cd AccreditationCheck
pytest tests/ -v
```

**Current offline result: 117 passed, 0 failed**, across 8 test files. See
[TESTING.md](TESTING.md) for the full breakdown by file and what each file
covers.

## Live deployment status

**Live-verified.** Deployed to GenLayer Studio and confirmed via four
real, finalized transactions covering four different final-verdict
categories.

- **Deployed contract address (current, official):**
  `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d`
  ([explorer](https://explorer-studio.genlayer.com/address/0xC9E10e8212685F5767126C6AEE715E2B046F5A8d))

  Note: an earlier deployment at
  `0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB` was used for the first
  round of live testing (see CHANGELOG.md `[0.1.2]`) and was superseded by
  a fresh redeploy to the address above before the second round of
  testing. The address above is the one to treat as current/official.

- **`submit_check` transaction #1 — demonstrates `CredentialConfirmed`:**
  `0x0ea09a1ab72b586eda51fcaed29dc3e78942453edf09d3dd4bef78cfc4daa6fa` —
  FINALIZED / SUCCESS

  ```
  subject_name = "JPMorgan Chase Bank N.A. FDIC Insurance Test"
  claimed_credential_id = "628"
  evidence_urls = [
    "https://www.bankregreports.com/banks/jpmorgan-chase-bank-national-association-852218/",
    "https://laneguide.com/findroutingnumbers/021000306~RoutingNumber"
  ]
  ```
  Both are real, independent pages (different registrable domains) that
  each state JPMorgan Chase Bank, N.A.'s FDIC Certificate is 628/00628 in
  a context affirming current status. Result (`get_check("check-0")`):
  ```json
  {
    "check_id": "check-0",
    "subject_name": "JPMorgan Chase Bank N.A. FDIC Insurance Test",
    "claimed_credential_id": "628",
    "submitted_by": "0xBD767E1958928ff1CAaE1218dbCb4b2f2ada35F6",
    "evidence": [
      {
        "url": "https://www.bankregreports.com/banks/jpmorgan-chase-bank-national-association-852218/",
        "domain": "bankregreports.com",
        "is_duplicate_domain": false,
        "contains_credential_id": true,
        "fetch_status": "ok",
        "verdict": "IndicatesValid"
      },
      {
        "url": "https://laneguide.com/findroutingnumbers/021000306~RoutingNumber",
        "domain": "laneguide.com",
        "is_duplicate_domain": false,
        "contains_credential_id": true,
        "fetch_status": "ok",
        "verdict": "IndicatesValid"
      }
    ],
    "final_verdict": "CredentialConfirmed"
  }
  ```
  `get_verdict("check-0")` → `"CredentialConfirmed"` — matches.

- **`submit_check` transaction #2 — demonstrates `LikelyRevokedOrExpired`
  and the deterministic ID-gate excluding a source:**
  `0xc50ca9bf415d3baf1197a385eecce52fada716e5d2a5597131250ad0331f617b` —
  FINALIZED / SUCCESS

  ```
  subject_name = "Rattan 6-Drawer Dresser Recall Test"
  claimed_credential_id = "26-172"
  evidence_urls = ["https://www.cpsc.gov/node/65727", "https://www.cpsc.gov/node/65729"]
  ```
  `node/65727` is a real CPSC recall notice literally containing
  "Recall number: 26-172"; `node/65729` is a different real CPSC recall
  notice (recall number 26-174) that does **not** contain "26-172".
  Result (`get_check("check-1")`):
  ```json
  {
    "check_id": "check-1",
    "subject_name": "Rattan 6-Drawer Dresser Recall Test",
    "claimed_credential_id": "26-172",
    "submitted_by": "0xBD767E1958928ff1CAaE1218dbCb4b2f2ada35F6",
    "evidence": [
      {
        "url": "https://www.cpsc.gov/node/65727",
        "domain": "cpsc.gov",
        "is_duplicate_domain": false,
        "contains_credential_id": true,
        "fetch_status": "ok",
        "verdict": "IndicatesRevokedOrExpired"
      },
      {
        "url": "https://www.cpsc.gov/node/65729",
        "domain": "cpsc.gov",
        "is_duplicate_domain": true,
        "contains_credential_id": false,
        "fetch_status": "ok",
        "verdict": "CredentialIdNotFound"
      }
    ],
    "final_verdict": "LikelyRevokedOrExpired"
  }
  ```
  `get_verdict("check-1")` → `"LikelyRevokedOrExpired"` — matches.
  `total_checks()` → `2` — matches (two checks submitted on this
  contract instance).

  **What this proves live, not just offline:** the source that did not
  contain the claimed ID (`node/65729`) was excluded from corroboration
  via `contains_credential_id: false` / `verdict: "CredentialIdNotFound"`
  — the deterministic gate ran before, and independently of, any LLM
  judgment. This matches
  `test_contract_integration.py::TestDeterministicIdGate` exactly, live.

- **`submit_check` transaction #3 — demonstrates `Unverified`:**
  `0xeeec72658107511bf1bc459359a5feefe4151598ce78ab9ac49a80895898c0e8` —
  FINALIZED / SUCCESS

  ```
  subject_name = "JPMorgan Chase Bank N.A. Single-Source Test"
  claimed_credential_id = "628"
  evidence_urls = ["https://www.bankregreports.com/banks/jpmorgan-chase-bank-national-association-852218/"]
  ```
  Same real, ID-matching source as transaction #1 above, but submitted
  **alone** (a single corroborating domain, not two independent ones).
  Result: `contains_credential_id: true`, `verdict: "IndicatesValid"` for
  the one source, and — because `aggregate_verdict` requires at least two
  independent corroborating domains for `CredentialConfirmed` — `check-3`
  came back `final_verdict: "Unverified"`, confirmed via
  `get_verdict("check-3")` → `"Unverified"`.

  **What this proves live:** a single favorable source, however clearly
  worded, is deliberately not enough for full confirmation — matching
  `test_aggregation.py::test_single_valid_domain_is_unverified_not_confirmed`,
  live.

- **`submit_check` transaction #4 — demonstrates `InsufficientEvidence`:**
  `0x65203140f57eae9de08466885af8a0908aafc22627de459a3075dcfb299c6434` —
  FINALIZED / SUCCESS

  ```
  subject_name = "Fictional Credential InsufficientEvidence Test"
  claimed_credential_id = "ZZ-000000"
  evidence_urls = ["https://www.cpsc.gov/node/65727", "https://www.cpsc.gov/node/65729"]
  ```
  Same two real, accessible CPSC pages as transaction #2, but with a
  deliberately fictional claimed ID that appears on neither. Both sources
  came back `fetch_status: "ok"`, `contains_credential_id: false`,
  `verdict: "CredentialIdNotFound"` — accessible, real evidence that
  simply never mentions the claimed ID. Result (`check-4`):
  `final_verdict: "InsufficientEvidence"`, confirmed via
  `get_verdict("check-4")` → `"InsufficientEvidence"`.

  **What this proves live:** pages being real and fetchable is not
  enough on its own — with zero corroborating or revoking signal (every
  source `CredentialIdNotFound`), the contract correctly declines to
  confirm anything either way, rather than defaulting to a false
  positive or false negative.

- **Verdict categories with a live example so far:** `CredentialConfirmed`,
  `LikelyRevokedOrExpired`, `Unverified`, `InsufficientEvidence`.
  `Disputed` was actively investigated for a live example (real FDIC
  certificate numbers of failed banks, real CPSC/FDA recall numbers
  republished on secondary sites) and none was found — real-world sources
  that cite the same specific credential ID essentially always trace back
  to one canonical issuing authority and agree with each other once they
  include the ID at all, rather than genuinely disagreeing. See
  CHANGELOG.md `[0.1.6]` for the full investigation record. `Disputed`
  remains covered by `test_aggregation.py` and
  `test_contract_integration.py` offline.
- **Note on `check-2`:** `total_checks()` is `4` on this contract
  (`check-0` through `check-3`), one more than the three transactions
  documented above. `check-2` was a repeat of the recall scenario
  (`LikelyRevokedOrExpired`) run between transactions #2 and #3 above; its
  exact transaction hash wasn't captured for this document, but its
  `get_verdict("check-2")` result was confirmed as `"LikelyRevokedOrExpired"`,
  consistent with transaction #2. Recorded here rather than silently
  omitted, per this project's documentation-honesty standard.
- **Consensus notes:** both transactions finalized as `ACCEPTED`/`SUCCESS`
  with fewer than all validators reporting `Agree` — one validator
  disagreed on transaction #2's `IndicatesRevokedOrExpired` judgment
  page's predecessor run, and two validators showed
  `ERROR / Idle — Validator execution cancelled after quorum` on
  transaction #2 (this specific message means those validators simply
  didn't need to finish once quorum was already reached, not that they
  failed). See SECURITY.md's consensus note for what this does and
  doesn't imply.

**Reminders still relevant for future live testing** (see
[ROADMAP.md](ROADMAP.md) and [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md)):
- Type real JSON arrays into the `evidence_urls` field before submitting.
- If Studio shows "Could not load contract schema", check the runner
  header first (must be a pinned hash, not `:latest`/`:test` — see
  CHANGELOG.md `[0.1.1]`) before assuming it's the client-side caching
  bug (hard refresh → clear site data → incognito).
- Avoid `britannica.com`, `reuters.com`, `investopedia.com`, and
  `ftc.gov` as live evidence URLs — they have returned
  `fetch_status: "inaccessible"` in real transactions on prior projects.
  `cpsc.gov`, `bankregreports.com`, and `laneguide.com` all worked
  reliably for this project's live tests.
- If redeploying, note the new contract address will start its own
  `check_ids`/`checks` storage from scratch (`check-0` again) — this is
  expected, not a bug; it's a fresh contract instance.

## License

MIT — see [LICENSE](LICENSE).
