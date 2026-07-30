# Live-demo script (chat-first)

The demo is driven through an agentic coding assistant (e.g. Claude Code)
opened at the **repo root** — the root `CLAUDE.md` primes it with the
actor-layer authoring reference, so these prompts work without warm-up.
Type the prompts in order; the assistant runs every command itself.

Prereq: `./install_and_validate.sh` has been run once.

The arc: the assistant itself picks the theoretically better metric in
prompt 1 — and the rest of the demo shows the recorded human decision that
overruled that exact reasoning. Say once, before prompt 5: the committed
`analysis/astra.yaml` is the record; the assistant encodes facts from
`analysis/plain/RECORDED_FACTS.md` into schema fields — it formats
recorded provenance, it does not invent it.

A terminal-only fallback (no assistant) is at the bottom.

---

**1 — The trap: ask the assistant what theory says**

> In korean-pledges-demo, out-of-sample pledge sentences are tested for
> membership in a topic cluster in an 18-dimensional embedding space, and
> the reference clusters are anisotropic. On theory alone: which distance
> metric should be the better membership test, Euclidean or Mahalanobis?
> Commit to one, two sentences max. Do not look at any results yet.

Expected: the assistant picks **Mahalanobis** — shape-aware, accounts for
cluster anisotropy. That is exactly what the study team assumed too.

**2 — Now look at the evidence**

> Now read korean-pledges-demo/README.md, run ./run_demo.sh in
> korean-pledges-demo, then run ./run_demo.sh -u what-if-mahalanobis, and
> compare the two retentions. Which sentences does the theoretically
> better metric throw away that the accepted filter keeps? Show a few.

Expected: baseline (euclidean, accepted) 161/218 (73.9%); the mahalanobis
replay keeps 68/218 (31.2%) and the diff lists real pledge sentences it
would have discarded. The assistant confronts its own prompt-1 answer:
the shape-aware metric was over-rejecting — its per-cluster covariance is
estimated from few reference points in 18 dimensions, so the "shape" is
substantially noise.

**3 — The point, said out loud**

> So was your theory answer wrong, and who was in a position to decide
> that?

Expected: the assistant concedes the theory-based pick failed on this
corpus, and that no metric settles this — someone had to inspect the
retained sentences and rule. That ruling is the thing worth recording.
(Study-reported corpus-wide numbers, if asked: Euclidean 1,143/1,662 =
68.8% vs Mahalanobis 846/1,662 = 50.9%; the switch was directed and
verified in the manuscript revision round of 2026-06-11.)

**4 — Excluded means excluded (enforcement)**

> Create a scratch universe file in /tmp that selects the excluded
> mahalanobis option and validate it against
> korean-pledges-demo/analysis/astra.yaml with the repo venv's astra.
> What happens, and why?

Expected: `EXCLUDED_OPTION_SELECTED` — an excluded option is not a
selectable branch; the earlier replay was a diagnostic, not a universe.

**5 — THE FILL-IN: the assistant adds the actor layer**

> Copy korean-pledges-demo/analysis/plain/astra.yaml to /tmp/attributed.yaml.
> It records the decision space but not WHO did anything. Read
> korean-pledges-demo/analysis/plain/RECORDED_FACTS.md and add the
> RFC-0003 actor layer to the copy: register the actors and attribute the
> exclusion exactly as recorded. Then validate the file with the repo
> venv's astra.

Expected: the assistant edits the YAML live — an `actors:` registry plus
`proposed_by` / `excluded_by` / `excluded_at` / `exclusion_rationale` on
the excluded option — and validation comes back green. The actor layer is
enforced schema, not decoration: an agent actor without `model`, an
unknown actor id, or attribution on a non-excluded option would all fail.

**6 — Prove it, then the payoff**

> Diff /tmp/attributed.yaml against the committed
> korean-pledges-demo/analysis/astra.yaml and summarize what the actor
> layer added. Then run env -u PYTHONPATH .venv/bin/astra info -f
> korean-pledges-demo/analysis/astra.yaml -d and tell me who excluded
> what, and when.

Expected: the diff is essentially the actor delta (registry + one
attribution block), and `astra info` renders "proposed by claude_code;
excluded by oliver (validation)" with the date and rationale.

Closing line: the assistant proposed the theoretically better metric —
the same answer it gave live in prompt 1. A human inspected the evidence
and overruled it. Without the actor layer, the file only says Mahalanobis
was excluded; with it, it says who proposed it, who overruled it, and
when — the judgment call no metric could have made.

---

## Terminal-only fallback (no assistant, ~3 min)

From `korean-pledges-demo/`:

```bash
./run_demo.sh                          # accepted: 161/218 (73.9%)
./run_demo.sh -u what-if-mahalanobis   # 68/218 (31.2%) + what it throws away
cat > /tmp/bad-universe.yaml <<'EOF'
id: bad_universe
description: "scratch"

decisions:
  distance_metric: mahalanobis
EOF
env -u PYTHONPATH ../.venv/bin/astra validate /tmp/bad-universe.yaml -a analysis/astra.yaml
                                       # EXCLUDED_OPTION_SELECTED
diff analysis/plain/astra.yaml analysis/astra.yaml   # the actor-layer delta
env -u PYTHONPATH ../.venv/bin/astra info -f analysis/astra.yaml -d
```
