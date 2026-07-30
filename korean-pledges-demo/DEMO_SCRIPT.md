# Live-demo script

Prompts to type into an agentic coding assistant (e.g. Claude Code opened
at the repo root), in order. Prereq: `./install_and_validate.sh` has been
run once. The committed `analysis/astra.yaml` is the reference output for
prompt 5 — if the generated file differs, diff them on screen; that
comparison is itself a good demo beat.

Framing (say this once, before prompts 4-5): the committed
`analysis/astra.yaml` is the record; the live generation re-derives it
from facts stated in the prompts, which come from that record. The
assistant formats provenance here — it does not invent it.

**1 — Run the real pipeline**

> Read korean-pledges-demo/README.md, then run ./run_demo.sh in
> korean-pledges-demo. Report what was filtered and why that number.

Expected: 68/218 (31.2%) retained — shape-aware metric, conservative
threshold.

**2 — Enforcement first: excluded means excluded**

> Create a scratch universe file that selects the excluded euclidean
> option and validate it with
> ../.venv/bin/astra validate <scratch file> -a korean-pledges-demo/analysis/astra.yaml

Expected: `EXCLUDED_OPTION_SELECTED` — an excluded option is not a
selectable branch of the multiverse. Say it out loud: everything that runs
after this point is a diagnostic replay for audit, not a valid universe.

**3 — Show the real problem (diagnostic replay)**

> Now run ./run_demo.sh -u what-if-euclidean. Then open
> korean-pledges-demo/analysis/examples/euclidean_extras.md and tell me
> whether the three sentences it lists belong in a "Forest Bioenergy"
> topic cluster.

Expected: retention jumps to 161/218 (73.9%); the pre-translated sentences
are about defense industry, urban parks, food/bio industry — off-topic.
The tempting number admits junk. (Translations are committed so the demo
does not depend on live translation quality.)

**4 — Generate the decision record**

> Write an ASTRA analysis spec (schema version 0.0.13) for this filter in
> a scratch file: decisions distance_metric (mahalanobis, euclidean) and
> threshold_rule (loo_alpha_01, chisq_shrinkage), with the options we just
> compared, the rejected ones marked excluded with excluded_reason quoting
> the numbers you just computed.

Expected: a valid plain ASTRA file — decision space captured, but no
record of WHO ruled anything out.

**5 — Attribute it**

> Add the RFC-0003 actor layer: register actors oliver (human) and
> claude_code (agent, model claude-opus-4-8, harness claude-code). The
> assistant proposed euclidean and chisq_shrinkage during the original
> analysis; the researcher excluded both on 2026-05-09. Attribute each
> exclusion (proposed_by, excluded_by, excluded_at) and add a one-sentence
> exclusion_rationale to each.

Expected: the same file, now answering who/when/why — compare with the
committed korean-pledges-demo/analysis/astra.yaml.

**6 — Prove it**

> Validate the generated file, then the committed one, with:
> ../.venv/bin/astra validate <file>
> and show who excluded what with:
> ../.venv/bin/astra info -f korean-pledges-demo/analysis/astra.yaml -d

Expected: validation green (the actor layer is enforced, not decorative);
`astra info` renders the actor registry and, on each excluded option,
"proposed by claude_code; excluded by oliver (validation)".

