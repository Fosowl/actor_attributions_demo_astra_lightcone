# Korean pledges: a real actor-attribution example

The iris example next door is a toy. This one is a slice of a real study,
with the real failure mode the actor layer exists for: **the
theoretically better method lost to the evidence, and a human had to make
that call.**

## The 90-second story

A dissertation pipeline filters Korean presidential/district election
pledge sentences, deciding which ones genuinely belong to a forest-policy
topic cluster. This demo ships the complete slice for one cluster
(Forest Bioenergy): 218 real sentences with their 18-d embedding
coordinates.

Theory said use **Mahalanobis** distance — it adapts to each topic
cluster's shape, so on paper it is the better membership test, and it was
the assumed choice. But its retention came out implausibly low: 50.9%
corpus-wide, and on the study's Climate Adaptation cluster it kept 0 of 2
sentences. With per-cluster covariances estimated from small reference
samples in 18 dimensions, the "shape" it adapted to was substantially
estimation noise. The simple **Euclidean** filter retained 68.8%
corpus-wide (1,143/1,662), and close review of the retained sentences
during manuscript revision confirmed its set was superior. The final
manuscript adopted Euclidean.

On this demo's cluster the contrast is: Euclidean **161/218 (73.9%)**
accepted, Mahalanobis **68/218 (31.2%)** excluded. A plain ASTRA file
records *that* Mahalanobis was excluded and why. The actor layer records
*who* proposed the theoretically-better option, *who* overruled it after
inspection, and *when* — the human judgment call that no metric could have
made, preserved where a reviewer or future collaborator can find it.

## Run it

    ../install_and_validate.sh          # once: build the shared venv
    ./run_demo.sh                       # accepted baseline: 161/218 (73.9%)
    ./run_demo.sh -u what-if-mahalanobis  # 68/218 (31.2%) + what it throws away
    ./run_demo.sh --validate            # astra validate + actor-attributed info

Tests (`env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v`) enforce
two things: point-level agreement with the study's recorded per-sentence
decisions for BOTH metrics (218/218 sentences each), and that every number
quoted in the analysis files is one this pipeline computes from `data/`.

| Run | Retained | Relation to the study |
|---|---:|---|
| baseline (euclidean, accepted) | 161/218 (73.9%) | exact per-cluster study value, per-sentence tested |
| what-if-mahalanobis (excluded) | 68/218 (31.2%) | exact per-cluster study value, per-sentence tested |

Corpus-wide (study-reported, not recomputed here): Euclidean 1,143/1,662
(68.8%) vs Mahalanobis 846/1,662 (50.9%).

## Why the counterfactual is not a universe file

ASTRA refuses a universe that selects an excluded option
(`EXCLUDED_OPTION_SELECTED`) — excluded branches are out of the valid
multiverse by construction. So `analysis/universes/` holds only the
accepted `baseline`, and `what-if-mahalanobis` is a **diagnostic replay,
not an ASTRA universe**: the demo executes it only to show what the
theoretically favored filter would have discarded. The refusal is
enforcement working, not a limitation.

## What was simplified

- The full study also varied the threshold rule and the location
  correction; this demo hard-codes their accepted values (99th-percentile
  reference leave-one-out quantile at alpha = 0.01; distances measured
  from the pledge slice's pooled centroid, with the reference cluster
  supplying shape and threshold).
- The full study covers 8 clusters and 1,662 sentences; this demo ships
  the one cluster where the metric contrast is most dramatic.
  Completeness of the slice keeps the pooled centroid identical to the
  study's; exactness of both headline numbers is then verified
  per-sentence against the study's recorded keep/remove decisions
  (218/218 agreement for each metric, enforced by tests).

## Data

- `data/pledges_subset.csv` — sentence text (Korean), president, cluster,
  D1..D18. District/party metadata deliberately not included.
- `data/reference_stats.npz` — derived reference-corpus statistics
  (centroid, ridged covariance, leave-one-out distance distributions);
  no reference text.
- The source corpus is private to the originating research group;
  `tools/make_subset.py` regenerates these files for anyone with access.
- Decision provenance: internal records on file — TRACE session
  trace_20260509_305aaf (the assumed-Mahalanobis state) and the manuscript
  revision round of 2026-06-11 that directed and verified the switch to
  Euclidean. Source records are not published with this artifact.
