# ARCHITECTURE.md

## Overview

`contract.py` is a single-file GenLayer Intelligent Contract. It has no
external dependencies beyond the `genlayer` SDK and the Python standard
library (`json`, `re`, `dataclasses`, `urllib.parse`).

## Data model

### Storage fields (top-level only — see "Storage schema discipline" below)

```python
class AccreditationCheck(gl.Contract):
    checks: TreeMap[str, str]   # check_id -> JSON-serialized check record
    check_ids: DynArray[str]    # ordered list of check_ids, for total_checks()
```

Both fields are plain, top-level `gl.Contract` fields of a scalar-valued
generic type (`TreeMap[str, str]` and `DynArray[str]`). Neither is ever
constructed by contract code — both are zero-initialized automatically by
the runtime at contract creation, and are only ever read, `.append()`-ed
to, or assigned into by key. See "Storage schema discipline" below for why
this matters.

### The check record (JSON, not a storage type)

Every check is stored as **one JSON string** under `checks[check_id]`.
Deserialized, it looks like:

```json
{
  "check_id": "check-0",
  "subject_name": "Jane Doe",
  "claimed_credential_id": "AB123456",
  "submitted_by": "0x1111111111111111111111111111111111111111",
  "evidence": [
    {
      "url": "https://board.example.gov/licenses/AB123456",
      "domain": "example.gov",
      "is_duplicate_domain": false,
      "contains_credential_id": true,
      "fetch_status": "ok",
      "verdict": "IndicatesValid"
    }
  ],
  "final_verdict": "Unverified"
}
```

Everything under `"evidence"` — a list of per-URL dicts — is built and
read with plain Python, entirely inside `submit_check` / `get_check`,
using `json.dumps` / `json.loads`. It never exists as a GenVM storage
type at any point. This is deliberate; see the next section.

## Storage schema discipline (guardrail #17)

Every persistent field in this contract is one of:

- a plain scalar (here: `str` values inside `TreeMap`/`DynArray`), or
- a top-level `TreeMap[K, V]` / `DynArray[T]` field declared directly on
  the `gl.Contract` subclass, with a scalar value/element type.

There is **no** `DynArray[SomeDataclass]` and **no**
`TreeMap[K, SomeDataclass]` anywhere, nested or otherwise. The natural
"a check has a list of evidence sub-records" relationship is instead
represented as: one `str` value in `checks: TreeMap[str, str]`, holding
`json.dumps(...)` of a plain Python dict whose `"evidence"` key is a plain
list of plain dicts.

This is a direct response to a confirmed real-GenVM limitation (not a
guess): `DynArray[T]` cannot be constructed by user code under any
circumstance in current GenVM builds, including as a field nested inside
another dataclass that itself needs to be freshly built in memory. `str`
has no such construction restriction, so nesting the evidence list inside
a JSON string entirely sidesteps the problem. See DESIGN_DECISIONS.md for
the full reasoning and SECURITY.md for the tradeoffs this introduces
(e.g. no on-chain query "give me all checks where verdict = X" without
fetching and parsing every record).

## Equivalence principle usage

Each evidence URL's fetch + judge pipeline runs as **one** nondet unit,
wrapped in `gl.eq_principle.strict_eq`:

```python
def pipeline() -> str:
    ... gl.nondet.web.render(url, mode="text") ...
    ... text_contains_credential_id(...) ...
    ... gl.nondet.exec_prompt(prompt) ...
    return json.dumps({"fetch_status": ..., "contains_credential_id": ..., "verdict": ...})

result_json = gl.eq_principle.strict_eq(pipeline)
```

**Why the whole pipeline is one nondet unit, not separate fetch/judge
units:** the raw fetched page text is the thing most likely to differ
subtly between independent validator fetches (timestamps, ad content,
minor markup differences), while the *final categorical outputs*
(`fetch_status`, `contains_credential_id`, `verdict`) are small,
discrete, and much more likely to agree across validators for the same
underlying page. Requiring `strict_eq` on raw page text would make
consensus fragile for reasons that have nothing to do with the actual
question being asked. Requiring it only on the final JSON blob asks
validators to agree on what matters (did the ID appear, and what did the
page indicate about status) rather than on incidental byte-level fetch
differences.

This does mean a single evidence URL's `submit_check` cost includes (at
most) one fetch and one LLM call per validator, run inside the same
`strict_eq` closure — not a smaller number pooled across validators. That
is standard for GenLayer nondet blocks and is not specific to this
contract.

## Method inventory

| Method | Type | Purpose |
|---|---|---|
| `submit_check(subject_name, claimed_credential_id, evidence_urls)` | write | Validates input, runs the per-URL pipeline, aggregates a final verdict, stores the check, returns its `check_id`. |
| `get_check(check_id)` | view | Returns the full JSON check record. |
| `get_verdict(check_id)` | view | Returns just the `final_verdict` string. |
| `total_checks()` | view | Returns the number of checks ever submitted. |
| `_process_evidence_url(url, subject_name, credential_id)` | internal instance method | Runs the fetch → ID-gate → (conditional) LLM pipeline for one URL. |

All five are plain instance methods with `self` as the first parameter —
no `@classmethod`/`@staticmethod` anywhere in `contract.py` (GenVM lint
rule E022; verified by `tests/test_lint_e022.py` via AST inspection, not
just manual review).

## Pure helper functions (module-level, not contract methods)

These carry no `self`, do no I/O, and are unit-tested directly, independent
of the contract or the stub:

- `normalize_id_fragment(s)` / `text_contains_credential_id(page_text, credential_id)`
  — the deterministic ID gate.
- `normalize_host(url)` / `registrable_domain(host)` — domain normalization
  (guardrail #14 pattern).
- `parse_llm_verdict(raw)` — fixed-vocabulary LLM response parsing
  (guardrail #15 pattern).
- `build_judgment_prompt(subject_name, credential_id, page_text)` — prompt
  construction (pure string formatting, no I/O).
- `aggregate_verdict(evidence_records)` — the final-verdict rule.

Keeping these at module level (rather than as `@staticmethod`s on the
class) means E022 doesn't even apply to them, and they're trivially
callable from tests without constructing a contract instance at all.

## The offline `genlayer` stub

Located at `tests/genlayer_stub/genlayer/`. It is a **test double**, not a
reimplementation of GenVM — its only jobs are (a) let `contract.py` import
and run unmodified outside real GenVM, and (b) fail in the same specific,
documented ways real GenVM fails for the bugs listed in guardrails #1–4,
so the offline suite has actual predictive power for those specific
issues rather than false confidence. See TESTING.md for what is and isn't
covered by this stub, and `tests/test_stub_hardening.py` for direct tests
of the stub's own hardening (not contract.py logic).

Configurable per-test state lives in `stub_control`
(`genlayer.gl.stub_control`): `sender_address`, `web_pages` (url → text or
an Exception instance to raise), and `llm_responses` (ordered
matcher → response pairs, with a default fallback).
