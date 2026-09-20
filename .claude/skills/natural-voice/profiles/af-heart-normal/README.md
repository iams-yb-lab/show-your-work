# af-heart-normal

Female explainer voice at normal speaking pace. Selected 2026-08-21 for the Doppler cooling /
magneto-optical trap film, from six Kokoro female presets auditioned on one identical passage.

## What it is

Kokoro-82M's built-in preset `af_heart`, American, at `speed=1.0`. **A named preset, not a
clone** — there is no conditioning prompt and no real person behind it, so there is no prompt
WAV to keep immutable and no prompt hash. That is a genuine structural difference from
`warm-natural`, which is a Chatterbox identity carried in a prompt file.

| measurement | value |
|---|---:|
| median F0 | 202 Hz |
| F0 IQR | 51 Hz |
| delivered rate | 182 wpm |
| word error rate | 0.027 (a transcriber spelling *metres* as "meters" — not a speech error) |
| sample rate | 24 kHz |

## How it was chosen

One variable: the voice. Every candidate spoke the same passage, at the same speed, with the
same seed, and the set was loudness-matched to a common −25.28 LUFS before anyone listened —
that being the loudest level at which every file kept 1 dB of true-peak room, by static gain,
with no limiter. Louder always sounds better, so an unmatched audition decides nothing.

The five it beat, and `warm-natural` before them, are listed in `profile.json` under
`selection.rejected_alternatives` so a later session does not re-audition them blindly.

## Using it

```python
import espeakng_loader
from phonemizer.backend.espeak.wrapper import EspeakWrapper
EspeakWrapper.set_library(espeakng_loader.get_library_path())
EspeakWrapper.set_data_path(espeakng_loader.get_data_path())

from kokoro import KPipeline
pipe = KPipeline(lang_code="a", device="cuda")
chunks = list(pipe(text, voice="af_heart", speed=1.0))
```

The espeak wiring is **not optional** on a machine without a system espeak-ng. Without it,
misaki's out-of-dictionary fallback never arms, and G2P returns `None` phonemes for any word
outside its lexicon — a single British spelling such as *metres* crashes the render.

Install on Python 3.13 needs the sequence in `profile.json → install_notes`; the ordinary
`pip install kokoro` fails because its dependency chain pins a spacy/thinc with no cp313 wheels.

## Limits — read before processing anything

- **24 kHz output, so zero energy above 12 kHz.** Measured, not theoretical. Whether that reads
  as a noise-cancelling-mic texture on this voice is an open question and has not been tested.
- **No EQ curve exists for this profile.** Do not paste the `warm-natural` curve onto it. That
  curve was measured on a male voice roughly an octave lower, and the method is explicit that it
  is profile-specific rather than a preset.
- **Speed stays at 1.0.** The film that selected this voice was explicitly required to keep
  normal speaking pace and take its length from the picture instead. `deep-onyx-slow` runs at
  0.78; that belongs to that profile, not this one.
- **Restoration untested.** `MossFormer2_SR_48K` is the method's answer to the band-limit, but
  it has not been run against this voice, and on the reference film it failed its checks on
  roughly a quarter of sections.
