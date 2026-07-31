# Working notes — out-of-sample filter, distance measure

Informal notes kept while choosing the filter. Not a decision record;
this is the raw material one would be written from.

## Who worked on this

- **Oliver** — the researcher on the project. Human.
- **The assistant** — Claude Opus, model id `claude-opus-4-8`, running in
  the Claude Code harness, working sessions dated May 2026. An agent.

## How the choice went

**May 2026.** Starting the filter, the assistant proposed Mahalanobis
distance and I agreed. The argument was the textbook one: the topics are
stretched rather than round in the 18-d space, and Mahalanobis accounts
for that stretch while Euclidean does not. It was the methodologically
obvious pick, so we built the first pass on it and treated Euclidean as
the baseline we would beat.

**What went wrong.** The retention was too low to believe. Across the
full corpus Mahalanobis kept 846 of 1,662 sentences (50.9%); Euclidean
kept 1,143 (68.8%). On the Climate Adaptation topic Mahalanobis kept 0 of
2. The problem is that each topic's shape has to be estimated from the
handful of reference sentences in that topic, in 18 dimensions — so the
shape it was adapting to was mostly noise, and it threw away good
sentences as if they were far away.

**2026-06-11.** During the manuscript revision round I went through the
sentences each measure kept and dropped. Euclidean's set was clearly
better on reading. I ruled Mahalanobis out that day and we switched the
manuscript to Euclidean, checking the replacement numbers sentence by
sentence before they went in.

So: the assistant proposed the option, and I was the one who ruled it out
after looking at the results — that is the part I would want on the
record, along with the date.

## Things that did not change

- Cut-off: 99th percentile of the reference corpus's leave-one-out
  distances (alpha = 0.01).
- Distances measured from the pledge set's own centre, with the reference
  topic supplying shape and cut-off.

Both were settled earlier and were not revisited, so they are constants
here, not open choices.
