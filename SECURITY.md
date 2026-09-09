# SECURITY.md

This document lists known limitations and honest tradeoffs, not just
theoretical concerns. Nothing here is hidden or minimized.

## 1. The deterministic ID gate proves presence, not authority

**The core, explicitly disclosed limitation of this contract's design.**
`contains_credential_id: True` proves only that the claimed ID string
appears somewhere on the fetched page — it does **not** prove the page is
an authoritative source for that credential type, or that the ID's
presence means what a naive reading would suggest.

Concretely: a credential-issuing body could publish a page containing the
exact ID string in a context that means the *opposite* of "valid" — most
obviously, a revocation list. The deterministic gate will correctly mark
such a page as `contains_credential_id: True`; it is the subsequent LLM
judgment step's job to correctly classify that page as
`IndicatesRevokedOrExpired`, not `IndicatesValid`, based on the
surrounding context.

This interaction is deliberately tested, not just described:
`tests/test_contract_integration.py::TestIdPresentButRevoked` exercises
exactly this scenario — a page where the ID is present but the correct
verdict is revocation, not confirmation — and asserts the final aggregated
verdict comes back `LikelyRevokedOrExpired`, not `CredentialConfirmed`.

The gate is a **necessary, not sufficient**, condition for a page to
count as supporting evidence. It eliminates an entire class of failure
(vague, ID-less, confident-sounding prose) but does not eliminate the need
for the LLM judgment step, and does not eliminate the residual risk that
an LLM misreads context on a page where the ID genuinely is present.

## 2. ID matching is substring-based and line-scoped, not boundary-aware

`text_contains_credential_id` normalizes both the credential ID and each
line of page text by stripping all non-alphanumeric characters and
lowercasing, then checks substring containment. Two consequences, both
accepted by design (see DESIGN_DECISIONS.md):

- **False positives from substring containment.** An ID that happens to be
  a contiguous substring of a longer alphanumeric run on the page (e.g.
  claimed ID `AB123456` appearing inside a longer reference code
  `XAB123456Y`) will match. This is intentionally not "fixed" with
  boundary heuristics, because ad-hoc word-boundary logic on
  arbitrarily-punctuated real-world license number formats is itself a
  significant source of false negatives — the tradeoff was decided in
  favor of the simpler, more auditable rule. Tested directly in
  `test_id_matching.py::test_id_as_substring_of_longer_token_still_matches`.
- **Line-scoped normalization, not document-wide.** Normalization happens
  per line of page text, not on the whole document collapsed into one
  string. This is itself a mitigation against a *worse* false-positive
  mode (unrelated numbers from different sentences being concatenated into
  a false match once all whitespace in the entire document is stripped at
  once) — but it is a mitigation, not a complete fix. An ID that happens
  to be split across a line break on the source page (rare, but possible
  with certain HTML→text extraction behavior) will not match. Tested
  directly in `test_id_matching.py::test_id_split_across_lines_does_not_match`.

## 3. Registrable-domain approximation is not a full public suffix list

`registrable_domain` uses a small, hardcoded set of ~25 known multi-part
suffixes (`co.uk`, `com.au`, `gov.uk`, etc.) rather than depending on the
full, regularly-updated Mozilla Public Suffix List. A domain under an
uncommon multi-part suffix not in this hardcoded set will be reduced
incorrectly (treated as if the last two labels were the registrable
domain, when a three-label suffix is actually correct for that TLD). This
only affects the `domain` / `is_duplicate_domain` bookkeeping used for
independent-source counting — it does not affect the ID-matching or LLM
judgment for any individual page. See DESIGN_DECISIONS.md for why a full
PSL dependency was deliberately avoided for this project's scope.

## 4. Fetch reliability of specific domains

