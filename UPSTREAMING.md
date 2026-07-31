# Upstreaming the actor attribution layer (RFC-0004)

Status notes for turning the fork prototype in this repo into upstream
pull requests against `LightconeResearch/astra-spec` and
`LightconeResearch/astra-tools`. The two submodules here (`astra-spec`,
`astra-tools`, both `Fosowl` forks) carry the working implementation;
this file records what is fork-only wiring versus what goes upstream.

## What the prototype contains

- **astra-spec** (tagged `v0.0.13` on the fork):
  - `rfcs/0004-actor-attribution.md` — the RFC draft.
  - `src/astra/schema/actor.yaml` — new LinkML module: `ActorType`,
    `HumanRole` / `AgentRole` enums, `ResearcherId`, `Actor`,
    `Attribution`; imported by `analysis.yaml` (`Analysis.actors`,
    `Option.proposed_by` / `excluded_by`) and `universe.yaml`
    (`DecisionSelection.selected_by` / `reviewed_by`, explicit
    `union(string, DecisionSelection)` on both `decisions` slots).
  - Regenerated datamodels, fixtures (`tests/data/{valid,invalid,problem}`),
    updated `docs/specification.md`.
- **astra-tools**:
  - Semantic enforcement (the runtime enforcement point): registry
    membership of attribution refs (resolving upward through ancestor
    scopes), role legality for the actor's type (`ROLE_ALLOWED_TYPES`
    derived from the schema enums), `excluded_by` ⇒ `excluded: true`,
    human/agent field split, non-empty `identifiers`.
  - Both universe selection forms (scalar shorthand and attribution
    object) parse, validate, and display; `astra info` renders the
    registry and attributions; `examples/iris` is the attributed demo.

## PR strategy

astra-spec's own RFC process expects the **draft PR to be the RFC
document alone**, with implementation following acceptance in one
reviewed PR per repo. So:

1. **Now — upstream draft PR**: only `rfcs/0004-actor-attribution.md`,
   opened as a GitHub draft against `LightconeResearch/astra-spec`,
   linking the fork branches as the reference implementation.
   Before opening: fill the `authors:` frontmatter, open the tracking
   issue (RFC-labelled) and link it, and replace the fork-link TODO.
2. **Held for acceptance — implementation PRs**: upstream-clean branches
   (see checklist below), astra-tools PR marked *blocked on* the
   astra-spec release that ships the schema.
3. **This repo** stays on the fork state — the fork-only wiring below is
   exactly what makes the side-by-side submodule layout work.

## Fork-only wiring (must NOT go upstream)

### `[tool.uv.sources]` in astra-tools' `pyproject.toml`

```toml
astra-spec = { path = "../astra-spec", editable = true }
```

Resolves `astra-spec` from the sibling checkout instead of PyPI. Scope:
this affects **only uv-managed environments of the astra-tools project
itself** (`uv sync` / `uv run` in the repo) — it does *not* propagate to
anyone installing astra-tools as a package. It is still upstream-hostile
for a different reason: it forces every contributor who clones
astra-tools to have a sibling `../astra-spec` checkout. Keep it on the
fork (it matches this repo's submodule layout); strip it from the
upstream branch.

### `uv.lock` in astra-tools

Committed on the fork as a side effect of development; it pins
astra-spec to the local path source. Upstream does not track a lockfile
in astra-tools. Drop it (and gitignore it) on the upstream branch.

## Decided and staying (with rationale reviewers may ask about)

### Dependency pin `astra-spec>=0.0.13`

Reverting to `>=0.0.11` is **not an option**: the tooling hard-requires
the new schema — `semantic.py` imports `HumanRole` / `AgentRole` from
the datamodel at module import (ImportError on old astra-spec), and the
`extra="forbid"` Pydantic models of older astra-spec reject every actor
field anyway. The honest pin is the version that ships the schema
(`0.0.13` on the fork; upstream may assign a different number), with the
astra-tools PR marked blocked on the astra-spec release. This is the
normal shape for a cross-repo change.

### The `astra init` version clamp (separate small PR)

```python
# Dev/editable installs report versions like 0.0.12.post2.dev0+abc123;
# the schema's version pattern only accepts X.Y[.Z], so keep the base.
base = re.match(r"\d+\.\d+(?:\.\d+)?", spec_version)
```

A genuine standalone bug fix, not dev-only scaffolding: `astra init`
stamps the scaffold's `version:` with the installed astra-spec version
verbatim, and any non-release install (editable checkout, `pip install
git+...` between tags) reports a dynamic version like
`0.0.12.post2.dev0+abc123` — which the schema's `X.Y[.Z]` pattern
rejects, so `astra init` produced a file that fails its own
`astra validate`. For release installs the regex is a no-op. It is
unrelated to the actor layer, so cherry-pick it into its own commit/PR
("fix: astra init writes invalid version from dev installs") rather
than shipping it inside the actor PR.

## Checklist for the upstream-clean implementation branches

astra-spec (`RFC-0004-impl`):
- [ ] Drop the fork-local `Release v0.0.13` commit and `v0.0.13` tag
      (upstream cuts its own release; version numbers are theirs).
- [ ] Keep: `actor.yaml`, `analysis.yaml` / `universe.yaml` edits,
      regenerated datamodels, fixtures, `docs/specification.md`.

astra-tools (`RFC-0004-impl`):
- [ ] Remove `[tool.uv.sources]` from `pyproject.toml`.
- [ ] Remove `uv.lock`; add it to `.gitignore`.
- [ ] Cherry-pick the `astra init` version clamp into its own commit
      (or a separate PR).
- [ ] Keep the `astra-spec>=<release>` pin; note "blocked on
      astra-spec#<PR>" in the PR body.
- [ ] Re-run gates: `pytest` (207), `ruff check`, `ruff format --check`,
      `mypy src/` (strict) — all green on the fork as of 2026-07-30.

## Known limitations to disclose in review

- The bare actor-id shorthand (`proposed_by: jane`) is valid per the
  schema and the Pydantic path, but the generated *dataclass* loader
  cannot coerce a string into `Attribution` (pythongen `any_of`
  limitation). Documented upstream-style via
  `tests/data/problem/valid/Analysis-003-shorthand-attribution.yaml`.
- LinkML `rules:` compile to JSON Schema if/then (astra-spec CI) but not
  to Pydantic validators — astra-tools' semantic layer is the runtime
  enforcement point. Actor rules are written one-forbid-per-slot because
  a multi-slot ABSENT postcondition compiles to `not: {required: [...]}`,
  which only fires when *all* slots are present (same convention as the
  existing `from_alias_forbids_*` rules).
- The `ResearcherId` at-least-one-identifier constraint (class-level
  `any_of`) compiles to neither Pydantic nor JSON Schema; it is enforced
  only by astra-tools (`EMPTY_IDENTIFIERS`).
- **Open defect, must be fixed before the implementation PR.** The explicit
  `union(string, DecisionSelection)` on the two `decisions` slots compiles to a
  self-contradictory JSON Schema on linkml 1.10.0, so *every* universe file in
  astra-spec fails generated-JSON-Schema validation, including files that predate
  the actor layer. `astra validate` is unaffected because it runs through the
  Pydantic models. astra-spec's suite stays green because valid fixtures load
  through the gen-python dataclasses and only invalid fixtures reach the
  JSON-Schema validator. Until this is fixed, the backward-compatibility claim
  holds for the Pydantic and dataclass paths but not for the generated JSON
  Schema. Reproduction, bisect, and two verified fixes are in issue #1.
