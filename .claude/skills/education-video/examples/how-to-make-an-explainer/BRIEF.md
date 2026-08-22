# How to make an explainer — the film's brief

Stage 0 output: the fifteen answers that decide what gets made. Settled 2026-08-13, before any
document, script or line of audio existed. Anything reopened later gets changed here first.

**Subject:** the four-stage method for making an explainer video, taught by a film made that way.
**Its own source document:** [`SOURCE.md`](SOURCE.md) — written for this film, audited at stage 1.

## The audience

A technical person who knows their own subject cold and has never made a video. Assume no
production knowledge whatsoever: no audio, no editing, no timecodes, no synthetic voice. Tone is a
peer who has already paid for these mistakes.

## Shape

Numbers below are keys into [`NUMBERS.md`](NUMBERS.md), which is their only home.

| | decided |
|---|---|
| runtime | `FILM.runtime`, `FILM.scenes`, `FILM.words` |
| precedent | the deleted trial film: `TRIAL.words` → `TRIAL.duration`, `TRIAL.cues` |
| picture | the real artifacts on screen — checklist ticking, a document with one number lit, a cue sheet, a waveform, a scene table |
| delivery | `DELIVER.picture`, silent picture + SRT captions from the locked master |
| voice | the approved `warm-natural` profile, [`../../natural-voice/profiles/warm-natural/`](../../../natural-voice/profiles/warm-natural/) |
| files | this directory; heavy takes and masters under `video/out/education/how-to-make-an-explainer/` |
| tooling | written fresh — nothing restored from the deleted trial, so this run tests the method with no inheritance |

The picture register is literal on purpose: a film that tells you to write a document, then shows
one, is demonstrating rather than asserting.

**Order of the scenes, decided after the first review of [`SOURCE.md`](SOURCE.md):** scene one is
where the viewer is standing — you finished the thing, people have to understand it, you want a
short clean video and don't know how to start. Scene two is the architecture, whole, before any
detail. Then the four stages in order, then the verdict and the install.

**Nothing about what goes wrong appears in the opening.** The viewer has not started, so they have
not failed; a cost only means something once they know which stage it belongs to.

## Evidence rule

**Only numbers re-derived from files that exist now may be spoken as measured.** A number the repo
merely *records* is spoken as recorded ("the log says"); an estimate is spoken as an estimate; a
choice this film made is never spoken as a finding. Every row of [`NUMBERS.md`](NUMBERS.md) carries
its grade and the method that produced it, and the measured ones re-derive with
[`tools/verify_numbers.py`](tools/verify_numbers.py).

## The verdict it ends on

**The four stages, in this order: document → script → audio → picture.** Each reversal is named
with its own cost — document last, script skipped, audio last — and loses on screen. The film does
not end on a single insight; it ends on the ordering rule.

## Vocabulary

**Plain speech, terms on screen.** The narration names nothing it would have to define: "one line
of narration", "the seconds it has to breathe", "the finished sound file, frozen". The picture
labels those same things with the working words, so a viewer leaves able to read the skill's files
without ever being lectured mid-sentence.

Reuse the phrases already load-bearing in the source where they fit — one number, one home; the
sound decides the timing; leave a hole at the top of every scene.

## The skill, and the honest limit

The skill is named **at every stage**, not just at the end: each scene says what the skill does for
you at that point in the process. The instruction to go and install it lands at the close, and the
limit is spoken once, there — **built and verified with Claude; other models are untested, which is
unknown rather than broken.**

The repository is not public yet, so the script carries `{{REPO}}` as a marked placeholder in a
short cue of its own, re-recordable in seconds once the name exists. **No URL gets invented.**

## Do not narrate

- **Nothing specific to this project's hardware.** No part numbers, no ppm/°C, no thermoelectric
  cooler. The failures are told generically so the film travels to any subject.
- **No voice-engine or model names**, no GPU or memory figures. They date fast and turn a method
  film into a tool review.
- **No claim about how anything sounds.** Not natural, not human, not good. There is no instrument
  for that here, and asserting it would break the film's own rule in the film's own voice.
