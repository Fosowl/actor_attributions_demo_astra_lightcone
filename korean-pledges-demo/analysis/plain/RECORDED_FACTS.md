# Recorded facts for the actor layer

Source: internal records on file — TRACE session trace_20260509_305aaf
(the assumed-Mahalanobis state) and the manuscript revision round of
2026-06-11 that directed and verified the switch to Euclidean; source
records are not published with this artifact. The agent's model id was
supplied by the researcher (the original sessions predate model-id
capture).

Encode these facts, exactly, when adding the RFC-0003 actor layer to a
copy of `plain/astra.yaml`:

- Actors:
  - `oliver` — human (the researcher); ORCID `0000-0002-5967-1314`.
  - `claude_code` — agent; model `claude-opus-4-8`; harness `claude-code`;
    version `"2026-05"`.
- `distance_metric.mahalanobis` (already excluded): proposed by
  `claude_code` (role `methodology`) as the theoretically superior
  shape-aware choice; excluded by `oliver` (role `validation`) on
  `2026-06-11`. One-line rationale: the assumed-best option, excluded
  after inspection — retention was implausibly low and reviewing the
  retained sentences showed the simple metric produced the better set;
  theory needed a human override.

The attributed reference output is `../astra.yaml`. A correct result
validates green with
`env -u PYTHONPATH ../.venv/bin/astra validate <file>` (run from
`korean-pledges-demo/`) and differs from `plain/astra.yaml` only by the
actor registry and the attribution fields.