Some well-known, high-traffic domains have been observed (in a prior
GenLayer contract's live transactions, not merely theorized) to return
`fetch_status: "inaccessible"` via `gl.nondet.web.render` — specifically
`britannica.com`, `reuters.com`, `investopedia.com`, and `ftc.gov`, likely
due to bot/scraper protection. This contract handles fetch failure of any
domain gracefully (`fetch_status: "inaccessible"`, `verdict: "NoEvidence"`,
contributes nothing to the final verdict either way) rather than failing
the whole transaction, but it cannot make an unreachable page reachable.
Evidence-source selection (in documentation, examples, and live testing)
deliberately avoids the four domains above; see README.md's deployment
reminders.

## 5. Sybil / single-operator evidence

Nothing in this contract can detect whether two "independent" domains are
actually controlled by the same operator (e.g. a claimant who owns both
`example-credentials.com` and `example-credentials.org` and posts
self-serving pages to both). The `is_duplicate_domain` / registrable-domain
counting logic only protects against the *same* domain being counted
twice — it is not, and does not claim to be, a Sybil-resistance mechanism
across genuinely different domains. This is a structural limitation of
any evidence-corroboration design that uses domain identity as its
independence proxy, not something unique to this contract.

## 6. LLM judgment reliability

`parse_llm_verdict` defaults to the most conservative category
(`Unclear`) on any unparseable response, and the LLM is only ever asked to
choose among three fixed words for pages that already passed the
deterministic gate — but the underlying judgment ("does this page,
correctly read, indicate current validity") is still an LLM call, and LLM
misjudgment of page context (as described in limitation #1 above) is a
residual risk that no amount of prompt engineering fully eliminates. This
is why `IndicatesRevokedOrExpired` outweighs `IndicatesValid` in the final
aggregation rule (see DESIGN_DECISIONS.md) rather than the two being
treated symmetrically — a false "confirmed" is treated as more costly than
a false "disputed."

## 7. No authentication or rate limiting

Any address can call `submit_check` for any `subject_name` and
`claimed_credential_id`, with no cost beyond gas/validator compute. This
contract does not attempt to prevent spam submissions, nor does it
restrict who may query a given subject's checks (all checks are publicly
readable via `get_check`/`get_verdict` given a `check_id`, and `check_id`s
are sequential and guessable). This is consistent with the intended use
case (a public verification registry) but is worth stating explicitly
rather than leaving implicit.

## 8. Runner header must be a pinned tag, not an alias

Discovered live, not predicted offline: GenVM rejects the `:latest`/`:test`
alias runner tags in the `{"Depends": ...}` header outside Debug mode,
with `':test/ :latest runner used in non-debug mode, this is not allowed'`
surfacing as a generic `Could not load contract schema` error in Studio.
`contract.py`'s header is now pinned to a specific runner hash (see
CHANGELOG.md `[0.1.1]`). `tests/test_runner_header.py` statically checks
this going forward, but — like the Studio UI-layer issues in this
document — this class of problem is only fully catchable by an actual
Studio load attempt, not by the offline `genlayer` stub, which has no
model of GenVM runners at all.

## 9. Consensus and validator disagreement (observed live)

On this project's live `submit_check` transactions, not every validator
in the set reported `Agree` every time, yet every transaction still
finalized as `ACCEPTED`/`SUCCESS` because quorum was reached:
- One transaction had 4 of 5 validators `Agree` and one `Disagree`.
- Another had 3 of 5 validators `Agree` and two reporting
  `ERROR / Idle — Validator execution cancelled after quorum` (meaning
  those validators simply stopped once quorum was already reached, not
  that they failed a check).

This is expected optimistic-democracy behavior, not a defect:
`gl.eq_principle.strict_eq` requires the validators that count toward
quorum to agree on the final categorical output of each nondet block, not
that every single validator in the set produces an identical result on
every call — an LLM-backed judgment step (this contract's
`IndicatesValid`/`IndicatesRevokedOrExpired`/`Unclear` classification) can
plausibly draw a different validator to a different fixed-vocabulary
answer on a borderline page. This contract does not (and structurally
cannot, since it never has visibility into which individual validators
agreed) determine *why* a specific validator disagreed on a specific run;
the guarantee it relies on is that consensus, not individual unanimity,
is required for finalization. See CHANGELOG.md `[0.1.2]` and `[0.1.3]`
for the specific transactions these were observed on.

## Reporting

This is a Portal Builder track submission, not a production security
posture. If reviewing this for the Builder track and something above is
incomplete or another issue is found, please raise it via the normal
Portal review process — see REVIEWER_GUIDE.md for what reviewers are asked
to specifically check.
