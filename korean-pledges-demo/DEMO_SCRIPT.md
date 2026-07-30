# Live-demo script

Prompts to type into an agentic coding assistant (e.g. Claude Code opened
at the repo root), in order. Prereq: `./install_and_validate.sh` has been
run once. The committed `analysis/astra.yaml` is the reference output for
prompt 4 — if the generated file differs, diff them on screen; that
comparison is itself a good demo beat.

**1 — Run the real pipeline**

> Read korean-pledges-demo/README.md, then run ./run_demo.sh in
> korean-pledges-demo. Report what was filtered and why that number.

Expected: 68/218 (31.2%) retained — shape-aware metric, conservative
threshold.

**2 — Show the real problem**

> Now run ./run_demo.sh -u what-if-euclidean. Translate the first three
> Korean sentences it retains that the baseline removes, and say whether
> they belong in a "Forest Bioenergy" topic cluster.

Expected: retention jumps to 161/218 (73.9%); the translated sentences are
about defense industry, urban parks, food/bio industry — off-topic. The
tempting number admits junk.

**3 — Generate the decision record**

> Write an ASTRA analysis spec (schema version 0.0.13) for this filter in
> a scratch file: decisions distance_metric (mahalanobis, euclidean) and
> threshold_rule (loo_alpha_01, chisq_shrinkage), with the options we just
> compared, the rejected ones marked excluded with excluded_reason quoting
> the numbers you just computed.

Expected: a valid plain ASTRA file — decision space captured, but no
record of WHO ruled anything out.

**4 — Attribute it**

> Add the RFC-0003 actor layer: register actors oliver (human) and
> claude_code (agent, model claude-opus-4-8, harness claude-code). The
> assistant proposed euclidean and chisq_shrinkage during the original
> analysis; the researcher excluded both on 2026-05-09. Attribute each
> exclusion (proposed_by, excluded_by, excluded_at) and add a one-sentence
> exclusion_rationale to each.

Expected: the same file, now answering who/when/why — compare with the
committed korean-pledges-demo/analysis/astra.yaml.

**5 — Prove it**

> Validate the file with the astra CLI from .venv, then run
> astra info -f on it with -d and show me who excluded what.

Expected: validation green (the actor layer is enforced, not decorative);
`astra info` renders the actor registry and, on each excluded option,
"proposed by claude_code; excluded by oliver".

**Optional encore — enforcement is real**

> Create a universe file that selects the excluded euclidean option and
> validate it against the analysis.

Expected: `EXCLUDED_OPTION_SELECTED` — ASTRA refuses to treat an excluded
option as a live branch of the multiverse.
