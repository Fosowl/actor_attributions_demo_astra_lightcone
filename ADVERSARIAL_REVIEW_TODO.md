# Adversarial review — verified findings & TODO (RFC-0004 actor attribution)

External adversarial review (Kimi) of the actor-attribution layer, 2026-07-30.
Every finding below was **empirically re-verified** (13 independent verification
agents reproducing each claim against the live forks): 13/15 findings confirmed,
2 confirmed with corrections. Line numbers drift — locate by symbol, not line.

> RFC renumbering: RFC-0003 was renamed **RFC-0004** (an unmerged upstream issue
> claimed 0003 first). References below use the finding numbers from the review.

**Verdict on the RFC's two central claims:** (a) "fully additive" is false in two
documented ways (findings 1, 5); (b) "astra-tools enforces what the schema can't"
holds on the `astra validate` analysis path but the universe paths are under-gated
(findings 2–4) and astra-spec's CI cannot see any semantic invariant (finding 8).

---

## Tier 1 — genuinely ours (RFC-0004). Fix before the implementation PR.

- [ ] **#1 (critical) — `decisions` union compiles to self-contradictory JSON Schema.**
  linkml 1.10.0: the `any_of: [string, DecisionSelection]` on `Universe.decisions`
  AND `UniverseNode.decisions` emits a sibling scalar `anyOf` next to
  `type: [object, null]` — **any** `decisions:` map fails the generated-JSON-Schema
  path, *including empty `{}`* (worse than the review claimed) and including both
  committed valid fixtures. Pydantic path unaffected; single-valued attribution
  slots (`proposed_by` etc.) unaffected — defect is specific to
  multivalued+inlined+any_of. Fix candidates tracked in this repo's issue #1 —
  coordinate there (remodel as list, or pin/post-process the generator).

- [ ] **#2-crashes (critical) — `_validate_attribution` crashes / silently accepts
  malformed values.** New 0004 code (`astra-tools/src/astra/validation/semantic.py`):
  non-str/non-dict values (`selected_by: 42`, `[jane]`) hit `else: return errors` —
  silently valid; list-valued `role` crashes at `ROLE_ALLOWED_TYPES.get(role)`,
  list-valued `actor` at the `in actors_in_scope` test (`TypeError: unhashable`).
  Fix: isinstance guards + new `INVALID_ATTRIBUTION` error code. (The *missing
  schema gate* in `universe check` is pre-existing — see Tier 2 — but our code is
  what crashes.)

- [ ] **#5 (major) — reserved-id `actors` breaks "fully additive".** Commit 671fc45
  added `|actors` to every entity-id lookahead: a pre-existing file with an entity
  literally named `actors` was valid on 0.0.12 and now fails. Boundary ids
  (`actors2`, `xactors`, `actors_1`) unaffected; applied consistently. The RFC
  claims universal backward compat seven lines below the reservation. Fix: add a
  migration note to the RFC and soften the universal claim — it cannot be both.

- [ ] **#6 (major) — `astra-spec>=0.0.13` unsatisfiable from PyPI** (max published:
  0.0.12; plain `pip install` of astra-tools fails resolution). Release-strategy
  decision: publish 0.0.13 first or hold the pin. Also reword the
  `[tool.uv.sources]` comment — resolution *does* go to the index for consumers,
  but the outcome is failure, which the comment obscures.

- [ ] **#7 (major) — bare actor-id shorthand crashes the generated-dataclass loader**
  (`Attribution(**value)` on a string; pythongen `any_of` limitation). 2-of-3
  validation paths accept the shorthand; the third can't parse it, contradicting
  RFC §2's universality. Documented in `tests/data/problem/…` — but **nothing runs
  `problem/`** (no test, no just recipe, no CI). Fix: coerce str→Attribution in a
  post-init fixup, or scope the shorthand claim; wire `problem/` in as xfail.

- [ ] **#10 (minor) — explicit `decision_id` contradicting its map key never flagged.**
  Injection uses `setdefault`; the key silently wins. Correction to the review: in
  its own 2-decision repro validation *fails* (MISSING_DECISION for the orphaned
  decision) — the true defect is that the contradiction itself is never diagnosed.
  Fix: `DECISION_ID_MISMATCH` semantic error.

- [ ] **#12 (design call) — no inverse check**: `excluded: true` with only legacy
  `excluded_reason` passes; nothing requires the new who/when/judgment record
  (legacy pair IS bidirectional; only the three 0004 fields are one-directional).
  RFC authors decide whether a `MISSING_EXCLUSION_RECORD` (error or warning) is
  wanted. Leave unimplemented until decided.

