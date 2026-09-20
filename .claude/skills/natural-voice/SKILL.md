---
name: natural-voice
description: Load whenever generated or synthetic speech is involved in a task — TTS, narration, voice-over, voice cloning, dubbing, or mixing, evaluating or editing any of them. Applies to every film and every future voice. Read before generating a single line.
---

# Natural voice — process notes

**The method is [`method/README.md`](method/README.md). Read it in full before generating any
speech, and follow it.** [`method/EXPERIMENTS.md`](method/EXPERIMENTS.md) records what has been
tried and rejected, so it is not tried again. This file is the short form: the finding, the rules
that follow from it, and the shape of a voice job.

## The finding

Acoustic realism has to be present in the performance the engine produces. Nothing added afterwards
has supplied it in any test in this repository: room simulation, reflections, compression,
saturation, pitch drift and synthetic breaths were each tried and each made the voice sound less
human. The one approach that was accepted adds no realism downstream at all: a plausible voice, whole
paragraphs generated as one performance, endings and breaths kept, and at most a restrained EQ.

## What was tried and rejected

Kept as a table so it is not repeated. Full detail is in the method's experiments file and in each
film's audio log.

| treatment | why it was rejected |
|---|---|
| synthesised score with per-event sound effects placed from the animation's schedule | the effects sounded artificial |
| a cloud TTS narrator used as delivered | sounded synthetic |
| the same voice with de-essing, chest and presence EQ, compression, saturation, pitch drift, a stereo room impulse and synthesised breaths | sounded more artificial than without |
| rewriting the script while keeping the voice | the objection was to the voice, not the words |
| a local model's built-in voice with no processing | natural, but the wrong voice for the film (median pitch 118 Hz) |
| cloning a model onto a pitch-shifted copy of itself | pitch wandered 15 Hz from line to line; read as a different person per line |
| a different local model with a deep built-in voice | too clean and metronomic |
| a 3B model chosen by leaderboard score, with model-generated breaths | band-limited; sounded like a noise-cancelling microphone |
| six full renders in one batch, offered for the user to pick from | the narrator changed character between lines inside one film |
| eight fresh takes of one hurried line, selected per line | word-perfect, none fitted the duration; per-line selection breaks narrator coherence |
| room tone, early reflections at 17/29/43 ms and soft-knee compression on the approved cut | sounded like a robot with echoes |
| slowing the conditioning prompt to move an unhurried pace upstream | pace did not transfer; pitch spread widened |
| cloning a prompt the listener had just approved, with a larger model | every clone sounded worse than the raw prompt |
| loudness-matching audition files by static gain with no peak check, then AAC-encoding them | every delivered file clipped; the comparison was invalid |

Two general lessons from that table. A measurement passing is not the job finished: files that were
word-perfect, loudness-correct and in sync were still rejected by ear. And the file handed to a
listener must itself be measured, not only its inputs.

## Rules that follow

- **Audio first, picture second.** The audio is the timing authority. A caption marks speech that
  already exists. If a picture already exists, say so and expect editing artefacts.
- **Audition the raw prompt before generating anything.** It must already sound like a plausible
  close recording. Then audition the engine speaking the real script: a prompt that passes proves
  nothing about what an engine conditioned on it produces.
- **Generate paragraphs, not caption lines.** Phrasing, pauses and sentence releases happen inside
  one performance.
- **Never trim on a silence threshold or at last-word plus 100 ms.** Lexical timing is not acoustic
  timing. Keep releases, breaths and decays.
- **One model, one prompt, one register for the whole project**, per language. Vary seeds, not the
  narrator's identity. A second language is a second voice chosen the same way.
- **No denoiser, noise gate, exciter, synthetic breath, pitch drift, saturation, room impulse or
  echo taps by default.** Compression only against a measured dynamic-range problem, with a
  loudness-matched bypass comparison.
- **Loudness-match before any comparison**, downward: the common level is the loudest at which every
  file keeps at least 1 dB of true-peak headroom. Static gain only; no limiter.
- **Measure the true peak and loudness of every file you hand over, after you make it.**
- **Deliver lossless.** Never introduce a lossy encode into a comparison or a master.
- **Change one thing at a time, from the setting that was chosen.** Do not open a wide sweep once a
  voice is picked; a sweep changes the identity you are trying to hold still.
- **Agree the approach before rendering.** Do not present a matrix of candidates for the user to
  sort; that hands them a defect you should have caught.
- **A measurement does not overrule what the listener hears.**
- **Record every rejected treatment and the reason** in the film's audio log, named, so another
  session does not rediscover it.

## How a voice job runs

1. **Settle whose voice it is**, in plain prose: which language, male or female, and the register
   in ordinary words. Offer an existing profile first, by name, with its measurements. A voice with
   no proven profile means the full prompt-selection procedure in the method, not a switch.
2. **Hand over five short samples**: real lines from the real script, one file each, loudness-matched,
   absolute paths. Five readings to pick from, not a grid of voices.
3. **The user picks one. That is the voice**, and everything in that language renders in it.
4. **Render the whole thing, one take per section.** A second take is generated only for a section
   that fails a check. Takes are not voices; say so.
5. **Verify mechanically**: words against the script, true peak, loudness, sample rate, lossless
   container. Name what you are unsure of.
6. **The user listens to every file, start to end**, and names the broken ones. Hand over the
   complete list of paths in script order.
7. **Regenerate exactly the ones they name**, verify those, hand them back. Do not re-render the
   rest; do not re-pick the voice.

When the words cannot be settled from a transcript ("in order" against "an order" is the same
sound), keep the take, say what to listen for, and let the listener decide.

## Before handing over anything to be listened to

1. True peak of each delivered file at or below −1 dBFS. If anything reads positive, it clipped;
   throw the comparison away.
2. Integrated loudness of each delivered file, confirming the set matches.
3. Lossless container and one sample rate across the set.
4. Say what each file is: which are inputs, which are outputs, which speak different words.
5. Give the absolute path of every file, one per line.

Then say what you are unsure of, and what a given judgement would and would not settle. If a
comparison has more than one variable, say so before the listening, not after.

## Reusing a voice

A chosen voice is a reusable profile under [`profiles/`](profiles/) — for example
[`profiles/warm-natural/`](profiles/warm-natural/) and `profiles/af-heart-normal/`, the lab's
female explainer voice: prompt file and hash where
there is one, selection record, generation ranges, reproduction script, README. Never overwrite a
profile; a changed prompt, model or conditioning is a new profile version. Never normalise, denoise,
noise-gate, resample or lossy-encode a stored prompt. EQ curves are profile-specific; do not copy one
voice's curve onto another. For a new voice, follow the profile contract and prompt-selection
procedure in the method.
