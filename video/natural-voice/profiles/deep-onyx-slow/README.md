# deep-onyx-slow

The assembly film's narrator: deep, slow, calm. Kokoro-82M's preset `am_onyx` at speed 0.78,
generating directly. Selected by ear on 2026-08-13.

## How this profile differs from `warm-natural`

`warm-natural` is a Chatterbox voice with a conditioning prompt WAV, and its prompt file is an
input to every generation. **Kokoro takes no conditioning prompt.** `deep_onyx_slow_reference.wav`
is an identity reference for auditioning and comparison only; nothing reads it at generation time.
Reproduce this voice from `voice`, `speed` and `seed`, not from the file.

The profile contract still applies to it: never overwrite it, never normalise, denoise, gate,
resample or lossy-encode it. A changed voice or speed is a new profile version.

## Use

```python
from kokoro import KPipeline
pipe = KPipeline(lang_code="a", device="cuda")
chunks = [a for _, _, a in pipe(text, voice="am_onyx", speed=0.78)]
```

Write what comes out. Do not trim it — see below.

## Limits, and what was learned getting here

- **Seeding barely varies it.** Four takes of a line differ only in sampling noise and have
  identical durations. There is no meaningful by-ear take selection for this engine, and no
  consistency machinery is needed: cross-line register spread is 4.7 Hz across the six lines
  without any selection at all.
- **Do not silence-trim it.** Every line arrives with 0.26–0.32 s of lead-in and 0.84–1.01 s of
  tail. That tail is the sentence release, and it is most of what makes the read sound unhurried.
  Place a line by subtracting its measured lead-in from its anchor, so the first word lands where
  it should while the file keeps both ends.
- **Do not clone it to get something else.** A 3B cloning model conditioned on this voice was
  ranked below the voice itself — it kept the timbre and lost the pace. The raw engine won.
- **Do not time-stretch it.** At 0.78 the read is already unhurried at the source; v7.2 needed
  `atempo` because its engine would not slow down, and this one does not.
- **Adjust it in small steps.** If the pace needs to move, the next version is 0.76 or 0.80 —
  derived from this profile, one setting at a time. A wide sweep changes narrator identity.
- Output is 24 kHz, so it has nothing above 12 kHz. `MossFormer2_SR_48K` restoration passed its
  gates on all six lines of the first production, adding measurable energy above 12 kHz with word
  error rate 0.000 and pitch moving at most 3 Hz.

## Listening notes

Line 3, *"Then, piece by piece, purpose takes form."*, comes out with a noticeably wider pitch
range than the rest — F0 IQR 20.6–25.9 against 11.7–15.9 everywhere else. It is the shortest line
and the only one whose delivery reads as more expressive than its neighbours. Nothing has been
done about it; it is recorded here so the next session knows it was seen and not missed.
