# Internal — how the target is proved, and what the evidence is

**None of this is narrated.** It lives outside [`SOURCE.md`](SOURCE.md) on purpose: the viewer came
for a clear, accurate video, not for our quality system. Kept because a target with no test is an
opinion, and because the film's claims have to rest on something.

Numbers by key from [`NUMBERS.md`](NUMBERS.md).

## The pass rule behind goal 3

The film states three goals as outcomes. The third — *nothing in it sounds wrong* — is checked like
this, silently:

1. **No line was re-recorded, trimmed or spliced in order to fit a picture.**
2. **Every scene boundary in the delivered picture matches the audio-derived scene table** to within
   `TOL.boundary`.
3. **The scene durations sum to the delivered file's real duration** to within `TOL.total`.

The reference film in this repo **passes part 3 and fails part 1**. Part 3 is measured: its scene
table and its delivered file agree to `REF.table_vs_file`. Part 1 is recorded — its narration was
fitted to a picture that already existed, and it still carries imperfect sentence joins.

**So a film can be correct to the millisecond and still audibly wrong.** That is precisely why goal 3
is written as something a person hears rather than something a tool reports, and why a human listening
is a stage and not a courtesy.

## Every check names one artifact

A limit belonging to a delivered file, applied to a raw take, manufactures a failure. So does a
writing guideline applied to a recording. The log records four checks on the trial film aimed at the
wrong artifact, each of which produced a red result on work that was fine, and nearly had it thrown
away. Before believing any red result, check what it was written about.

## What breaking the order cost, in this repo

Same columns, both films, at the same point in their lives — delivered:

| | reference explainer | trial explainer |
|---|---|---|
| order used | picture first, narration fitted to it | document → script → audio → picture |
| scenes | `REF.scenes` | not recorded |
| lines of narration | `REF.cues` | `TRIAL.cues` |
| words | `REF.words` | `TRIAL.words` |
| runtime | `REF.duration`, measured | `TRIAL.duration`, recorded |
| words per minute over the whole film | `REF.wpm`, measured | `TRIAL.wpm`, from a recorded runtime |
| where its timecodes came from | written against a finished picture | measured off the frozen sound |
| timing artifacts it still carries | imperfect sentence joins, recorded | none recorded |

**Reasoned, not measured:** the gap between the two rates is mostly silence rather than delivery
speed, because the reference film's slots were sized to a picture that already existed. That is an
explanation, not evidence.

## What Claude holds the document to

The film says only that Claude presses on what is measured and refuses a repeated fact. The actual bar,
which the viewer never meets:

- **Evidence status before any claim** — built, measured, modelled, or merely planned. Without it every
  figure reads as measured.
- **Every fact exactly once.** Two copies eventually disagree, and the film then picks one at random.
- **Mechanism as a chain of causes, not a claim.** *"The design handles it"* cannot be animated; *this
  pushes, so that moves, so the two cancel* can, because every step is something a picture can perform.
- **Typicals, estimates and assumptions labelled inline**, a scope section, and a verdict with reasons.

## What Claude holds the script to

Also invisible to the viewer, who is told only that no line has to be hurried:

- **Slot length tracks word count, not a grid.** On the reference film the range is `REF.slot_min` to
  `REF.slot_max`, and the longest slots are its densest technical lines.
- **A gap of about `REF.hole_min` at the top of every scene**, so a cut can land without the narrator
  talking over it.
- **One trace per claim, and rounding as the only permitted transform.**

## Traceability, on the reference film

`REF.traced` of `REF.cues` lines trace to a line of its source report. The ones that fail are its
softest claims — one invents a comparison the report never makes. That drift happened *with* a process
in place, which is why a trace is written down per line rather than trusted.
