# REVIEWER_GUIDE.md

A short guide for anyone reviewing this submission for the GenLayer Portal
Builder track, Intelligent Contracts category.

## What to check first: is this actually novel, not duplicative?

Read `DESIGN_DECISIONS.md`'s opening section, "What makes this project not
materially duplicative." The specific claim is: this contract introduces a
**deterministic content-extraction gate between fetch and LLM judgment**
— pages that don't literally contain the claimed credential ID (via
normalized string matching, no LLM) are permanently excluded from
corroboration, regardless of how favorably an LLM might otherwise judge
their prose. If you've reviewed a prior corroboration-style GenLayer
contract that used purely-LLM-judged verdicts or purely-structural
(domain-count-only) exclusion, this is the specific mechanic that differs.

**Fastest way to verify this claim isn't just asserted:** run
`test_contract_integration.py::TestDeterministicIdGate::test_source_without_id_is_excluded_even_with_favorable_llm_configured`.
That test deliberately configures the stub LLM to answer `IndicatesValid`
for *any* prompt, then submits one evidence source that contains the ID
and one that doesn't (but reads as generically favorable), and asserts the
non-matching source is excluded from the final verdict anyway. If the gate
were broken or bypassed, this specific test would fail.

## What to check second: does the storage schema actually respect guardrail #17?

Open `contract.py` and confirm:
- The only two fields declared on `AccreditationCheck` are
  `checks: TreeMap[str, str]` and `check_ids: DynArray[str]` — both
  top-level, both scalar-valued.
- `submit_check` builds the full check record (including the evidence
  list) as a plain Python dict, then `json.dumps`s it into a single string
  before ever touching `self.checks`. There is no point in the code where
  a `DynArray` or `TreeMap` is constructed directly by contract code (only
  `.append()` on `self.check_ids` and key assignment on `self.checks`).

`ARCHITECTURE.md`'s "Storage schema discipline" section explains why this
matters (a confirmed real-GenVM limitation, not a style preference).

## What to check third: is the offline test suite honest about its own limits?

Run the suite:
```bash
pip install pytest
cd AccreditationCheck
pytest tests/ -v
```
Confirm the reported count matches what's claimed in README.md/TESTING.md
(117 passed, 0 failed, at time of writing — re-run to confirm current
state rather than trusting the written number).

Then read `TESTING.md`'s "What the offline stub does and does not verify"
section. A reviewer should come away understanding that 117/117 offline is
a real, checkable number, but is explicitly *not* being presented as
equivalent to live verification — check `README.md`'s "Live deployment
status" section for the actual live-verification claim, which should never
say more than what a specific transaction hash actually backs.

## What to check fourth: the disclosed limitations are actually disclosed, not buried

Read `SECURITY.md` in full — it's short. In particular, confirm section 1
("The deterministic ID gate proves presence, not authority") matches the
project brief's required disclosed limitation, and confirm
`test_contract_integration.py::TestIdPresentButRevoked` actually exercises
the specific case described (ID present, but the page is a revocation
list — verdict should be `LikelyRevokedOrExpired`, not
`CredentialConfirmed`).

## What NOT to expect at this stage

- **A live example of `Disputed`**, specifically — the one remaining
  verdict category without a live transaction. `CredentialConfirmed`,
  `LikelyRevokedOrExpired`, `Unverified`, and `InsufficientEvidence` all
  have live transactions behind them (see README.md's "Live deployment
  status"). This isn't an unfinished task: a real investigation was
  carried out (real FDIC certificate numbers of failed banks, real
  CPSC/FDA recall numbers on secondary sites) and no genuine live
  disagreement was found — see CHANGELOG.md `[0.1.6]` for the full
  record and TESTING.md's "Coverage gaps acknowledged, not hidden" for
  why this is a plausible, evidenced conclusion rather than a gap in
  effort.

## Quick file map for review

| If you want to check... | Read... |
|---|---|
| The novel mechanic claim | `DESIGN_DECISIONS.md` (top section), `README.md` |
| Storage schema correctness | `ARCHITECTURE.md`, `contract.py` |
| Test rigor and honesty about limits | `TESTING.md`, `tests/README.md` |
| Disclosed limitations | `SECURITY.md` |
| Live-verification status (single source of truth) | `README.md` |
| What's left to do | `ROADMAP.md`, `SUBMISSION_CHECKLIST.md` |
