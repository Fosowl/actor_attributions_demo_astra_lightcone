# Korean pledges demo — design

Status: approved design; amended during implementation (see Amendments).

## Amendments (build-time)

- ASTRA semantic validation refuses a universe that selects an excluded
  option (`EXCLUDED_OPTION_SELECTED`), so the two what-if universe files
  cannot exist as valid universes. `baseline.yaml` is the only committed
  universe; the counterfactuals run as named decision-flag presets through
  the filter CLI — the same `{decisions.*}` recipe form the analysis file
  declares. The refusal itself is documented in the README as part of the
  enforcement story.
- Recipe commands accept only `{inputs}`/`{inputs.<id>}`/`{decisions.<id>}`/
  `{output}` placeholders, so the analysis recipes pass decisions as
  `--metric`/`--threshold` flags rather than a universe name.
- The reference statistics are derived from the study's operative reference
  file (`embeddings6_projected.csv`) with its exact conventions (ridged
  covariance `np.cov + 1e-6*I`; full-LOO Mahalanobis distribution;
  LOO-centroid non-squared Euclidean distribution), recovered by matching
  the study's per-sentence distances and keep decisions exactly.

## Purpose

A second worked example for this repo, beside the iris toy: a real study,
real data, and a real failure mode that the RFC-0003 actor layer addresses.
Target format is a live 3–5 minute demo for an audience unfamiliar with
ASTRA, the actor layer, or the underlying study. Everything on screen is
computed live from data committed in this repo.

## Background the demo must carry

- ASTRA encodes an analysis's decision space: the options considered, the
  ones excluded, and why. The actor layer (RFC-0003, implemented in the two
  submodules here) adds *who* proposed and excluded each option, and when.
- The study: filtering out-of-sample Korean district-level election pledge
  sentences against an 18-dimensional reference embedding derived from a
  905-sentence forest-policy planning corpus. The contested quantity is
  retention — what share of pledge sentences survive the filter.
- The real problem: every rejected filter variant produced a *higher*
  retention than the one chosen, so the decision is maximally exposed to
  tuning toward a target band. On the demo cluster (forest bioenergy),
  switching the distance metric from Mahalanobis to Euclidean lifts
  retention from roughly a third to roughly three quarters — while
  qualitative reading shows the extra sentences are off-topic. A plain
  ASTRA file records that Euclidean was excluded and why; only the actor
  layer records that the agent proposed it and the human excluded it.

## Layout

New top-level directory; the two submodules and the iris example are
untouched.

```
korean-pledges-demo/
  README.md               # the 90-second story + run instructions
  DEMO_SCRIPT.md          # live-demo chat prompt sequence (see below)
  data/
    pledges_subset.csv    # all real OOS sentences for the demo cluster(s):
                          # text_sentence, president, cluster, D1..D18
    reference_stats.npz   # derived per-cluster reference mean, covariance,
                          # LOO D^2 quantiles — numeric only, no text
  src/
    filter_pledges.py     # pure-function filter:
                          # metric in {mahalanobis, euclidean}
                          # threshold in {loo_alpha_01, chisq_shrinkage}
  analysis/
    astra.yaml            # attributed spec: 2 decisions, actors registry
    universes/
      baseline.yaml
      what-if-euclidean.yaml
      what-if-chisq.yaml
  tools/
    make_subset.py        # one-time extraction from the private source
                          # corpus; takes --source-dir; the corpus itself
                          # is not distributed
  tests/
    test_demo_numbers.py  # invariant guard + validation gate (see Testing)
  run_demo.sh             # wraps the repo venv: filter run + astra
                          # validate + astra info
```

## Data

- The subset is a **complete vertical slice**: every out-of-sample pledge
  sentence assigned to the demo cluster(s), across all three presidencies.
  Completeness is what makes the live per-cluster numbers identical to the
  study's real values rather than approximations.
- Kept columns: `text_sentence`, `president`, `cluster`, `D1..D18`.
  District, party, administrative codes, and similarity/diagnostic columns
  are deliberately excluded from the published subset.
- `reference_stats.npz` carries only derived statistics of the reference
  corpus (per-cluster mean, covariance, leave-one-out D^2 quantiles at the
  alphas the demo uses). No reference text is distributed.
