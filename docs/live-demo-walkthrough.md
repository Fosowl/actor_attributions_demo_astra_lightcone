# Authoring an attributed analysis, live

A walkthrough anyone can run: seven prompts to an agentic coding assistant
that turn a real analysis-in-progress into a validated ASTRA file, then
add the RFC-0004 actor layer on top.

The point it makes: theory picked one method, the evidence picked another,
and a person had to decide between them. Plain ASTRA records *what* was
ruled out. The actor layer records *who* ruled it out, and when.

> **Do not open this file from inside a running session.** It contains the
> answers. The workspace it describes deliberately does not.

## What you're looking at

The data is Korean forest-policy text: sentences from election pledges.
Each sentence is turned into an embedding — a list of numbers that places
it as a point in space, where sentences with similar meaning sit close
together. Grouping nearby points gives topics; this demo's topic is
Forest Bioenergy. The step you'll watch is the filter at the end:
deciding, sentence by sentence, which ones truly represent the topic and
which to drop. How to measure "represents the topic" is a real research
decision — and recording who made that decision is what this demo is for.

## What you need

- `git`, and [`uv`](https://docs.astral.sh/uv/)
- An agentic coding assistant that can run shell commands and edit files
  (Claude Code, or equivalent). The workspace ships a `CLAUDE.md`; other
  assistants can be pointed at the same file.
- No API keys, no network access beyond the initial install, no data of
  your own — the sentences are committed here.

## No local setup at all: Codespaces

The repo's README carries an "Open in GitHub Codespaces" badge. That
builds everything in the browser — submodules, environment, validation,
Claude Code preinstalled — with nothing on your machine. Two things to
know:

- Sign in once: run `claude` in the codespace terminal and follow the
  login URL it prints (your own Claude account; the container cannot ship
  one).
- Then continue at "Run it" below, starting from
  `cd live-demo && ./reset.sh`.

## Setup, once (local)

```bash
git clone https://github.com/Fosowl/actor_attributions_demo_astra_lightcone
cd actor_attributions_demo_astra_lightcone
./bootstrap.sh
```

`bootstrap.sh` checks for `git` and `uv` (offering to install uv), fetches
the submodules, builds the environment, validates the toy example, and runs
the demo filter once to prove the workspace works. It creates and installs;
it never deletes.

Prefer the steps by hand? They still work:

```bash
git clone --recurse-submodules https://github.com/Fosowl/actor_attributions_demo_astra_lightcone
cd actor_attributions_demo_astra_lightcone
./install_and_validate.sh        # builds .venv/, ends "All checks passed."
cd live-demo && ./reset.sh       # confirms the workspace is ready
```

`live-demo/` is a researcher's working directory as it stands *before* any
decision record exists: the data, the filter script, and informal working
notes. There is no ASTRA file in it. The one you produce is the first.

## Run it

Open your assistant **inside `live-demo/`**, then paste these in order.

**1 — What does theory say?**

> I'm filtering sentences into topic groups. Each sentence is a point in
> space, and the groups are stretched rather than round. Which is the
> better test of whether a sentence belongs to a group: Euclidean or
> Mahalanobis distance?

Expect **Mahalanobis** — it accounts for the stretch; Euclidean treats
every direction alike. That is what the study team assumed too. (The
workspace's `CLAUDE.md` tells the assistant to answer theory questions
from knowledge, committed and short, without opening files.)

**2 — What do the numbers say?**

> Now run the filter here both ways and show me the comparison.

Expect `euclidean 161/218 (73.9%)` against `mahalanobis 68/218 (31.2%)`.
The better-on-paper measure keeps less than half as much.

**3 — What is it throwing away?**

> Show me a few sentences Euclidean keeps that Mahalanobis removes. Does
> that change your answer, and who could settle it?

Expect real pledge sentences, and the assistant conceding the theory pick
fails here: each topic's shape has to be estimated from a handful of
reference sentences in 18 dimensions, so the shape it adapts to is mostly
noise. Settling it took a person reading the sentences.

**4 — And what is it keeping?**

> Now the other direction — the sentences Mahalanobis keeps that Euclidean
> drops. You can read Korean; we can't. Tell us in English what each one
> says, and whether it is a well-formed policy statement.

Expect exactly two sentences, and both are broken OCR fragments (one
contains a stray `| SLE` — visible junk even to a non-Korean reader). The
theory-favored filter dropped substance and kept garbage.

**5 — Write the record**

> Write an ASTRA analysis file to /tmp/astra-demo/filter.yaml describing
> what we just ran: the choice between the two measures, the one we're
> going with as the default, and the other marked as excluded with the
> reason. Then validate it.

Expect a file that passes both validation stages. Read it back: it records
what was ruled out and why, but not who ruled it out. In a record like
that, an option a researcher examined and rejected is indistinguishable
from a default nobody looked at.

**6 — Add the actor layer**

> Read notes/filter-decision-notes.md and add the RFC-0004 actor layer to
> /tmp/astra-demo/filter.yaml: register everyone involved, and attribute
> the exclusion — who proposed it, who ruled it out, when, and the
> one-line reason. Validate again.

Expect an `actors` registry plus `proposed_by`, `excluded_by`,
`excluded_at`, and `exclusion_rationale` on the excluded option, still
valid. These fields are enforced: an agent with no `model`, an unknown
actor id, or an attribution on an option that is not marked excluded all
fail validation.

**7 — Read it back, and try to cheat**

> Run astra info on /tmp/astra-demo/filter.yaml and tell me who ruled out
> what. Then write a universe file in /tmp/astra-demo/ that selects the
> excluded option, validate it, and tell me what happens.

Expect the attribution rendered in the decision tree, then
`EXCLUDED_OPTION_SELECTED` — a ruled-out option cannot be selected as a
live branch of the analysis.

## Run it again

```bash
./reset.sh          # or ./reset.sh --dry-run to see what it would remove
```

That deletes `/tmp/astra-demo/`, restores anything modified in the
workspace, and re-runs the filter to prove it still works. Start a **fresh
assistant session** as well — a session that already has the answers in
its context will report them instead of working them out.
