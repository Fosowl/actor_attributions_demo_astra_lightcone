# Recorded facts for the actor layer

Source: internal TRACE record on file, session trace_20260509_305aaf
(2026-05-09); the source record is not published with this artifact. The
agent's model id was supplied by the researcher (the original sessions
predate model-id capture).

Encode these facts, exactly, when adding the RFC-0003 actor layer to a
copy of `plain/astra.yaml`:

- Actors:
  - `oliver` — human (the researcher).
  - `claude_code` — agent; model `claude-opus-4-8`; harness `claude-code`;
    version `"2026-05"`.
- `distance_metric.euclidean` (already excluded): proposed by
  `claude_code` (role `methodology`); excluded by `oliver` (role
  `validation`) on `2026-05-09`. One-line rationale: the tempting number —
  more than twice the retention from the simplest metric — rejected
  because qualitative reading showed the extra sentences are off-topic and
  survive only because Euclidean ignores the cluster's elongated shape.
- `threshold_rule.chisq_shrinkage` (already excluded): proposed by
  `claude_code` (role `methodology`); excluded by `oliver` (role
  `validation`) on `2026-05-09`. One-line rationale: also a higher number,
  rejected anyway — beta has no principled basis and the variant changes
  threshold source and covariance source at once, so nothing can be
  attributed.

The attributed reference output is `../astra.yaml`. A correct result
validates green with
`env -u PYTHONPATH ../.venv/bin/astra validate <file>` (run from
`korean-pledges-demo/`) and differs from `plain/astra.yaml` only by the
actor registry and the attribution fields.
