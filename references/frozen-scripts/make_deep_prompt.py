r"""v8 prompt candidates for the deep showoff narrator.

The v7.2 narrator is Step-Audio-EditX cloning `onyx_prompt.wav` — Kokoro
`am_onyx` reading a neutral passage at speed 0.88. Its one unresolved defect is
pace: eight fresh line-1 takes all came back too fast, because the clone
inherits the prompt's pace. v7.2 fixed that downstream with `atempo=0.90/0.93`.

`video/natural-voice/README.md` puts the fix upstream, in the performance. So
this generates slower candidates of the SAME passage in the SAME voice — one
variable, per the EXPERIMENTS.md protocol — and measures each one the way the
method's prompt-selection section requires.

Nothing here picks a winner by measurement alone. Pitch and pace are
consistency measurements, not quality scores; the student's ears decide.

Run in `%TEMP%\sr-venv` (kokoro + torch). Writes to
`video/out/showoff/natural-v8/prompts/`.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

os.environ["PATH"] += os.pathsep + (
    r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
)

import numpy as np
import librosa
import soundfile as sf
import torch

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See video/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "video" / "natural-voice").is_dir())
OUT = REPO / "video" / "out" / "showoff" / "natural-v8" / "prompts"
OUT.mkdir(parents=True, exist_ok=True)

INCUMBENT = REPO / "video" / "out" / "showoff" / "voice-rnd" / "onyx_prompt.wav"

# Unchanged from gen_prompt.py. The register target for this film is an epic
# narrator, not the education film's collaborator, so the passage stays as-is;
# changing text and pace together would confound the comparison.
PROMPT_TEXT = (
    "In the beginning, there was only silence. Then, from the silence, an instrument was born. "
    "Patient, precise, and calm beyond measure, it waited for its purpose."
)

VOICE = "am_onyx"
SEED = 20260813
# 0.88 is v7.2's incumbent, regenerated here as a reproduction check.
SPEEDS = [0.88, 0.82, 0.78, 0.74]


def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()


def wer(ref, hyp):
    import difflib

    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(
        max(i2 - i1, j2 - j1)
        for op, i1, i2, j1, j2 in sm.get_opcodes()
        if op != "equal"
    )
    return errs / max(1, len(ref))


def f0_stats(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    if not f0.size:
        return float("nan"), float("nan")
    return float(np.median(f0)), float(np.percentile(f0, 75) - np.percentile(f0, 25))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measure(path, transcribe):
    y, sr = librosa.load(str(path), sr=None)
    med, iqr = f0_stats(y, sr)
    rec = dict(
        path=str(path),
        sha256=sha256(path),
        sample_rate=int(sr),
        duration_s=round(len(y) / sr, 3),
        median_f0_hz=round(med, 2),
        f0_iqr_hz=round(iqr, 2),
        peak=round(float(np.max(np.abs(y))), 4),
    )
    if transcribe is not None:
        hyp = transcribe(str(path))
        rec["transcript"] = hyp
        rec["word_error_rate"] = round(wer(norm_words(PROMPT_TEXT), norm_words(hyp)), 4)
    return rec


def main():
    transcribe = None
    try:
        import whisper

        asr = whisper.load_model("base.en", device="cuda" if torch.cuda.is_available() else "cpu")
        transcribe = lambda p: asr.transcribe(p, language="en")["text"].strip()
        print("whisper loaded", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: no whisper in this env ({e}); WER will be unmeasured", flush=True)

    from kokoro import KPipeline

    pipe = KPipeline(lang_code="a", device="cuda" if torch.cuda.is_available() else "cpu")

    records = []

    # the file v7.2 actually shipped on, measured with the same instruments
    inc = measure(INCUMBENT, transcribe)
    inc.update(candidate="incumbent-v7.2", voice=VOICE, speed=0.88, seed=None)
    records.append(inc)
    print(
        f"incumbent      {inc['duration_s']:5.2f}s  F0 {inc['median_f0_hz']:.1f} Hz  "
        f"IQR {inc['f0_iqr_hz']:.1f}  WER {inc.get('word_error_rate', float('nan'))}",
        flush=True,
    )

    for speed in SPEEDS:
        torch.manual_seed(SEED)
        chunks = [a for _, _, a in pipe(PROMPT_TEXT, voice=VOICE, speed=speed)]
        y = torch.cat(chunks).numpy().astype(np.float32)
        tag = f"s{str(speed).replace('.', '')}"
        path = OUT / f"onyx_prompt_{tag}.wav"
        # 24 kHz mono, matching the incumbent. No normalisation, no trim:
        # a stored prompt is never processed.
        sf.write(str(path), y, 24000)

        rec = measure(path, transcribe)
        rec.update(candidate=tag, voice=VOICE, speed=speed, seed=SEED)
        records.append(rec)
        print(
            f"speed {speed:<5}    {rec['duration_s']:5.2f}s  F0 {rec['median_f0_hz']:.1f} Hz  "
            f"IQR {rec['f0_iqr_hz']:.1f}  WER {rec.get('word_error_rate', float('nan'))}",
            flush=True,
        )

    (OUT / "prompt-candidates.json").write_text(
        json.dumps(
            dict(
                passage=PROMPT_TEXT,
                voice=VOICE,
                model="hexgrad/Kokoro-82M",
                seed=SEED,
                note=(
                    "Prompt candidates only. Selection is by ear on the cloned output, "
                    "not on these measurements."
                ),
                candidates=records,
            ),
            indent=2,
        )
    )
    print(f"\nwrote {OUT / 'prompt-candidates.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
