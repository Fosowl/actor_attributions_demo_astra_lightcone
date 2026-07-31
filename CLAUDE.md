# CLAUDE.md — actor_attributions_demo_astra_lightcone

Demo repository for the RFC-0003 **actor attribution** layer on ASTRA.
The two submodules carry the working implementation: `astra-spec` (LinkML
schema + generated datamodels) and `astra-tools` (the `astra` CLI and the
semantic validator, which is the actor layer's runtime enforcement point).

## Layout

- `astra-spec/`, `astra-tools/` — fork submodules with the actor layer.
- `astra-tools/examples/iris/` — toy attributed example.
- `live-demo/` — a working directory as it stands *before* a decision
  record exists (data, filter script, working notes), used to author one
  live; `live-demo/reset.sh` clears a run's output so it can be repeated.
  **It has its own `CLAUDE.md`, and it is self-contained: when working
  there, do not read `korean-pledges-demo/`, the examples, or
  `docs/live-demo-walkthrough.md` — they hold the finished version of the
  same analysis and reading them defeats the exercise.**
- `korean-pledges-demo/` — real-data example: 218 Korean pledge sentences,
  a runnable filter (`run_demo.sh`), an attributed analysis
  (`analysis/astra.yaml`), a plain un-attributed twin
  (`analysis/plain/astra.yaml`) with its recorded facts
  (`analysis/plain/RECORDED_FACTS.md`), and `DEMO_SCRIPT.md` (live-demo
  prompts).
- `install_and_validate.sh` — builds the shared venv at `.venv/` and
  validates an analysis plus its sibling universes.

## Commands (always via the repo venv; never a global astra)

```bash
./install_and_validate.sh                  # once; ends "All checks passed."
env -u PYTHONPATH .venv/bin/astra validate <analysis.yaml>
env -u PYTHONPATH .venv/bin/astra validate <universe.yaml> -a <analysis.yaml>
env -u PYTHONPATH .venv/bin/astra info -f <analysis.yaml> -d
cd korean-pledges-demo && ./run_demo.sh [-u <run-name>] [--validate]
```

Tests for the Korean demo (from `korean-pledges-demo/`):
`env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v`

## Actor layer authoring reference (RFC-0003)

Registry — one `actors:` map at analysis level:

```yaml
actors:
  jane:                      # id pattern ^[a-z][a-z0-9_]*$
    type: human              # human may carry identifiers: {orcid: ...}
  assistant:
    type: agent
    model: claude-opus-5     # REQUIRED for agents (MISSING_AGENT_MODEL)
    harness: claude-code     # optional
    version: "2026-07"       # optional
```

Rules enforced by the semantic validator (astra-tools):
- Agent actors REQUIRE `model`; humans FORBID `model`/`harness`/`version`;
  agents forbid `identifiers`.
- Attribution slots take a bare actor id (`proposed_by: assistant`) or an
  object (`proposed_by: {actor: assistant, role: methodology}`). The role
  must be legal for the actor's type: agents use `AgentRole` (= HumanRole
  minus `conceptualization` and `supervision`; `methodology`,
  `validation`, `data_curation`, `software` are all agent-legal).
- Exclusion record on an option: `excluded: true` plus optional
  `excluded_by`, `excluded_at` ("YYYY-MM-DD"), `exclusion_rationale`
  (attributed one-line judgment) — each of those three REQUIRES
  `excluded: true` (ORPHAN_* errors otherwise). `excluded_reason` is the
  fuller technical reason and predates the actor layer.
- Universe selections: scalar shorthand (`decision: option_id`) or object
  (`{option_id: ..., selected_by: ..., reviewed_by: ...}`).
- A universe may NOT select an excluded option (EXCLUDED_OPTION_SELECTED).
  Excluded branches may be replayed diagnostically through explicit
  decision values, never as universes.
- Recipe command placeholders: only `{inputs}`, `{inputs.<id>}`,
  `{decisions.<id>}`, `{output}`.

## Repo conventions

- Never edit the submodules from this repo; changes go through their own
  branches/PRs.
- In `korean-pledges-demo/analysis/astra.yaml`, every quoted percentage
  and N/218 fraction must be a value `src/filter_pledges.py` computes from
  `data/` — `tests/test_demo_numbers.py` fails otherwise. Never hand-edit
  a number.
- Scratch/generated files belong in `/tmp` or an ignored path, not in the
  tree.