- [ ] **#13 (wording only) — from:-aliased decisions**: NOT a defect — a `from:`
  alias is a pure pointer that *cannot carry* options/attribution
  (`from_alias_forbids_options`), so attribution is inherently defining-scope.
  Fix: one sentence in the RFC stating defining-scope semantics.

- [ ] **#14 (docs) —** (a) the `human_carries_identity` comment in `actor.yaml` is
  half-wrong: the `any_of` **rule postcondition** DOES compile to JSON Schema
  (verified: bare `type: human` rejected there); only the Pydantic half of the
  comment is true. (The class-level `any_of` on `ResearcherId` genuinely compiles
  nowhere — that comment stands.) (b) RFC sentence "…not by `identifiers` alone"
  is garbled — implementation allows identifiers-alone; reword to "either alone
  suffices". (c) Scalar `when:` is dead code on the standard pipeline (semantic
  layer supports str; Pydantic requires list) — note or drop.

- [ ] **#15-partial — collateral error cascades** from 0004's normalization: a
  selection missing `option_id` emits MISSING_OPTION_ID plus spurious
  MISSING_DECISION; an unknown `option_id` still feeds `when` evaluation,
  producing collateral INACTIVE_DECISION downstream. Suppress coverage/when
  collateral for selections already reported malformed.

## Tier 2 — pre-existing upstream bugs (file as separate issues/PRs; do NOT mix
into the RFC implementation diff)

Filing these first, marked "pre-existing, found during RFC-0004 adversarial
review", prevents them being blamed on the actor layer and builds reviewer trust.

- [ ] **#4 (high) — universe validation trusts an unvalidated analysis.**
  `validate_universe_file` never validates the analysis: `when: ["d1.o1.extra"]`
  (Pydantic-valid — the `when` slot has **no pattern**) crashes
  `is_condition_met` at `ref.split(".")`; `when: ["ghost.o1"]` makes the
  conditional decision inactive → a universe *missing it* passes clean (silent
  acceptance of an incomplete universe — core multiverse correctness hole).
  Fix: guard the split; validate/surface analysis errors in
  `validate_universe_file`.

- [ ] **#3 (high) — `validate_universe_file` never calls `resolve_analysis_tree`.**
  Any `path:`-composed analysis yields false UNKNOWN_DECISION (and now
  UNKNOWN_ACTOR) for sub-analysis selections; same universe passes standalone.
  Correction to the review: the actor-type "shadowing" miss only occurs via
  `path:` subs — downstream of this same root cause; inline shadowing resolves
  correctly. One-line fix mirroring `validate_analysis`.

- [ ] **#2-gate (medium) — `universe check` runs no schema validation** (only
  semantic). Pre-existing structure, made dangerous by 0004. Fix: call
  `validate_universe_data` first (mirror the `validate` command).

- [ ] **#11 (medium) — duplicate YAML keys silently last-win** inside
  `yaml.safe_load` — parse-time data loss no validator can see; audit-hostile.
  Fix: duplicate-key-rejecting SafeLoader in `helpers.load_yaml`.

- [ ] **#8 (medium) — astra-spec CI blind spots** (the reason #1 went unnoticed):
  valid fixtures never validated through JSON Schema; invalid fixtures assert only
  "some error"; `_test-examples` is failure-allowed; no semantic invariant is
  exercised anywhere in astra-spec CI. Fix: valid-fixtures-through-JSON-Schema
  test (will fail until #1 is fixed — sequence accordingly) + a CI step invoking
  astra-tools validation.

- [ ] **#9 (low) — filename sniffing** (`"universe" in stem or parent == "universes"`)
  misroutes universes even when `-a` is passed, with no hint the flag was ignored.
  Fix: `-a` forces universe mode.

- [ ] **#15a (low) — raw tracebacks** on YAML syntax errors (unguarded `load_yaml`
  at the CLI boundary). Note: an *unquoted* invalid date (`2024-13-45`) crashes
  inside PyYAML itself and surfaces the same way.

## Verified clean (no action)

`astra init` version clamp (dev/post/local versions handled); `excluded_at` date
handling (quoted + unquoted valid dates pass, invalid rejected — at Pydantic if
quoted, at PyYAML if not); `requires`/`incompatible_with` on object-form
selections; Role enum identical across RFC / schema / reference module /
`ROLE_ALLOWED_TYPES` (guardrail-tested); ORPHAN_* codes and registry checks fire;
actor shadowing in *analysis* validation resolves innermost-first correctly.