- Primary demo cluster: cluster 6 (forest bioenergy), the strongest
  metric-flip story. If its chi-squared-threshold number turns out
  undramatic when computed, the fallback is adding one more complete
  cluster slice — never changing the invariant below.

## The honesty invariant

**Every number quoted in `analysis/astra.yaml` is a number this repo's
pipeline computes from the committed data.** The implementation first
recomputes the per-cluster values from the real data; only reproduced
values are written into the YAML rationales. If recomputation cannot
reproduce the study's values, implementation stops and the discrepancy is
reconciled — numbers are never adjusted to fit a narrative. A test
enforces the invariant permanently (see Testing).

## The attributed analysis file

- Two decisions, simplified from the study's three:
  - `distance_metric`: `mahalanobis` (accepted) vs `euclidean` (excluded).
  - `threshold_rule`: `loo_alpha_01` (accepted) vs `chisq_shrinkage`
    (excluded).
  - The study's third decision (out-of-sample centroid correction) is
    hard-coded to its accepted value (pooled) and noted in the README as
    simplified out.
- Rationales are one to two sentences each and quote the demo's own
  per-cluster numbers.
- Actors registry: `oliver` (human) and `claude_code` (agent,
  `model: claude-opus-4-8`, `harness: claude-code`). The model id is
  supplied by the researcher; the original working sessions predate
  model-id capture. This appears as a single YAML comment and is not part
  of the demo flow.
- Each excluded option carries the full attribution set: `proposed_by:
  claude_code`, `excluded_by: oliver`, `excluded_at: "2026-05-09"`, and an
  `exclusion_rationale` distinct from the technical `excluded_reason`.
- Universe files exercise both selection forms the schema allows:
  `baseline.yaml` uses the attribution-object form (`selected_by`,
  `reviewed_by`); the two what-if universes use the scalar shorthand. Both
  render in `astra info`.

## DEMO_SCRIPT.md

A numbered sequence of chat prompts to type into an agentic coding
assistant on stage. The committed `analysis/astra.yaml` doubles as the
reference output the generated file is compared against. The sequence:

1. **Run the pipeline** — read `data/` and `src/filter_pledges.py`, run
   the baseline filter (Mahalanobis, alpha 0.01), report retention.
2. **Show the real problem** — run the Euclidean variant, diff the
   additionally admitted sentences, translate three of them (the audience
   sees off-topic pledges the tempting filter admits).
3. **Generate the spec** — write an ASTRA analysis spec for the pipeline:
   both decisions, all options considered, rejected options marked
   `excluded` with reasons.
4. **Attribute it** — register the two actors and attribute each
   exclusion (agent proposed, human excluded, date, rationale).
5. **Prove it** — `astra validate` the generated file, then `astra info`
   to display who excluded what and why.

## Code standards

`src/filter_pledges.py` and `tools/make_subset.py` follow the repo-wide
Python conventions: pure functions with explicit inputs and outputs,
Pydantic v2 models for structured configuration crossing function
boundaries, documented side effects, pyright basic clean. Failure is loud:
CSV schema mismatch, missing npz keys, and unknown universe names all
raise with specific messages — nothing degrades silently.

## Testing

`pytest`, against the committed real data (no mocks):

1. **Invariant guard** — parse every percentage quoted in
   `analysis/astra.yaml`, recompute each via the pipeline from
   `data/`, assert exact match at the quoted precision.
2. **Validation gate** — `astra validate` passes for the analysis file and
   all three universes, run through the repo venv created by
   `install_and_validate.sh`.

## Out of scope

- No changes to the `astra-spec` / `astra-tools` submodules or upstream PR
  content.
- No changes to the iris example.
- No GUI; the demo is CLI plus one YAML file on screen.

## Acceptance criteria

- `./install_and_validate.sh korean-pledges-demo/analysis/astra.yaml`
  passes, including automatic sibling-universe validation.
- `pytest` green in `korean-pledges-demo/tests/`.
- `run_demo.sh` (baseline and both what-if universes) prints exactly the
  numbers quoted in `analysis/astra.yaml`.
- pyright basic reports no errors on `src/`, `tools/`, `tests/`.
