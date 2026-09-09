# CONTRIBUTING.md

This is a Portal Builder track submission, not a large open-source project
with a formal governance process — but if you're extending, reviewing, or
adapting this contract, here's how the pieces fit together and what's
expected of a change.

## Before changing `contract.py`

1. Read `ARCHITECTURE.md` and `DESIGN_DECISIONS.md` first. Several things
   that might look like oversights (line-scoped ID normalization instead
   of document-wide, a small hardcoded suffix list instead of the full
   PSL, JSON-string storage instead of nested storage types) are
   deliberate, documented tradeoffs with reasons attached. If you disagree
   with one, that's fine — but change the design decision explicitly in
   `DESIGN_DECISIONS.md`, don't just silently patch around it.
2. Verify any new or changed `gl.*` API usage against current GenLayer
   documentation (web search) before writing code that depends on it.
   Don't assume a documentation example for one type (e.g. `TreeMap`)
   generalizes to a superficially similar type (e.g. `DynArray`) — see
   guardrail #3 in the original project brief, and `ARCHITECTURE.md`'s
   storage schema section, for a confirmed case where it didn't.
3. Check the storage schema discipline in `ARCHITECTURE.md` before adding
   any new persistent field. New fields should be plain scalars or
   top-level `TreeMap`/`DynArray` with scalar value/element types — never
   a nested `DynArray[SomeDataclass]` or `TreeMap[K, SomeDataclass]`.

## Making a change

1. Add or update tests **before or alongside** the code change, not after.
   If you're fixing a bug found live (see the CHANGELOG.md standing rule),
   the fix isn't complete until:
   - `contract.py` is fixed,
   - the offline `genlayer` stub (`tests/genlayer_stub/genlayer/`) is
     updated to reproduce the same class of bug, so it's caught offline
     next time, and
   - `CHANGELOG.md` and `SECURITY.md` (if relevant) record what happened,
     honestly, including that it was missed offline first.
2. Every method on the `AccreditationCheck` class must remain a plain
   instance method with `self` as its first parameter — no
   `@classmethod`/`@staticmethod` anywhere in `contract.py` (GenVM lint
   rule E022). `tests/test_lint_e022.py` enforces this via AST inspection;
   it should never need to be weakened to accommodate a change.
3. Run the full suite before considering a change done:
   ```bash
   pip install pytest
   cd AccreditationCheck
   pytest tests/ -v
   ```
   Report the exact pass/fail count — don't round or approximate it in any
   commit message or doc update.
4. If your change affects the per-evidence or final verdict vocabularies
   (`EVIDENCE_VERDICTS`, `LLM_VERDICTS`, `FINAL_VERDICTS` in
   `contract.py`), update `DESIGN_DECISIONS.md`'s aggregation-rule section
   to match, and add or update tests in `test_aggregation.py` covering the
   new/changed branch.

## Documentation discipline

This project keeps 12 top-level docs plus a `tests/README.md` coverage
index specifically so that "not yet live-verified" and "live-verified with
transaction hash X" are never in an inconsistent state across files. If
you update live-deployment status, check **all six** files that carry the
disclaimer — README.md, CHANGELOG.md, SUBMISSION_CHECKLIST.md,
TESTING.md, REVIEWER_GUIDE.md, PROJECT_OVERVIEW.md — not just the one you
happened to be editing.

## What a good PR/change description looks like here

- States which of the 7 test files were touched and the before/after pass
  count.
- States plainly whether the change affects any live-verification claim
  (it shouldn't, unless you actually ran a new live transaction).
- If it's a design change (not just a bug fix), points to the relevant
  section of `DESIGN_DECISIONS.md` it updates.
