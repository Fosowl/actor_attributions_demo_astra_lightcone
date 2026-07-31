# CLAUDE.md — live-demo workspace

A researcher's working directory for an out-of-sample filtering analysis,
as it stands **before** any decision record exists: data, the filter
script, and informal working notes. Nothing here records which options
were considered or who chose them yet. Creating that record is the work.

This directory is used in front of a live audience. Optimize for short,
legible turns.

## Response style

- **Two or three sentences per turn.** Longer only when asked to explain.
- **No preamble, no recap, no next-steps.** Answer, then stop.
- Let command output and file contents speak; quote only the number or
  error that matters.
- Plain words. The audience does not share terms like anisotropic,
  covariance, or quantile — say "stretched shape", "each topic's spread",
  "cut-off".
- Prose over bullet lists unless the answer is genuinely a list.

## Scope

- **Work only inside `live-demo/`.** Sibling directories in this repo
  contain finished examples; reading them gives away the exercise, so do
  not open them unless explicitly asked.
- Do exactly what is asked and nothing adjacent. Do not run test suites,
  survey the repo, or check git state unprompted.
- `notes/` holds the researcher's working notes. Read them when asked,
  not before.
- Write new files to `/tmp` unless told otherwise.

## Commands

The shared virtualenv is one level up. Always clear `PYTHONPATH`:

```bash
env -u PYTHONPATH ../.venv/bin/python src/filter.py --compare
env -u PYTHONPATH ../.venv/bin/python src/filter.py --compare --show-disagreement
env -u PYTHONPATH ../.venv/bin/astra validate <file.yaml>
env -u PYTHONPATH ../.venv/bin/astra validate <universe.yaml> -a <analysis.yaml>
env -u PYTHONPATH ../.venv/bin/astra info -f <file.yaml> -d
```

`src/filter.py --help` documents the rest. If the venv is missing, run
`../install_and_validate.sh` from the repo root.

## Writing an ASTRA analysis file

ASTRA (`astra-spec`, v0.0.13) describes an analysis as inputs, outputs,
and the decisions behind them. Skeleton:

```yaml
id: snake_case_id                 # ^[a-z][a-z0-9_]*$
version: "0.0.13"
name: "Human readable name"
description: |
  What this analysis decides.

inputs:
  - id: some_input
    type: data
    source: "data/file.csv"
    description: >-
      What it is.

outputs:
  - id: some_output
    type: data                    # data | metric | figure | table | report
    description: What it holds.
    decisions: [decision_id]      # every {decisions.x} used below must be listed
    recipe:
      command: >-
        python src/script.py --flag {decisions.decision_id}

decisions:
  decision_id:
    label: "Short label"
    rationale: >-
      Why this choice matters.
    default: chosen_option
    options:
      chosen_option:
        label: "..."
        description: "..."
      rejected_option:
        label: "..."
        description: "..."
        excluded: true
        excluded_reason: >-
          The technical reason it was ruled out.
```

Recipe commands accept only `{inputs}`, `{inputs.<id>}`,
`{decisions.<id>}`, and `{output}` as placeholders.

## The actor layer (RFC-0003)

Optional, additive. A registry of who was involved, plus attribution on
the options of a decision:

```yaml
actors:
  some_person:                    # id pattern ^[a-z][a-z0-9_]*$
    type: human                   # humans may carry identifiers: {orcid: ...}
  some_agent:
    type: agent
    model: model-id               # REQUIRED for agents
    harness: harness-name         # optional
    version: "2026-05"            # optional

decisions:
  decision_id:
    options:
      rejected_option:
        excluded: true
        proposed_by: {actor: some_agent, role: methodology}
        excluded_by: {actor: some_person, role: validation}
        excluded_at: "2026-01-31"
        exclusion_rationale: >-
          One line: the judgment behind ruling it out.
        excluded_reason: >-
          The fuller technical reason (predates the actor layer).
```

Enforced at validation time:

- Agents require `model`; humans forbid `model`/`harness`/`version`;
  agents forbid `identifiers`.
- An attribution is a bare actor id or `{actor, role}`. Roles come from a
  CRediT-derived set — `methodology`, `validation`, `data_curation`,
  `software` suit either type; `conceptualization` and `supervision` are
  human-only.
- `excluded_by`, `excluded_at`, and `exclusion_rationale` each require
  `excluded: true` on the same option.
- A universe file may not select an excluded option.
