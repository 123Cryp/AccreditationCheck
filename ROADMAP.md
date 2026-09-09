# ROADMAP.md

## Done

1. ~~Deploy `contract.py` to GenLayer Studio.~~ Deployed at
   `0x40EAa5e7cCD29BDd58B9a77902e49cC546b8F6AB`
   (tx `0xb51c086c179e66f5f40e7b7acff557dcbd2b88e348781fd3ebf2f6ae2965a8c4`,
   FINALIZED/SUCCESS, 5/5 validators).
2. ~~Run at least one live `submit_check` transaction that specifically
   demonstrates the deterministic ID-gate excluding a source.~~ Done via
   tx `0xb2d4d88edadbf201cabf1a3e5ee43c9366512320d09c18fb8c35d4263d784c7e`
   using two real `cpsc.gov` recall pages (one containing the claimed ID,
   one not) — see README.md's "Live deployment status" for the full
   record.
3. ~~Update six files with the real result.~~ README.md, CHANGELOG.md,
   SUBMISSION_CHECKLIST.md, TESTING.md, REVIEWER_GUIDE.md, and
   PROJECT_OVERVIEW.md all now reflect the live-verified state
   consistently, including a redeploy to a new official address
   (`0xC9E10e8212685F5767126C6AEE715E2B046F5A8d`) and a second live
   transaction demonstrating `CredentialConfirmed` (two independent real
   sources — `bankregreports.com` and `laneguide.com` — both affirming
   JPMorgan Chase Bank, N.A.'s FDIC certificate number).
4. A real live discrepancy from offline predictions WAS found along the
   way — the runner header used the alias tag `:latest`, which GenVM
   rejects outside Debug mode. Fixed in `contract.py`, caught going
   forward by a new `test_runner_header.py`, and recorded honestly in
   CHANGELOG.md `[0.1.1]` and SECURITY.md #8, per the standing rule.

5. ~~Attempt to find a live example of a genuinely `Disputed`
   verdict.~~ A real investigation was carried out: real FDIC certificate
   numbers of banks closed by regulators (checking whether any stale
   third-party directory site still cites the same certificate as
   currently valid), and real CPSC/FDA recall numbers republished on
   secondary sites (checking whether any retailer/blog cites the same
   recall number with a positive framing). No genuine live disagreement
   was found — see CHANGELOG.md `[0.1.6]` for the full record. `Disputed`
   remains covered by offline tests only
   (`test_aggregation.py`, `test_contract_integration.py`), which is now
   a documented, evidenced conclusion rather than an open task.

## Immediate next steps (still open)

1. Draft and character-count the Portal Submit Contribution form's
   Notes/Description text against its confirmed 1000-character limit
   before pasting it in.
2. Standing rule, still in effect for any future change: if any live
   `gl.*` behavior doesn't match what the offline stub predicted, fix
   `contract.py`, fix the stub to catch the same class of bug offline
   going forward, and record what happened in CHANGELOG.md and
   SECURITY.md honestly — this already happened once (the runner header)
   and is expected to be a real possibility again, not a failure
   condition when it happens.

## Possible future directions (not required for this submission)

These are explicitly out of scope for the initial Builder track submission
and listed here only as honest "here's where this could go," not as
implied commitments:

- **Full Public Suffix List support**, replacing the small hardcoded
  multi-part-suffix set, if a maintainable way to vendor or reference it
  within GenVM's single-file-contract model becomes practical.
- **Per-subject or per-credential-type query methods** (e.g. "all checks
  for subject X"), which would require either an additional
  `TreeMap[str, DynArray[str]]`-shaped index (itself a top-level field, so
  compatible with guardrail #17) mapping subject name to a list of
  `check_id`s, or off-chain indexing of `get_check` results. Not built
  initially to keep the storage schema minimal and easy to reason about.
- **Re-check / refresh mechanism**: allowing a `check_id` to be
  re-verified against the same or updated evidence URLs at a later date,
  rather than every check being a permanent, immutable single snapshot.
  This would need a clear answer to "does a re-check overwrite the
  original record or create a new linked one" before being built.
- **Confidence/strength signal beyond the five-way final verdict** — e.g.
  surfacing the actual count of corroborating vs. revoking domains
  alongside the categorical verdict (this data already exists in the
  stored evidence list and is fully computable by any consumer of
  `get_check` today; it just isn't surfaced as a separate summary field).
- **Evidence URL count above the current cap of 10** — the current
  `MAX_EVIDENCE_URLS = 10` is a simple, documented pre-flight limit
  (see DESIGN_DECISIONS.md); raising it would mostly be a cost/gas
  tradeoff decision for a live network, not a design change.
