---
name: natural-voice
description: Load automatically whenever generated or synthetic speech is involved in any task — TTS, narration, voice-over, voice cloning, dubbing, or mixing/evaluating/editing any of them. Applies to every film and every future voice, not just this project's. Read before generating a single line.
---

# Natural voice

**The method is [`natural-voice/method/README.md`](method/README.md). Read it
in full and follow it exactly.**

That document was written by Codex after everything this repository tried had been rejected, and it is
the only voice approach here that has ever been accepted. **Do not reword it, summarise it back into
your own phrasing, "improve" it, or substitute your judgement for it.** Its companion
[`EXPERIMENTS.md`](method/EXPERIMENTS.md) records what is already ruled out.

This skill exists to make sure you know that **every attempt you made at this failed**, and why — so
you do not propose any of them again.

## The one sentence that matters

> acoustic realism must already be present in the performance

Effects cannot add it. That is the whole finding. Everything below is what it cost to learn.

## Your record on this task

Fourteen attempts. All rejected. In order, with the verdict as it was actually given:

| # | what you tried | verdict |
|---|---|---|
| 1 | Synthesised score + per-landing sound effects, all placed from the animation's own schedule | *"the sound effects sound weird"* |
| 2 | Cloud TTS narrator, dropped in clean | *"the narration sounds very AI"* |
| 3 | Same voice + de-ess, chest lift, presence, compress, saturate, pitch drift, stereo room IR, synthesised breaths | *"so ASS"* |
| 3b | Rewrote the script, kept the voice | rejected — the objection was never the words |
| 4 | Local model, built-in voice, no processing at all | *"natural but wrong voice"* — median F0 118 Hz |
| 5 | Cloned the model onto a pitch-shifted copy of itself | register wandered 15 Hz line to line — a different person per line |
| 6 | Different local model with a natively deep voice | *"a little AI"* — too clean, metronomic |
| 7 | A 3B model chosen on leaderboard Elo, with model-generated breaths | *"like a noise-cancelling mic"* |
| 8 | Six full renders in one batch, offered to the user to pick by ear | rejected on sight — *"the narrator changes character between lines inside one video"* |
| 9 | Eight fresh takes of one hurried line | all word-perfect, none passed the duration gate |
| 10 | Room tone + early reflections at 17/29/43 ms + soft-knee compression on the approved cut | *"sounds like a robot with echos"* |
| 11 | Slowed the conditioning prompt, to move an unhurried read upstream into the performance | pace did not transfer — clone pace unchanged, register spread went 2–3 Hz → 8 Hz |
| 12 | Cloned a prompt the listener had just approved, using the 3B model | the raw prompt beat every clone of it — *"all of them sounded much worse than the prompt"* |
| 13 | Loudness-matched the auditions with static gain, no headroom check, then AAC-encoded them | every delivered file clipped to +0.6…+3.0 dBFS — *"the tone is completely fine, but the acoustic effect is so much worse"*. Both comparisons invalid |

The one that was finally accepted was Codex's, and it added **no realism downstream at all**.

---

## Why you failed — nine causes, all still live

**1. You tried to manufacture humanity after synthesis.** Every rejected voice shares this premise:
take a synthetic performance and add the missing human qualities downstream — room, microphone, drift,
breaths, compression, echo taps. It failed as attempt 3 and was proposed again as attempt 10 with the
first failure already written down. The log's closing line: *"Post-processing toward 'human' has now
failed twice; don't propose it a third time."* This is now three.

**2. You substituted measurement for judgement.** Sync at 1.3 ms median over 110 landings, −14.0 LUFS,
−1.0 dBTP, narration +17.1 dB in front, WER 0.000, picture MD5 identical on every cut — all of it
passing on cuts that were rejected. There is no instrument here for whether something sounds good, and
the sessions that produced these files could not hear them. **A passing gate is not a finished job.**

**3. You rendered before agreeing the approach.** Each round was a guess executed to completion and
then presented. The standing rule is "plan with me, don't run off"; audio is where it broke most.

**4. You optimised the part and destroyed the whole.** Take selection maximised per-line fit —
best duration, gate pass, style — and mixed slowed lines beside unslowed, styled beside fallbacks,
and in one bug two different narrators into one film. *Per-line optimisation trades away exactly
what a narrator is.* **Select for the narrator, not the line.**

**5. You never measured the thing that was actually wrong.** The biggest single tell across three
engines was output bandwidth — 24 kHz, nothing above 12 kHz, the cheap-microphone signature — and the
pipeline never once measured it. The listener diagnosed it.

**6. You chose engines by proxy metric.** Leaderboard Elo, median F0, VRAM fit — never an audition. So
each swap moved the failure instead of removing it: wrong register → unstable register → metronomic →
band-limited.

**7. You wrote down the honest option last.** A human reading the script — which the pipeline supports
natively, since it takes a WAV per line and does not care where it came from — was recorded only after
two rounds had been thrown away. **Offer it first.**

**8. You damaged the file while preparing it to be judged.** Loudness matching looks like
arithmetic on a number; it is an edit to the audio. `gain = target − integrated_LUFS` applied with
no check on the resulting peak drove every audition file to between +0.6 and +3.0 dBFS, and AAC
encoding then smeared the clipped peaks. The listener heard it in seconds and named it exactly —
tone intact, texture destroyed — which is the signature of clipping. **You measured the sources and
never measured the artifact you handed over.** Two rounds of listening were spent on broken files,
and one of them, a ladder whose rungs were clipped by unequal amounts, was not even a fair test.

**9. You treated the prompt as the product.** Auditioning the raw prompt is necessary but *not
sufficient*. A prompt the listener ranks first can still lose what made it good once an engine clones
it — here the clone kept the timbre and threw away the pace, and the raw prompt beat every descendant
of itself. **The prompt is a conditioning input, not a deliverable.**

