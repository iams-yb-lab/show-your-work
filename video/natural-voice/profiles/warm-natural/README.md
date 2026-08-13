# Warm narrator voice profile

This directory is the reusable identity for the approved warm technical narrator. Copy it as a unit; do
not normalize, denoise, resample or re-encode the prompt WAV.

`warm_narrator_prompt.wav` is a synthetic Chatterbox voice, not a clone of a real person. It was selected
from four locally generated readings of one neutral, welcoming passage. `make_warm_prompt.py` contains the
complete generation grid, seeds, transcription gate, pitch measurements, and selection score.

The selected prompt is mono, 24 kHz, and intentionally has no added reverb, echo, room impulse response,
compression, denoising, or noise floor. Its natural character is native model output. The narration
pipeline preserves that character by generating contextual passages, retaining the model's low-level
endings, conditionally restoring bandwidth, and applying only restrained EQ.

Files:

- `warm_narrator_prompt.wav` — immutable conditioning audio; SHA-256 is recorded in
  `voice-settings.json`.
- `warm_narrator_prompt.json` — the original four-take audition and selected measurements.
- `profile.json` — voice identity, prompt hash, acoustic policy and proven starting range.
- `make_warm_prompt.py` — self-contained prompt reproduction and selection procedure.

For a different future voice, create a separate profile directory with the same four artifacts. Judge the
prompt for acoustic realism before rendering narration: it must already sound like a person speaking in a
believable close-microphone space. Do not try to manufacture that quality later with an effects chain.

The education film's selected takes and seeds are in
[`../../../education/intro/audio/warm-natural-v2/education-v2-generation-settings.json`](../../../education/intro/audio/warm-natural-v2/education-v2-generation-settings.json).
The shared audio-first procedure is in [`../../README.md`](../../README.md).
