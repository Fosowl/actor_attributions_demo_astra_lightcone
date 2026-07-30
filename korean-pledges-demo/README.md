# Korean pledges: a real actor-attribution example

The iris example next door is a toy. This one is a slice of a real study,
with the real failure mode the actor layer exists for.

## The 90-second story

A dissertation pipeline filters Korean presidential/district election
pledge sentences, deciding which ones genuinely belong to a forest-policy
topic cluster. This demo ships the complete slice for one cluster
(Forest Bioenergy): 218 real sentences with their 18-d embedding
coordinates.

The accepted filter retains **68/218 (31.2%)**. Every alternative that was
considered retains more — the simplest one more than twice as much — and
qualitative reading shows the extra sentences are off-topic (defense
industry, electronics, urban parks). Each alternative was proposed by the
AI assistant during analysis and excluded by the human researcher. A plain
ASTRA file records *that* they were excluded and why. The actor layer
records *who* proposed them, *who* excluded them, and *when* — which is
exactly what a methods reviewer, a committee, or a future collaborator
needs when the tempting number resurfaces.

## Run it

    ../install_and_validate.sh          # once: build the shared venv
    ./run_demo.sh                       # baseline: 68/218 (31.2%)
    ./run_demo.sh -u what-if-euclidean  # 161/218 (73.9%) + the sentences it lets in
    ./run_demo.sh -u what-if-chisq      # 114/218 (52.3%), the other tempting number
    ./run_demo.sh --validate            # astra validate + actor-attributed info

Tests (`env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v`) enforce
two things: point-level agreement with the study's recorded per-sentence
decisions, and that every number quoted in `analysis/astra.yaml` is one
this pipeline computes from `data/`.

## Why the counterfactuals are not universe files

ASTRA refuses a universe that selects an excluded option
(`EXCLUDED_OPTION_SELECTED`) — the excluded branches are out of the valid
multiverse by construction. So `analysis/universes/` holds only the
accepted `baseline`. The two what-if runs are **diagnostic replays, not
ASTRA universes**: ASTRA validation still rejects them as selectable
analysis branches, and the demo executes them only to show what the
excluded options would have retained (they pass explicit decision values
to the filter, the same values the recipe commands in `analysis/astra.yaml`
parameterize over). The refusal is enforcement working, not a limitation.

| Run | Retained | Relation to the study |
|---|---:|---|
| baseline (mahalanobis + LOO p99) | 68/218 (31.2%) | exact per-cluster study value, per-sentence tested |
| what-if-euclidean | 161/218 (73.9%) | exact per-cluster study value, per-sentence tested |
| what-if-chisq (shrinkage beta 0.75) | 114/218 (52.3%) | demo recomputation on this cluster; the study reported this variant corpus-wide |

## What was simplified

- The full study varies a third decision (out-of-sample centroid
  correction); this demo hard-codes its accepted value. That correction is
  itself load-bearing: every distance is measured from the pledge slice's
  own pooled centroid, with the reference cluster supplying shape
  (covariance) and threshold. The reference centroid does not anchor
  membership — the reference cluster's geometry does.
- The full study covers 8 clusters and 1,662 sentences; this demo ships
  the one cluster where the metric choice matters most. Completeness of
  the slice keeps the pooled centroid identical to the study's; exactness
  of the two headline numbers is then verified per-sentence against the
  study's recorded keep/remove decisions (218/218 agreement, enforced by
  tests). The chi-squared counterfactual is a demo recomputation on this
  cluster; the study reported that variant corpus-wide.

## Data

- `data/pledges_subset.csv` — sentence text (Korean), president, cluster,
  D1..D18. District/party metadata deliberately not included.
- `data/reference_stats.npz` — derived reference-corpus statistics
  (centroid, ridged covariance, leave-one-out distance distributions);
  no reference text.
- The source corpus is private to the originating research group;
  `tools/make_subset.py` regenerates these files for anyone with access.
- Decision provenance: internal TRACE record on file, session
  trace_20260509_305aaf (2026-05-09); the source record is not published
  with this artifact.
