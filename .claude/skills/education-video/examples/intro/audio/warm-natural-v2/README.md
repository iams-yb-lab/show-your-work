# Warm-natural education narration v2

This is the education film's reproducible production record: generation, fixed-picture alignment, speech
restoration, score, mix, verification and reports. Reusable voice identity and acoustic method are shared
separately under [`../../../../../natural-voice/`](../../../../../natural-voice/).

## Layout

| location | contents |
|---|---|
| `video/natural-voice/profiles/warm-natural/` | Immutable narrator prompt and profile |
| this directory | Tracked film-specific scripts, settings, manifests and reports |
| `video/out/education/warm-natural-v2/` | Ignored raw takes, aligned/restored speech, stems and final WAV |
| `video/out/releases/` | Canonical final MP4 |
| `video/education/intro/picture/` | Canonical silent picture master |
| `video/education/intro/script/` | Canonical settled script and captions |

## What v2 repaired

The picture already existed, so v2 had to split contextual narration back into 49 fixed cue slots. It
reconstructed the approved Chatterbox takes without the former `top_db=40` end trim, kept 0.44–1.235 s
after lexical endings, applied a 12 ms landing fade and added 160 ms quiet post-roll. Cue 13 kept its exact
approved v1 performance because its raw replay slurred one phrase.

This alignment solved the worst truncation but did not make every inter-sentence join perfect. That is an
editing limitation, not a defect in the acoustic voice. Future films must use the audio-first workflow in
[`../../../../natural-voice/README.md`](../../../../../natural-voice/method/README.md): generate continuous narration,
lock it, then time captions and picture to it.

## Voice and sound

- Voice: local ChatterboxTTS 0.1.7, synthetic prompt, no real-person clone.
- Register: warm and collaborative, not deep/epic.
- Context: two to four sentences generated together.
- Bandwidth: conditional MossFormer2_SR_48K restoration; 36 cues accepted, 13 clean-resample fallbacks.
- Voice processing: corrective EQ and gain only—no denoise, gate, compression, exciter, reverb or echo.
- Music: 104 BPM, G major, constant −29.5 LUFS bed; no noise sources and no ducking.
- Master: measured −14.59 LUFS / −0.99 dBTP.
- Picture: H.264 stream-copied; MD5 `eed58d07f776f0be1a0b0860461b4f64`, identical to the silent master.

## Run and verify

A fresh run refuses to overwrite v2. It writes heavy artifacts only under `video/out/`:

From the repository root, with the venv that has the audio stack in it:

```powershell
& $env:EDITX_PYTHON video\education\intro\audio\warm-natural-v2\run_pipeline.py
```

Verify the existing release after a move or toolchain change without replacing it:

```powershell
& $env:EDITX_PYTHON video\education\intro\audio\warm-natural-v2\run_pipeline.py --verify-existing
```

The interpreter comes from `EDITX_PYTHON` rather than a written-out path: the two commands here
used to name one machine's venv inside one checkout, and were wrong on both counts after a move.

## Records

- `education-v2-generation-settings.json` — every film-specific take, seed and model argument.
- `reference/` — approved v1 group/take selection manifests.
- `environment.txt` — package versions for the three local environments.
- `pipeline.log` — historical execution log; pre-migration absolute paths are intentionally preserved.
- `pipeline-status.json` / `final-report.json` — current final paths and verification.
- `protected-input-hashes.json` — picture, script, captions, prompt, checkpoint and prior-delivery hashes.
- `video/out/education/warm-natural-v2/voice-raw-selected/generation-report.json` — raw replay record.
- `video/out/education/warm-natural-v2/voice-aligned-24k/alignment-report.json` — ASR and tail QA.
- `video/out/education/warm-natural-v2/voice-restored-48k/sr-report.json` — restoration decisions.
- `video/out/education/warm-natural-v2/mix/mix-report.json` — EQ, levels and picture-stream integrity.
