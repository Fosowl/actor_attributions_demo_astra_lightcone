# ASTRA Actor Attribution — Demo

*Who proposed this option? Who ruled it out? Who signed off?*

[ASTRA](https://astra-spec.org) records the decision structure of a scientific
analysis — which options were considered, chosen, or excluded, and why — but
not **who** was involved. In today's records, a choice a researcher examined
and rejected is indistinguishable from a default nobody looked at. That
distinction is exactly what accountability, credit, and oversight of
AI-assisted science need.

## Where this comes from

This work grew out of [TRACE](https://github.com/Thru-Echoes/TRACE), an
open project by [Thru-Echoes](https://github.com/Thru-Echoes) that actively
records the decisions of an AI-assisted science workflow *as they happen* —
who proposed each choice, who accepted or overruled it, and when. ASTRA
describes an analysis's decision space but had no place to put that "who".
This demo adds some of TRACE's capability to the ASTRA spec: a small,
optional, fully additive **actor layer** (RFC-0004) — a registry of the
humans and agents on an analysis, plus attribution fields on the two places
a "who" is meaningful: the *options* of a decision and the *selections* of
a universe.

## Guided tour (no setup)

[`docs/demo-day-walkthrough.html`](docs/demo-day-walkthrough.html) is a
self-contained interactive page that walks the whole story — the layer,
the trap, the evidence plots, enforcement, and the payoff — with every
number and error message a captured output of the committed pipeline.
[Open it rendered](https://raw.githack.com/Fosowl/actor_attributions_demo_astra_lightcone/main/docs/demo-day-walkthrough.html),
or open the file locally after cloning.

## The layer at a glance

![Actor attribution overview](assets/actor_attribution.svg)

```yaml
actors:                                # declare each actor once, refer by key
  jane:
    type: human
    identifiers: {orcid: "0009-0000-0000-0000"}   # or arxiv / openalex / wikidata / scholar
  assistant:
    type: agent
    model: claude-opus-5
    harness: claude-code

decisions:
  outlier_handling:
    options:
      drop_iqr:
        excluded: true                                  # existing ASTRA fields
        excluded_reason: Real variation, not error.
        proposed_by: {actor: assistant, role: methodology}   # NEW
        excluded_by: {actor: jane, role: validation}         # NEW
```

Universe selections attribute the same way — `selected_by` / `reviewed_by` on
a choice, while the plain `decision: option` shorthand stays valid. Every
attribution is a bare actor id or `{actor, role}`, with roles drawn from a
CRediT-derived vocabulary keyed to the actor's type (`conceptualization` and
`supervision` are human-only).

![Attribution flow](assets/attribution_flow.gif)

And the layer is enforced, not decorative — validation catches:

```
• 'excluded_by' references unknown actor 'bob' (actors in scope: assistant, jane)
• 'proposed_by' assigns role 'conceptualization' to agent 'assistant' — human-only
• option has 'excluded_by' but is not marked excluded
• human actor 'jane' declares agent-only field(s): model
• 'identifiers' record present but empty — at least one id required
```

## The real one: Korean pledges, live

The toy above shows the syntax. This shows the purpose, on a real study.

The data is Korean forest-policy text: sentences from election pledges.
Each sentence is turned into an embedding — a list of numbers that places
it as a point in space, where sentences with similar meaning sit close
together. Grouping nearby points gives topics; this demo's topic is Forest
Bioenergy. The step you'll watch is the filter at the end: deciding,
sentence by sentence, which ones truly represent the topic and which to
drop. How to measure "represents the topic" is a real research decision —
and recording who made that decision is what this demo is for.

![The distance_metric decision, attributed](assets/korean_pledges_decision.svg)

The demo runs live in an agentic coding session opened inside
[`live-demo/`](live-demo/) — a researcher's working directory as it stood
*before* any decision record existed. Setup, then the prompts, pasted one
at a time:

```bash
cd live-demo && ./reset.sh     # clean start; then open the assistant here
```

**1 — What does theory say?**

> I'm filtering sentences into topic groups. Each sentence is a point in
> space, and the groups are stretched rather than round. Which is the
> better test of whether a sentence belongs to a group: Euclidean or
> Mahalanobis distance?

Expect: **Mahalanobis** — the textbook answer, and what the study team
assumed too.

**2 — What do the numbers say?**

> Now run the filter here both ways and show me the comparison.

Expect: `euclidean 161/218 (73.9%)` against `mahalanobis 68/218 (31.2%)`.
The better-on-paper measure keeps less than half as much.

**3 — What is it throwing away?**

> Show me a few sentences Euclidean keeps that Mahalanobis removes. Does
> that change your answer, and who could settle it?

Expect: real pledge sentences on screen, and the assistant conceding that
each topic's shape is estimated from a handful of examples — so the shape
the theory pick adapts to is mostly noise.

**4 — And what is it keeping?**

> Now the other direction — the sentences Mahalanobis keeps that Euclidean
> drops. You can read Korean; we can't. Tell us in English what each one
> says, and whether it is a well-formed policy statement.

Expect: there are exactly two, and both are broken OCR fragments (one has
a stray `| SLE` in the middle — visible junk even without Korean). The
theory-favored filter was dropping substance *and* keeping garbage.

**5 — Write the record**

> Write an ASTRA analysis file to /tmp/astra-demo/filter.yaml describing
> what we just ran: the choice between the two measures, the one we're
> going with as the default, and the other marked as excluded with the
> reason. Then validate it.

Expect: a valid file, written live — but it does not say *who* ruled the
option out.

**6 — Add the actor layer**

> Read notes/filter-decision-notes.md and add the RFC-0004 actor layer to
> /tmp/astra-demo/filter.yaml: register everyone involved, and attribute
> the exclusion — who proposed it, who ruled it out, when, and the
> one-line reason. Validate again.

Expect: an `actors` registry plus `proposed_by` / `excluded_by` /
`excluded_at` / `exclusion_rationale`, still valid.

**7 — Read it back, and try to cheat**

> Run astra info on /tmp/astra-demo/filter.yaml and tell me who ruled out
> what. Then write a universe file in /tmp/astra-demo/ that selects the
> excluded option, validate it, and tell me what happens.

Expect: *"proposed by the assistant (methodology); excluded by oliver
(validation)"* with the date — then `EXCLUDED_OPTION_SELECTED`: a
ruled-out option cannot come back as a live branch.

The finished, attributed record for this study lives in
[`korean-pledges-demo/`](korean-pledges-demo/), with tests pinning every
quoted number to a live computation. Full walkthrough with expected
output: [`docs/live-demo-walkthrough.md`](docs/live-demo-walkthrough.md).

## Try it on your own!

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Fosowl/actor_attributions_demo_astra_lightcone?quickstart=1)

The badge builds everything in your browser — submodules, environment,
validation, Claude Code preinstalled (you sign in with your own account).
When setup finishes, `cd live-demo && ./reset.sh` and paste the prompts
above. Or locally:

```bash
git clone https://github.com/Fosowl/actor_attributions_demo_astra_lightcone
cd actor_attributions_demo_astra_lightcone
./bootstrap.sh        # or the manual steps: see docs/live-demo-walkthrough.md
```

## Repo map

| Path | What it is |
|---|---|
| [`astra-spec/`](https://github.com/Fosowl/astra-spec) | Fork submodule — the schema: `actor.yaml` LinkML module, RFC-0004 draft (`rfcs/0004-actor-attribution.md`) |
| [`astra-tools/`](https://github.com/Fosowl/astra-tools) | Fork submodule — the tooling: semantic enforcement, CLI display, attributed `examples/iris` |
| [`live-demo/`](live-demo/) | The pre-record working directory the prompts above run in |
| [`korean-pledges-demo/`](korean-pledges-demo/) | The finished, attributed real-data example with its tests and figures |
| [`bootstrap.sh`](bootstrap.sh) / [`install_and_validate.sh`](install_and_validate.sh) | One-command and manual setup |
| [`UPSTREAMING.md`](UPSTREAMING.md) | What goes upstream vs. fork-only wiring, PR strategy |

## Design in three sentences

The **schema** owns the vocabulary (`Actor`, `Attribution`, the role enums)
and the **astra-tools semantic layer** owns everything conditional or
cross-referential — the same split ASTRA already uses. Universe files stay
backward compatible via an explicit `union(string, DecisionSelection)`, so
every existing `astra.yaml` and universe remains valid, byte for byte. What
happened stays in the record; *who made it happen* is now recoverable.
