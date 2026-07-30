# Live-demo script (chat-first)

Six short prompts for an agentic coding assistant (e.g. Claude Code)
opened at the **repo root**. The root `CLAUDE.md` primes it with the
actor-layer rules and the right commands, so the prompts can stay short —
the assistant runs everything itself.

Prereq: `./install_and_validate.sh` has been run once.

The arc: the assistant picks the method that is better on paper in prompt
1, and the rest of the demo shows the recorded human decision that
overturned exactly that reasoning. Before prompt 5, say once: the
committed `analysis/astra.yaml` is the record; the assistant is putting
recorded facts from `analysis/plain/RECORDED_FACTS.md` into the right
fields, not inventing them.

A terminal-only fallback is at the bottom.

---

**1 — The trap**

> Sentences are points in space, and the topic groups they belong to are
> stretched, not round. Which distance measure should be the better test
> of whether a point belongs to a group: Euclidean or Mahalanobis? Answer
> from theory only, one sentence.

Expect: **Mahalanobis** — it accounts for each group's stretched shape,
Euclidean treats every direction alike. That is what the study team
assumed too.

**2 — The evidence**

> In korean-pledges-demo, run ./run_demo.sh, then run it again with
> -u what-if-mahalanobis. Compare the two, and show me a few sentences
> Mahalanobis throws away.

Expect: the accepted filter keeps 161/218 (73.9%); Mahalanobis keeps
68/218 (31.2%), and real discarded pledge sentences appear on screen. The
better-on-paper method was throwing away more than half the good
material: it measures each group's shape from only a handful of examples,
so the shape it adapts to is mostly noise.

**3 — The point, said out loud**

> So was your theory answer wrong, and who could have decided that?

Expect: the assistant concedes the theory pick failed on this data, and
that settling it took a person reading the sentences. That judgment is
what is worth recording. (Full-dataset numbers if asked: Euclidean kept
1,143 of 1,662 sentences, 68.8%; Mahalanobis 846, 50.9%. The switch was
made and checked during the manuscript revision of 2026-06-11.)

**4 — Excluded means excluded**

> Write a universe file in /tmp that picks the excluded mahalanobis
> option, validate it against korean-pledges-demo/analysis/astra.yaml,
> and tell me what happens.

Expect: `EXCLUDED_OPTION_SELECTED` — a ruled-out option cannot come back
as a real choice. The earlier run was a replay for inspection only.

**5 — The fill-in: the assistant adds the actor layer**

> Copy korean-pledges-demo/analysis/plain/astra.yaml to
> /tmp/attributed.yaml — it says what was decided but not who decided it.
> Add the actor layer using the facts in RECORDED_FACTS.md beside it,
> then validate it.

Expect: the assistant edits the file live — an `actors` registry plus
`proposed_by` / `excluded_by` / `excluded_at` / `exclusion_rationale` on
the ruled-out option — and validation passes. These fields are checked,
not decorative: an agent with no model named, an unknown person, or a
"who excluded it" on an option that was not excluded all fail.

**6 — The payoff**

> Diff your file against the committed
> korean-pledges-demo/analysis/astra.yaml, then run astra info on that
> one and tell me who excluded what, and when.

Expect: the diff is just the actor layer; `astra info` shows "proposed by
claude_code; excluded by oliver (validation)" with the date and reason.

Closing line: the assistant proposed the method that is better on paper —
the same answer it gave live in prompt 1. A person looked at the results
and overruled it. Without this layer the file only says Mahalanobis was
ruled out; with it, the file says who proposed it, who overruled it, and
when.

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
diff analysis/plain/astra.yaml analysis/astra.yaml   # the actor layer, side by side
env -u PYTHONPATH ../.venv/bin/astra info -f analysis/astra.yaml -d
```
