# Voice profiles

One directory per reusable voice identity. Each profile contains an immutable lossless prompt, its hash and
measurements, the prompt-generation or capture procedure, exact baseline model settings, and listening notes.

The shared production method is [`../method/README.md`](../method/README.md). Film-specific
takes, stems and mixes belong under `out/<film>/`; film-specific generation scripts and reports belong
with that film's `audio/` directory.

Current profiles:

- [`warm-natural/`](warm-natural/) — warm, collaborative technical explainer; synthetic Chatterbox identity.
- [`deep-onyx-slow/`](deep-onyx-slow/) — deep, slow, calm epic narrator; Kokoro preset, **no conditioning
  prompt**, so its stored WAV is an identity reference rather than a generation input.
