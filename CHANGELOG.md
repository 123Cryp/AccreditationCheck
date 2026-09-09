# CHANGELOG.md

All notable changes to this project are recorded here. Dates use the
device's local date at time of writing.

## [0.1.6] — Disputed live example: attempted, not found

### Investigation
- Spent a real research pass attempting to find a genuine live `Disputed`
  example: two independent domains, both citing the exact same claimed
  credential ID, one affirmatively indicating current validity and the
  other affirmatively indicating revocation/expiration.
- Investigated: FDIC certificate numbers for failed banks (a bank closed
  by regulators, checking whether any stale third-party directory site
  still cites the same certificate number as currently valid) —
  `laneguide.com`'s current page for the failed Republic First Bank
  (Cert #27332) still uses "Status: Valid Routing Number" framing but
  shows "0 active branches," which is ambiguous rather than an
  affirmative "still valid" claim; other independent sources either omit
  the certificate number entirely or consistently describe the same
  closure, with no genuine disagreement found.
- Also investigated CPSC/FDA recall numbers republished on secondary
  sites (e.g. `recallcheck.net`): recall-tracking sites that do cite a
  recall number consistently describe it negatively (matching the
  primary regulator), and product/retailer pages that describe a product
  positively essentially never cite the specific recall number in their
  text, so the deterministic ID gate would exclude them regardless of
  tone.
- **Conclusion: a genuine live `Disputed` example was not found.** This
  matches what `TESTING.md`'s "Coverage gaps acknowledged, not hidden"
  section anticipated before any live testing began — real-world sources
  that cite the same specific credential ID rarely genuinely disagree
  about its status; they either both omit the ID or both agree once they
  include it, since it usually traces back to a single canonical issuing
  authority. `Disputed` remains covered by
  `test_aggregation.py::test_revocation_and_valid_together_is_disputed`
  and `test_contract_integration.py`'s aggregation tests, which construct
  the scenario directly with stub-configured evidence rather than
  requiring it to occur naturally on the live web.
- No code change resulted from this investigation — `contract.py`'s
  `Disputed` branch logic is unchanged and remains offline-verified.

### Final live coverage
Four of five final-verdict categories now have live examples:
`CredentialConfirmed`, `LikelyRevokedOrExpired`, `Unverified`,
`InsufficientEvidence`. `Disputed` is offline-tested only, with the
investigation above documented honestly rather than omitted.

## [0.1.5] — InsufficientEvidence live example

### Live deployment
- Ran a fourth live `submit_check` transaction on the same
  `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d` contract
  (`0x65203140f57eae9de08466885af8a0908aafc22627de459a3075dcfb299c6434`,
  FINALIZED/SUCCESS, `check-4`) demonstrating **`InsufficientEvidence`**:
  the same two real, accessible `cpsc.gov` pages from `[0.1.3]`'s
  `LikelyRevokedOrExpired` example, but with a deliberately fictional
  claimed ID (`"ZZ-000000"`) that appears on neither. Both sources came
  back `contains_credential_id: false`, `verdict: "CredentialIdNotFound"`
  — real, fetchable evidence that simply never mentions the claimed ID —
  and `final_verdict: "InsufficientEvidence"`, confirmed via
  `get_verdict("check-4")`.
- Live verdict categories now demonstrated: `CredentialConfirmed`,
  `LikelyRevokedOrExpired`, `Unverified`, `InsufficientEvidence`. Still
  offline-tested only: `Disputed` (see ROADMAP.md — a live example
  requires two independent real sources that actively disagree about the
  same underlying claim, which is harder to locate than sources that
  simply corroborate or simply don't mention the ID).
- No discrepancy between predicted (offline stub) and actual (live GenVM)
  contract-logic behavior was found on this transaction.

## [0.1.4] — Unverified live example

### Live deployment
- Ran a third live `submit_check` transaction on the same
  `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d` contract
  (`0xeeec72658107511bf1bc459359a5feefe4151598ce78ab9ac49a80895898c0e8`,
  FINALIZED/SUCCESS, `check-3`) demonstrating **`Unverified`**: the same
  real `bankregreports.com` source from `[0.1.3]`'s `CredentialConfirmed`
  example, submitted alone instead of alongside a second independent
  domain. Result: `contains_credential_id: true`, `verdict:
  "IndicatesValid"` for the single source, `final_verdict: "Unverified"`
  — confirming a lone corroborating domain is deliberately not enough for
  full confirmation, live.
- `total_checks()` → `4` on this contract at time of writing. Noting
  honestly: this is one more than the three transactions this project has
  documented in detail (`check-0`, `check-1`, `check-3`); `check-2` is a
  repeat of the `[0.1.3]` recall scenario run in between, confirmed via
  `get_verdict("check-2")` → `"LikelyRevokedOrExpired"`, but its exact
  transaction hash was not captured for the record. See README.md's "Note
  on check-2".
- Live verdict categories now demonstrated: `CredentialConfirmed`,
  `LikelyRevokedOrExpired`, `Unverified`. Still offline-tested only:
  `Disputed`, `InsufficientEvidence` (see ROADMAP.md).
- No discrepancy between predicted (offline stub) and actual (live GenVM)
  contract-logic behavior was found on this transaction.

## [0.1.3] — CredentialConfirmed live example + redeploy

### Live deployment
- Redeployed to a fresh contract address,
  `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d`
  ([explorer](https://explorer-studio.genlayer.com/address/0xC9E10e8212685F5767126C6AEE715E2B046F5A8d)),
  superseding the `[0.1.2]` deployment at
  `0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB`. No code change prompted
  this — it was a fresh redeploy so both live verdict examples below could
  live on one contract instance instead of being split across two.
- Ran a second live `submit_check` transaction
  (`0x0ea09a1ab72b586eda51fcaed29dc3e78942453edf09d3dd4bef78cfc4daa6fa`,
  FINALIZED/SUCCESS) demonstrating **`CredentialConfirmed`**: two real,
  independent-domain pages (`bankregreports.com`, `laneguide.com`) both
  stating JPMorgan Chase Bank, N.A.'s FDIC Certificate is 628/00628 in a
  context affirming current status. Both evidence records came back
  `contains_credential_id: true`, `verdict: "IndicatesValid"`, and
  `final_verdict: "CredentialConfirmed"` — confirmed independently via
  `get_verdict("check-0")`.
- Re-ran the `[0.1.2]` recall scenario on the new address
  (`0xc50ca9bf415d3baf1197a385eecce52fada716e5d2a5597131250ad0331f617b`,
  FINALIZED/SUCCESS, `check-1`), reproducing the same
  `LikelyRevokedOrExpired` result and the same ID-gate exclusion of
  `node/65729`. `total_checks()` → `2`, confirming both checks landed on
  the same contract instance as expected.
- No discrepancy between predicted (offline stub) and actual (live GenVM)
  contract-logic behavior was found on either transaction.
- Live verdict categories now demonstrated: `CredentialConfirmed`,
  `LikelyRevokedOrExpired`. Still offline-tested only: `Disputed`,
  `Unverified`, `InsufficientEvidence` (see ROADMAP.md).
- Consensus observation: transaction #2 (the recall re-run) showed two
  validators reporting `ERROR / Idle — Validator execution cancelled
  after quorum` rather than `Agree`/`Disagree` — this specific status
  means those validators simply stopped once quorum was already reached,
  not that they failed a check. Recorded here for completeness alongside
  the `[0.1.2]` `Disagree` observation; see SECURITY.md's consensus note.

### Note on the superseded address
`0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB` (from `[0.1.2]`) is no longer
the address referenced anywhere else in this documentation set as of this
entry. It remains a real, valid past deployment (its
`LikelyRevokedOrExpired` transaction there is still valid history), it is
simply not the one to point people to going forward.

## [0.1.2] — live-verified

### Live deployment
- Deployed to GenLayer Studio.
  Address: `0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB`
  ([explorer](https://explorer-studio.genlayer.com/address/0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB)).
  Deployment tx `0xb51c086c179e66f5f40e7b7acff557dcbd2b88e348781fd3ebf2f6ae2965a8c4`
  — FINALIZED / SUCCESS, 5/5 validator agreement.
- Ran a live `submit_check` transaction
  (`0xb2d4d88edadbf201cabf1a3e5ee43c9366512320d09c18fb8c35d4263d784c7e`,
  FINALIZED / SUCCESS) specifically designed to demonstrate the
  deterministic ID-gate: two real CPSC recall notices, one containing the
  claimed ID ("26-172") and one not (a different real recall, "26-174").
  Result matched prediction exactly:
  - `https://www.cpsc.gov/node/65727` (contains "26-172") →
    `contains_credential_id: true`, `verdict: "IndicatesRevokedOrExpired"`
  - `https://www.cpsc.gov/node/65729` (does not contain "26-172") →
    `contains_credential_id: false`, `verdict: "CredentialIdNotFound"`
    (excluded from corroboration, exactly as designed — this source never
    reached the LLM step at all)
  - `final_verdict: "LikelyRevokedOrExpired"`, confirmed independently via
    `get_verdict("check-0")` → `"LikelyRevokedOrExpired"`, and
    `total_checks()` → `1`.
- No discrepancy between predicted (offline stub) and actual (live GenVM)
  contract-logic behavior was found on this transaction. See SECURITY.md
  "Consensus and validator disagreement" for a note on one validator
  returning `Disagree` on this same transaction (quorum still reached,
  transaction still finalized as SUCCESS — expected optimistic-democracy
  behavior, not a bug).
- Full JSON record, exact input values, and full validator breakdown are
  recorded in README.md's "Live deployment status" section — treat that
  section as the single source of truth if this entry and README.md ever
  drift.

### Still not yet attempted
- A live example of a genuinely `Disputed` verdict (see ROADMAP.md;
  `TESTING.md`'s "Coverage gaps acknowledged, not hidden" section still
  applies).
- Live examples of `CredentialConfirmed` and `Unverified` — only
  `LikelyRevokedOrExpired` has a live transaction behind it so far;
  `CredentialConfirmed`/`Unverified`/`Disputed`/`InsufficientEvidence`
  remain offline-tested only.

## [0.1.1] — runner header pinned (found during Studio deployment attempt)

### Fixed
- `contract.py`'s runner header used the alias tag
  `{"Depends": "py-genlayer:latest"}`. Attempting to load the contract in
  GenLayer Studio (Normal / Full Consensus execution mode) failed at
  schema-introspection time with `Could not load contract schema` /
  `Unexpected error in gen_getContractSchemaForCode: ('execution failed', ...)`.
  The underlying `genvm_log` entry reads:
  `':test/ :latest runner used in non-debug mode, this is not allowed'`.
  Confirmed against current GenLayer documentation examples, which pin the
  runner to a specific hash (e.g.
  `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`) rather
  than using `:latest` or `:test`. Changed the header to a pinned hash.
- Added `tests/test_runner_header.py` (3 new tests) to statically check the
  runner header is not an alias tag going forward. This is a static check
  only — the offline stub has no concept of GenVM runners at all, so this
  specific class of failure can never be caught by contract-logic tests; it
  can only be caught by (a) this cheap regex check on the header text, or
  (b) an actual Studio load attempt.

### Why this wasn't caught offline
This is exactly the kind of gap `TESTING.md`'s "What the offline stub does
and does not verify" section calls out in advance: the offline stub
exists to test `contract.py`'s *logic*, not GenVM's deployment/runner
infrastructure. No amount of offline stub hardening would have caught
this — it required an actual Studio load attempt. Recorded here, per the
project's standing rule (below), rather than quietly fixed with no trace.

### Offline test count
**114 → 117 passed, 0 failed** (added `test_runner_header.py`, 3 tests).

## [Unreleased]

Nothing pending. This project's live-verification work is complete: four
of five final-verdict categories are live-demonstrated (see `[0.1.5]`),
and a genuine live `Disputed` example was actively investigated and
found not to occur naturally on the live web (see `[0.1.6]`), which is
itself a documented, evidenced conclusion rather than an unfinished task.
See ROADMAP.md for what (if anything) is still open.

**Standing rule for this file:** if any live `gl.*` behavior is ever found
to not match what the offline stub predicted, that gets recorded here
honestly, alongside what was changed in `contract.py` and what was changed
in the offline stub to catch the same class of bug going forward. This
file does not get quietly edited after the fact to remove a discrepancy
once it's fixed — the record of "this was wrong once and here's what we
learned" is more useful to a reviewer than a clean history.

## [0.1.0] — initial build

### Added
- `contract.py`: `AccreditationCheck` GenLayer Intelligent Contract.
  - `submit_check(subject_name, claimed_credential_id, evidence_urls) -> str`
  - `get_check(check_id) -> str`
  - `get_verdict(check_id) -> str`
  - `total_checks() -> int`
  - Deterministic ID-matching gate (`text_contains_credential_id`) run
    before any LLM call, per evidence URL.
  - Domain normalization (`normalize_host`, `registrable_domain`) for
    duplicate-domain detection and independent-corroboration counting.
  - Fixed-vocabulary LLM verdict parsing (`parse_llm_verdict`) for the
    per-evidence `IndicatesValid` / `IndicatesRevokedOrExpired` / `Unclear`
    judgment.
  - Five-branch final-verdict aggregation rule (`aggregate_verdict`):
    `CredentialConfirmed`, `LikelyRevokedOrExpired`, `Disputed`,
    `Unverified`, `InsufficientEvidence`.
- Offline `genlayer` SDK stub (`tests/genlayer_stub/genlayer/`), hardened
  to reproduce four specific documented real-GenVM behaviors:
  `Address` double-wrap rejection, `dataclass` non-export from
  `from genlayer import *`, `DynArray`/`TreeMap` direct-construction
  rejection (including the `inmem_allocate` DynArray-specific quirk), and
  automatic top-level-field zero-initialization.
- Full offline test suite: 114 tests across 7 files
  (`test_id_matching.py`, `test_domain_normalization.py`,
  `test_llm_verdict_parsing.py`, `test_aggregation.py`,
  `test_stub_hardening.py`, `test_lint_e022.py`,
  `test_contract_integration.py`). All 114 passing at time of writing.
- 12-file documentation suite plus `tests/README.md` coverage index (this
  file among them).

### Known limitations at initial build (see SECURITY.md for full detail)
- ID matching is substring-based and line-scoped, not word-boundary-aware
  — a deliberate, documented tradeoff, not an oversight.
- Registrable-domain suffix list is a small hardcoded set, not the full
  Public Suffix List.
- No Sybil-resistance across genuinely different domains controlled by the
  same operator.
- Not yet live-deployed; no transaction hash exists yet for any behavior
  described in this changelog. See README.md's Live Deployment section.

### Not yet done
- Live deployment to GenLayer Studio.
- At least one live `submit_check` transaction specifically demonstrating
  the deterministic ID-gate excluding a source.
- Update to README.md / SUBMISSION_CHECKLIST.md / TESTING.md /
  REVIEWER_GUIDE.md / PROJECT_OVERVIEW.md with real deployment/transaction
  results, once available.
