# Live-demo script (chat-first)

The demo is driven through an agentic coding assistant (e.g. Claude Code)
opened at the **repo root** — the root `CLAUDE.md` primes it with the
actor-layer authoring reference, so these prompts work without warm-up.
Type the prompts in order; the assistant runs every command itself.

Prereq: `./install_and_validate.sh` has been run once.

Framing (say once, before prompt 4): the committed
`analysis/astra.yaml` is the record. In prompt 4 the assistant encodes
facts from `analysis/plain/RECORDED_FACTS.md` into schema fields — it
formats recorded provenance, it does not invent it.

A terminal-only fallback (no assistant) is at the bottom.

---

**1 — Run the real pipeline**

> Read korean-pledges-demo/README.md, then run ./run_demo.sh in
> korean-pledges-demo and report what was filtered and what the retention
> number means.

Expected: 68/218 (31.2%) retained — shape-aware metric, conservative
threshold, and the assistant explains the filter in one breath.

**2 — Excluded means excluded (enforcement)**

> Create a scratch universe file in /tmp that selects the excluded
> euclidean option and validate it against
> korean-pledges-demo/analysis/astra.yaml with the repo venv's astra.
> What happens, and why?

Expected: `EXCLUDED_OPTION_SELECTED` — the assistant explains that an
excluded option is not a selectable branch; everything after this is a
diagnostic replay for audit.

**3 — Show the real problem (diagnostic replay)**

> Now run ./run_demo.sh -u what-if-euclidean in korean-pledges-demo, open
> analysis/examples/euclidean_extras.md, and tell me whether those three
> sentences belong in a "Forest Bioenergy" topic cluster.

Expected: retention jumps to 161/218 (73.9%); the pre-translated sentences
are defense industry, urban parks, food/bio industry — off-topic. The
tempting number admits junk.

**4 — THE FILL-IN: the assistant adds the actor layer**

> Copy korean-pledges-demo/analysis/plain/astra.yaml to /tmp/attributed.yaml.
> It records the decision space but not WHO did anything. Read
> korean-pledges-demo/analysis/plain/RECORDED_FACTS.md and add the
> RFC-0003 actor layer to the copy: register the actors and attribute both
> exclusions exactly as recorded. Then validate the file with the repo
> venv's astra.

Expected: the assistant edits the YAML live — an `actors:` registry plus
`proposed_by` / `excluded_by` / `excluded_at` / `exclusion_rationale` on
each excluded option — and validation comes back green. The actor layer is
enforced schema, not decoration: an agent actor without `model`, an
unknown actor id, or attribution on a non-excluded option would all fail.

**5 — Prove it is the same record**

> Diff /tmp/attributed.yaml against the committed
> korean-pledges-demo/analysis/astra.yaml and summarize what the actor
> layer added.

Expected: the diff is essentially the ~30-line actor delta (registry + two
attribution blocks) — the plain twin differs from the committed file by
exactly the actor layer, so the audience sees the layer, not YAML noise.

**6 — The payoff: who said no**

> Run: env -u PYTHONPATH .venv/bin/astra info -f
> korean-pledges-demo/analysis/astra.yaml -d
> and tell me who excluded what, and when.

Expected: on each excluded option, "proposed by claude_code; excluded by
oliver (validation)" with the date and rationale. Closing line: without
the actor layer the file says WHAT was excluded and why; with it, it says
who proposed the tempting number, who refused it, and when.

---

## Terminal-only fallback (no assistant, ~3 min)

From `korean-pledges-demo/`:

```bash
./run_demo.sh                        # 68/218 (31.2%)
cat > /tmp/bad-universe.yaml <<'EOF'
id: bad_universe
description: "scratch"

decisions:
  distance_metric: euclidean
  threshold_rule: loo_alpha_01
EOF
env -u PYTHONPATH ../.venv/bin/astra validate /tmp/bad-universe.yaml -a analysis/astra.yaml
                                     # EXCLUDED_OPTION_SELECTED
./run_demo.sh -u what-if-euclidean   # 161/218 (73.9%) + admitted sentences
open analysis/examples/euclidean_extras.md
./run_demo.sh -u what-if-chisq       # 114/218 (52.3%), demo recomputation
diff analysis/plain/astra.yaml analysis/astra.yaml   # the actor-layer delta
env -u PYTHONPATH ../.venv/bin/astra info -f analysis/astra.yaml -d
```
