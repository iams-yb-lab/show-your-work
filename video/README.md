# The video tree

Everything the three skills dereference lives here. The skills are in
[`../.claude/skills/`](../.claude/skills/) and their relative links point into this tree, so
**this directory must sit one level below the repository root** — that is the whole contract.

## Layout

```
engine/         the shared audio: dsp, mix_audio, voice_chain, narrate, check_score
picture/        the HTML-bundle-to-video exporter
natural-voice/  the audio-first natural-speech method, its profiles and experiments
showoff/
  assembly/     the Blender + KiCad pipeline, and the film's logs
education/
  intro/        the first explainer's script and audio pipeline
  how-to-make-an-explainer/  the film made with `education-video`, and its tools
out/            gitignored. Frames, takes and mixes go here and never into git.
```

[`natural-voice/`](natural-voice/) is the shared method rather than a film: why the approved warm
narrator sounds natural, the procedure for transferring that to a new voice, the profile contract,
and the failed effects that must not silently return. `natural-voice/SKILL.md` links straight into
it, so it is load-bearing.

`engine/` holds the BS.1770-4 loudness meter, the true-peak limiter, the van Herk sliding maximum,
the voice chain and the pitch set. Every film imports it and none of them owns it: a second copy of
a loudness meter is a second answer to the same question.

## What is here, and what is not

Everything the two finished films need to be rebuilt is here: their documents, scripts, logs,
tooling, and the picture files that cannot be regenerated — the two Claude Design bundles above all,
which are an **input** to the render, not an output of it. Only `out/` stayed behind: 5.1 GB of
frames, takes and mixes, gitignored and regenerable.

Each film's **log** is the part that matters most — `RENDER-LOG.md`, `VOICE-LOG.md`, `AUDIO-LOG.md`,
`EXPERIMENTS.md`. Every rule in the three skills was paid for by something in those files, and a
rule whose evidence has been left behind is just an assertion.

**A new film does not belong here.** Its document, script, takes and picture belong to the project
using the skill; `education-video`'s interview stage says so and it applies to this directory. The
two that are here are the worked examples the skills were written from.

This tree travels as a unit and links only within itself and into `../.claude/skills/`. Nothing
here may point at a file in the repository root, because the root does not come along.

## Paths, for anything written here in future

**Do not anchor on the checkout.** Walk up from the file until you find the directory holding
`engine/` and `natural-voice/` — that *is* the video tree, by definition — and take every path from
there:

```python
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "video" / "natural-voice").is_dir())
```

Code written that way does not care which repository it has been lifted into, or which machine it
is on. The hardcoded checkout path this rule replaced is why a batch of scripts could not run on
the project's second machine, and `tools/check_links.py` now fails on any absolute path naming
another checkout.

## Frozen records

`showoff/assembly/audio/pipeline/` and `showoff/assembly/audio/natural-v8/` are the experiment
record behind the rejected-attempts table in `natural-voice/SKILL.md`. Their repository anchors
were repaired on the way in, but their inputs were takes under `out/` that did not travel. **Read
them; do not expect them to run.** The same goes for the two `narration-assembly*.md` scripts,
whose traces cite a board that lives in another repository.

## What is not checked

How any of it sounds. Sync, loudness, balance and pronunciation-by-duration are measured; taste is
not, and there is no instrument here for it. Agree the voice before rendering the whole thing.
