r"""v8 narration — the method's steps 3-6, on the selected voice.

Selected by ear: Kokoro-82M `am_onyx` at speed 0.78, generating directly. No
cloning. The 3B EditX model that produced v7.2 is not in this pipeline; the
listener ranked its raw prompt above every clone of that prompt.

`natural-voice/method/README.md`, followed in order:

  3. generate complete sections, several seeded takes each
  4. transcribe every take, reject wrong words before judging style
  5. select a coherent set, keeping each section continuous
  6. preserve the raw beginning, ending and internal silences

Step 6 is the one v7.2 broke. `pipeline/editx_gen.py` ran
librosa.effects.split(top_db=40) with a 60 ms pad before writing every take,
so releases and breaths were destroyed upstream of everything and the raw was
never kept. Nothing here trims. The lexical span is measured so the mix can
place a line by subtracting its lead-in instead of cutting it away.

Run in `%TEMP%\sr-venv`. Writes `out/showoff/natural-v8/kokoro_takes/`.
"""
import difflib
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
import torch
import librosa
import soundfile as sf

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See _shared/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / ".claude" / "skills" / "natural-voice").is_dir())
ROOT = REPO / "out" / "showoff" / "natural-v8"
OUT = ROOT / "kokoro_takes"
OUT.mkdir(parents=True, exist_ok=True)

VOICE = "am_onyx"
SPEED = 0.78
N_TAKES = 4
BASE_SEED = 20260813

# v7.2's approved placements: off the score's 70-frame (2.3333 s) downbeat grid
# and into the pulse gaps, with line 5 clearing the 57.3 s ADC bell. The cap is
# the spoken length that still ends before the music-only fade.
LINES = [
    (1, "It all begins with a bare board... and an idea precise enough to become real.", 2.85, 10.0),
    (2, "A thousandth of a degree... that is the promise written into every trace.", 14.50, 12.0),
    (3, "Then, piece by piece, purpose takes form.", 28.70, 15.0),
    (4, "Power. Sensing. Control. Every component answers the same demand.", 47.25, 10.0),
    (5, "And at its heart — a sentinel, listening for the faintest whisper of heat.", 58.90, 12.0),
    (6, "Until the instrument stands complete... ready to master the invisible frontier "
        "between heat... and control.", 72.95, 9.5),
]


def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()


def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(max(i2 - i1, j2 - j1)
               for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs / max(1, len(ref))


def f0_stats(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    if not f0.size:
        return float("nan"), float("nan")
    return float(np.median(f0)), float(np.percentile(f0, 75) - np.percentile(f0, 25))


def lexical_span(y, sr, top_db=40):
    """Measured for placement. Never used to cut — see the module docstring."""
    iv = librosa.effects.split(y, top_db=top_db)
    if len(iv) == 0:
        return 0.0, len(y) / sr
    return float(iv[0][0] / sr), float(iv[-1][1] / sr)


def main():
    from kokoro import KPipeline

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = KPipeline(lang_code="a", device=dev)

    import whisper

    asr = whisper.load_model("base.en", device=dev)

    manifest = []
    determinism_note = None
    for lid, text, start, cap in LINES:
        takes, seen = [], {}
        for ti in range(1, N_TAKES + 1):
            torch.manual_seed(BASE_SEED + 1000 * lid + ti)
            chunks = [a for _, _, a in pipe(text, voice=VOICE, speed=SPEED)]
            y = torch.cat(chunks).numpy().astype(np.float32)  # written as produced

            digest = hashlib.sha256(y.tobytes()).hexdigest()
            if digest in seen:
                takes.append(dict(take=ti, duplicate_of=seen[digest], sha256=digest))
                print(f"  line{lid} take{ti}: identical to take{seen[digest]}", flush=True)
                continue
            seen[digest] = ti

            path = OUT / f"line{lid}_take{ti}.wav"
            sf.write(str(path), y, 24000)
            hyp = asr.transcribe(str(path), language="en")["text"].strip()
            w = wer(norm_words(text), norm_words(hyp))
            med, iqr = f0_stats(y, 24000)
            lex0, lex1 = lexical_span(y, 24000)
            dur = len(y) / 24000
            takes.append(dict(
                take=ti, path=str(path), seed=BASE_SEED + 1000 * lid + ti, sha256=digest,
                sample_rate=24000, duration_s=round(dur, 3), spoken_s=round(lex1 - lex0, 3),
                lex_start_s=round(lex0, 3), lex_end_s=round(lex1, 3), tail_s=round(dur - lex1, 3),
                wer=round(w, 4), median_f0_hz=round(med, 2), f0_iqr_hz=round(iqr, 2),
                over_cap=bool((lex1 - lex0) > cap), transcript=hyp))
            print(f"  line{lid} take{ti}: {dur:5.2f}s  spoken {lex1 - lex0:5.2f}s  "
                  f"lead {lex0:4.2f}s  tail {dur - lex1:4.2f}s  wer={w:.3f}  "
                  f"F0 {med:.0f} Hz (IQR {iqr:.1f})"
                  + ("  OVER CAP" if (lex1 - lex0) > cap else ""), flush=True)

        unique = [t for t in takes if "duplicate_of" not in t]
        if len(unique) == 1 and len(takes) > 1 and determinism_note is None:
            determinism_note = (
                "Kokoro is deterministic for a fixed text, voice and speed: seeding produced "
                "byte-identical output. Multiple takes are therefore not available for this "
                "engine, and no by-ear take selection is possible or needed. The upside is that "
                "cross-line register consistency is exact rather than optimised for."
            )
        manifest.append(dict(line=lid, text=text, start=start, cap_s=cap, takes=takes))
        print("", flush=True)

    (OUT / "manifest.json").write_text(json.dumps(dict(
        engine="hexgrad/Kokoro-82M", voice=VOICE, speed=SPEED, base_seed=BASE_SEED,
        trimmed=False, determinism=determinism_note,
        note="Raw model output. Lexical span measured for placement, never cut.",
        lines=manifest), indent=2))

    if determinism_note:
        print(determinism_note, flush=True)
    f0s = [t["median_f0_hz"] for l in manifest for t in l["takes"] if "median_f0_hz" in t]
    print(f"\ncross-line F0 {min(f0s):.1f}-{max(f0s):.1f} Hz "
          f"(spread {max(f0s) - min(f0s):.1f} Hz)", flush=True)
    print(f"wrote {OUT / 'manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