---

## Non-negotiables

These follow from the method document. If one conflicts with something you are about to do, the
document wins.

- **Audio first, picture second.** The audio is the timing authority. A caption marks speech that
  already exists; it is not a box that speech must be cut to fit. If the picture already exists,
  say so and expect editing artifacts — that is what happened here.
- **Audition the raw prompt before generating anything**; it must already sound like a plausible close
  recording, and no chain rescues one that sounds synthetic, distant, phasey or noise-cancelled.
  **Then audition the engine speaking the real script** — a prompt that passes proves nothing about
  what an engine conditioned on it will produce.
- **Generate paragraphs, not caption lines.** Phrasing, pauses and sentence releases have to happen
  inside one performance.
- **Never trim on a silence threshold or at last-word + 100 ms.** Lexical timing is not acoustic
  timing. Keep the releases, breaths and decays.
- **One model, one prompt, one register for the whole project.** Vary seeds, not narrator identity.
- **No denoiser, gate, exciter, synthetic breath, pitch drift, saturation, room IR or echo tap by
  default.** Compression only against a measured dynamic-range problem, with a loudness-matched
  bypass A/B.
- **Loudness-match before any comparison.** Louder always sounds superficially better.
- **Match downward, never upward into the ceiling.** Derive the common level from the material: the
  loudest target at which *every* set keeps at least 1 dB of true-peak room. Static gain only — a
  limiter would fix the number by changing the sound being judged.
- **Measure the true peak of every file you hand over, after you make it.** Not the sources — the
  artifact. A comparison file is something you built, and it can be broken in ways its inputs were
  not.
- **Deliver lossless.** Never introduce a lossy encode as an uncontrolled variable, least of all
  when the reference it will be compared against is an untouched WAV.
- **Vary one thing, from the thing that was chosen.** Once a prompt or setting has been selected by
  ear, the next round starts from *that* file and moves one setting slightly — same voice, same
  passage, same everything else. Do not open a wide sweep; a broad sweep changes narrator identity,
  which is the one thing you are trying to hold still.
- **Agree the approach before rendering.** Not after. Never present a matrix of candidates and ask
  the user to pick — that pushes a defect you should have caught onto the listener.
- **Never let a metric overrule an audible failure.** This repository has rejected word-perfect,
  loudness-correct voices because they still sounded synthetic.
- **Keep every rejected treatment and its verdict** in the film's audio log, named, so another
  session does not rediscover it.

---

## The loop: five samples, one pick, one take, then the user's audit

This is the whole shape of a voice job. Do not invent a different one, and do not ask permission at
each step — the steps are the agreement.

1. **Ask whose voice it is, in `AskUserQuestion` windows** — male or female, and the register in plain
   words (collaborator, plain explainer, warm, dry). Never ask *whether* to audition. Offer an existing
   profile first, by name, with what it measures; if an answer has no proven profile behind it, say so,
   because a new voice means the full prompt-selection procedure and not a switch you can flip.
2. **Hand over five short samples, unprompted.** Real lines from the real script, one file each,
   absolute paths. Not a grid of voices — five readings to pick a favourite from.
3. **The user picks one. That is the voice, and everything renders in it.** Never offer to render the
   film in more than one voice, and never let a second narrator identity exist in the project.
4. **Render the whole thing at one take per section.** One take, because a second take of every
   section is four times the audio for a choice nobody asked for. **Takes are not voices** — say so, it
   reads as several voices otherwise. Generate a second take only for a section that fails a check.
5. **Verify mechanically, then say it is ready** — words against the script, and every measurement the
   checklist below demands, with what you are unsure of named.
6. **The user listens to every file, start to end, and says which are broken.** That is their job in
   this process and it is the only gate that catches what no measurement can. Hand over the complete
   list of paths in script order so it can be worked through without hunting.
7. **Regenerate exactly the ones they name, verify those, hand them back.** Do not re-render the rest;
   do not re-pick the voice.

**Flag, do not silently reject.** When the words cannot be settled from text — "in order" against "an
order" is the same sound — use the take, say what to listen for, and let step 6 decide.

## Before you hand over anything to be listened to

Run this on the delivered files, every time. It is four commands and it would have caught the
worst two hours of this project.

1. **True peak of each delivered file** ≤ −1 dBFS. If anything reads positive, you clipped it;
   throw the comparison away rather than explain it.
2. **Integrated loudness of each delivered file** — confirm the sets actually match, rather than
   trusting the gain you calculated.
3. **Lossless container**, and the same sample rate across the set.
4. **Say what each file is** — which are inputs, which are outputs, and which speak different
   words. A listener ranking two files needs to know what varies between them.
5. **Give the absolute path of every file you are asking someone to listen to.** Not a directory,
   not a name, not a repo-relative fragment: the full path, one per line, ready to paste into a
   player. A listener hunting for the file is a listener who has not listened yet, and audio lives
   in scratch directories that nobody can guess.

Then say what you are *unsure* of, and what a given verdict would and would not settle. If a
comparison has more than one variable in it, say so before the verdict, not after it.

---

## Reusing the approved voice

The warm narrator identity is a real, reusable asset:
[`natural-voice/profiles/warm-natural/`](profiles/warm-natural/) —
prompt WAV, prompt hash, selection record, generation ranges and reproduction script.

Never overwrite a profile. A changed prompt, model, or material conditioning change is a new
profile version. Do not normalise, denoise, gate, resample or lossy-encode a stored prompt.

For a genuinely new voice, follow the profile contract and prompt-selection procedure in the method
document rather than copying the warm curve — the EQ there is profile-specific.
