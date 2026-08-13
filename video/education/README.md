# Education films

Explainers. Two.

| | what it is | run time |
|---|---|---|
| [`intro/`](intro/) | the explainer for this project's instrument | 5:38 |
| [`how-to-make-an-explainer/`](how-to-make-an-explainer/) | how to point Claude at your own work and get one of these | 5:30, picture pending |

## Why this is a bucket and not the film

One directory named for a genre cannot hold two films — they would collide in `script/`, `audio/`
and `picture/`. So the genre is the directory and each film gets a subdirectory of its own, even
while there is only one. What becomes of a film when `video/` is lifted out is in
[`../README.md`](../README.md) and is not restated here: that answer has already changed once.

An earlier generic film — how to explain your own work — was built here on 2026-08-13 and
**deliberately deleted** so the `education-video` skill could be retested from a clean start. That
retest is `how-to-make-an-explainer/`, run end to end from GATE 0 with nothing inherited. The deleted
one is recoverable from git history; what was learned from both is in the skill.

Films here share the audio engine and the voice method. Neither is owned by a film: a second copy of
a loudness meter is a second answer to the same question.

## What is not checked

How either one sounds. Sync, loudness, balance and pronunciation-by-duration get measured; taste
does not, and this repo has no instrument for it. Agree the voice before rendering anything long —
[`../showoff/assembly/audio/AUDIO-LOG.md`](../showoff/assembly/audio/AUDIO-LOG.md) is what skipping that cost.
