# SUBMISSION_CHECKLIST.md

Use this as the literal checklist before marking this Portal Builder track
submission complete. Items are grouped in the order they should happen.

## Code

- [x] `contract.py` written, single file, deployable as-is
- [x] Storage schema checked against guardrail #17 before writing (plain
      scalars + top-level `TreeMap[str, str]` / `DynArray[str]` only, no
      nested `DynArray[dataclass]`/`TreeMap[K, dataclass]`)
- [x] `gl.message.sender_address` used without re-wrapping in `Address(...)`
- [x] `from dataclasses import dataclass` present explicitly (not relying
      on `from genlayer import *` to provide it)
- [x] No `@classmethod`/`@staticmethod` anywhere in `contract.py`
      (GenVM lint rule E022) — verified via AST, not just visual review
- [x] Pre-flight, fully-deterministic validation before any `gl.nondet.*`
      call, with `gl.vm.UserError` on failure
- [x] Domain normalization + registrable-domain reduction implemented
- [x] Fixed-vocabulary LLM verdict parsing implemented
- [x] Deterministic ID gate implemented and confirmed to run *before* any
      LLM call per evidence URL

## Tests

- [x] Offline `genlayer` SDK stub written and hardened per guardrails
      #1–4 (Address double-wrap, dataclass non-export, DynArray/TreeMap
      construction restrictions including `inmem_allocate` quirk)
- [x] Dedicated coverage for: exact ID match, no match, formatting-variant
      match, the "ID present but revoked" scenario, and the full pipeline
      excluding a `contains_credential_id: False` source from
      corroboration even with a favorable-LLM-configured stub
- [x] Full suite run and exact pass count reported: **117 passed, 0 failed**
- [ ] Full suite re-run immediately before final submission (numbers can
      drift if the contract changes after this checklist was last updated
      — don't trust a stale count)

## Documentation

- [x] All 12 files present: README.md, ARCHITECTURE.md, SECURITY.md,
      DESIGN_DECISIONS.md, TESTING.md, CHANGELOG.md, ROADMAP.md,
      CONTRIBUTING.md, REVIEWER_GUIDE.md, PROJECT_OVERVIEW.md,
      SUBMISSION_CHECKLIST.md (this file), LICENSE
- [x] `tests/README.md` coverage index present
- [x] README.md and DESIGN_DECISIONS.md both state the "not materially
      duplicative" novelty claim explicitly (guardrail #19)
- [x] SECURITY.md discloses the "ID presence proves presence, not
      authority" limitation, with a corresponding test referenced
      (guardrail's disclosed-limitation requirement)
- [ ] Portal Submit Contribution form's Notes/Description text drafted
      and character-counted against the confirmed 1000-character limit
      *before* pasting into the live form

## Live deployment

- [x] `contract.py` deployed to GenLayer Studio — current official
      address `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d` (superseded an
      earlier deployment at `0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB`
      — see CHANGELOG.md `[0.1.3]`)
- [x] `evidence_urls` field typed as an explicit JSON array in Studio
      before submitting — done successfully on all live `submit_check`
      transactions
- [x] Studio schema-panel caching issue checked for — not actually the
      cause hit on this project; the real cause was the runner header
      using an alias tag (`:latest`) instead of a pinned hash outside
      Debug mode. See CHANGELOG.md `[0.1.1]`.
- [x] At least one live `submit_check` transaction run that specifically
      demonstrates the deterministic ID-gate excluding a source — tx
      `0xc50ca9bf415d3baf1197a385eecce52fada716e5d2a5597131250ad0331f617b`,
      FINALIZED/SUCCESS (`LikelyRevokedOrExpired`)
- [x] A second live `submit_check` transaction demonstrating
      `CredentialConfirmed` — tx
      `0x0ea09a1ab72b586eda51fcaed29dc3e78942453edf09d3dd4bef78cfc4daa6fa`,
      FINALIZED/SUCCESS
- [x] A third live `submit_check` transaction demonstrating `Unverified`
      — tx
      `0xeeec72658107511bf1bc459359a5feefe4151598ce78ab9ac49a80895898c0e8`,
      FINALIZED/SUCCESS (single corroborating source, deliberately not
      enough for `CredentialConfirmed`)
- [x] A fourth live `submit_check` transaction demonstrating
      `InsufficientEvidence` — tx
      `0x65203140f57eae9de08466885af8a0908aafc22627de459a3075dcfb299c6434`,
      FINALIZED/SUCCESS (real, accessible sources with a fictional
      claimed ID present on neither)
- [x] Live evidence URLs chosen avoiding known-unreliable domains — used
      `cpsc.gov`, `bankregreports.com`, and `laneguide.com`, all fetched
      successfully (`fetch_status: "ok"` on every evidence URL across
      both transactions)
- [x] Attempt made to find/demonstrate a genuine live `Disputed` case —
      a real investigation was carried out (see CHANGELOG.md `[0.1.6]`):
      FDIC certificate numbers of regulator-closed banks, and CPSC/FDA
      recall numbers republished on secondary sites. No genuine live
      disagreement was found; documented honestly rather than forced.
- [x] Any live behavior mismatch vs. offline stub predictions fixed in
      `contract.py` AND the stub, and recorded in CHANGELOG.md/SECURITY.md
      — the runner-header issue (CHANGELOG.md `[0.1.1]`) was found,
      fixed, and a new static test (`test_runner_header.py`) added. Both
      subsequent `submit_check` transactions showed no further
      contract-logic discrepancy from offline predictions.

## Post-live-deployment doc sync (all six, not just README)

Done — updated **all six** of, twice now (once for `[0.1.2]`, again for
`[0.1.3]`'s redeploy and second verdict example):
- [x] README.md — Live deployment status section
- [x] CHANGELOG.md — dated `[0.1.2]` and `[0.1.3]` entries with
      address/hash/result
- [x] SUBMISSION_CHECKLIST.md — this section, checked off above
- [x] TESTING.md — "Current status" section's live-testing line
- [x] REVIEWER_GUIDE.md — "What NOT to expect at this stage" section,
      updated to reflect what now IS available
- [x] PROJECT_OVERVIEW.md — "Current status" section

## Final sanity pass

- [ ] Re-read README.md top to bottom as if seeing it for the first time
- [x] Confirm every doc file's live-verification claim agrees with every
      other doc file's (README, TESTING, PROJECT_OVERVIEW, REVIEWER_GUIDE,
      CHANGELOG, this file all now reference the same current official
      address `0xC9E10e8212685F5767126C6AEE715E2B046F5A8d` and the same
      two transaction hashes — checked during this update pass)
- [x] Confirm the reported offline test count in every doc that mentions
      it (README.md, TESTING.md, PROJECT_OVERVIEW.md, this file,
      tests/README.md) is the same number — **117 passed, 0 failed**
      everywhere except CHANGELOG.md's historical `[0.1.0]` entry, which
      correctly shows 114 (the true count at that point in time)

## Still open before calling this fully complete

- [ ] Full suite re-run immediately before final submission (numbers can
      drift if the contract changes after this checklist was last
      updated — don't trust a stale count)
- [ ] Portal Submit Contribution form's Notes/Description text drafted
      and character-counted against the confirmed 1000-character limit
      *before* pasting into the live form
