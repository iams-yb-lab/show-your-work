r"""v8 narration: all six lines from the chosen prompt, with nothing removed.

Chosen by ear on the A/B audition: prompt B, Kokoro `am_onyx` at speed 0.78.
That overruled the measurement, which favoured A — B's take-to-take F0 spread
was 8 Hz against A's 2-3 Hz. `video/natural-voice/README.md` is explicit that a
metric never overrules an audible verdict, so B ships and the spread is handled
where v7 handled it: joint selection over a larger pool. Hence 8 takes a line
rather than v7.2's 4.

Differences from `pipeline/editx_gen.py`, which produced v7.2:

  * no trim. v7.2 ran librosa.effects.split(top_db=40) with a 60 ms pad before
    writing every take, so releases and breaths were destroyed upstream of
    everything and the raw was never kept. EXPERIMENTS.md lists that operation
    as rejected. Here the model's output is written as produced, and the
    lexical span is *measured* so the mix can place a line by subtracting its
    lead-in instead of cutting it off.
  * plain clones only, no paralinguistic or style edit pass. v7's consistency
    correction found that mixing edit kinds per line is what made the narrator
    change character between lines.
  * take selection is not done here. This script only generates and measures;
    `select_v8.py` chooses the narrator across all six lines at once.

Run in `%TEMP%\editx-venv`. Writes to `video/out/showoff/natural-v8/takes/`.
"""
import difflib
import json
import os
import re
import sys
from pathlib import Path

os.environ["PATH"] += os.pathsep + (
    r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
)

IMPL = Path(os.environ["TEMP"]) / "editx-node" / "step_audio_impl"
os.chdir(IMPL)
sys.path.insert(0, str(IMPL))

import numpy as np
import torch
import librosa
import soundfile as sf

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See video/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "video" / "natural-voice").is_dir())
ROOT = REPO / "video" / "out" / "showoff" / "natural-v8"
OUT = ROOT / "takes"
OUT.mkdir(parents=True, exist_ok=True)

PROMPT_WAV = str(ROOT / "prompts" / "onyx_prompt_s078.wav")
PROMPT_TEXT = (
    "In the beginning, there was only silence. Then, from the silence, an instrument was born. "
    "Patient, precise, and calm beyond measure, it waited for its purpose."
)

# starts are v7.2's approved placements: nudged off the score's 70-frame
# (2.3333 s) downbeat grid into the pulse gaps, with line 5 clearing the
# 57.3 s ADC bell. `cap` is the spoken length that still ends before the
# music-only fade at ~82.5 s once the mix's atempo has stretched it.
LINES = [
    (1, "It all begins with a bare board... and an idea precise enough to become real.", 2.85, 8.0),
    (2, "A thousandth of a degree... that is the promise written into every trace.", 14.50, 9.0),
    (3, "Then, piece by piece, purpose takes form.", 28.70, 9.0),
    (4, "Power. Sensing. Control. Every component answers the same demand.", 47.25, 9.0),
    (5, "And at its heart — a sentinel, listening for the faintest whisper of heat.", 58.90, 9.0),
    (6, "Until the instrument stands complete... ready to master the invisible frontier "
        "between heat... and control.", 72.95, 8.8),
]
N_TAKES = 8


def norm_words(s):
    s = re.sub(r"\[.*?\]", " ", s)
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()


def wer(ref, hyp):
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


def lexical_span(y, sr, top_db=40):
    """Where the words sit. Measured, never cut — see the module docstring."""
    iv = librosa.effects.split(y, top_db=top_db)
    if len(iv) == 0:
        return 0.0, len(y) / sr
    return float(iv[0][0] / sr), float(iv[-1][1] / sr)


def to_numpy(audio):
    if isinstance(audio, torch.Tensor):
        audio = audio.cpu().numpy()
    return np.asarray(audio, dtype=np.float32).squeeze()


def main():
    from tokenizer import StepAudioTokenizer
    from tts import StepAudioTTS
    from model_loader import ModelSource

    models = Path(os.environ["TEMP"]) / "editx-models"
    encoder = StepAudioTokenizer(str(models / "Step-Audio-Tokenizer"), model_source=ModelSource.LOCAL)
    engine = StepAudioTTS(str(models / "Step-Audio-EditX"), encoder, model_source=ModelSource.LOCAL)
    print(f"models loaded; prompt = {PROMPT_WAV}", flush=True)

    import whisper

    asr = whisper.load_model("base.en", device="cuda")

    manifest = []
    for lid, text, start, cap in LINES:
        takes = []
        for ti in range(1, N_TAKES + 1):
            torch.manual_seed(91000 * lid + ti)
            audio, sr = engine.clone(PROMPT_WAV, PROMPT_TEXT, text)
            y = to_numpy(audio)  # written exactly as produced
            path = OUT / f"line{lid}_take{ti}.wav"
            sf.write(str(path), y, sr)

            hyp = asr.transcribe(str(path), language="en")["text"].strip()
            w = wer(norm_words(text), norm_words(hyp))
            med, iqr = f0_stats(y, sr)
            lex0, lex1 = lexical_span(y, sr)
            dur = len(y) / sr
            takes.append(
                dict(
                    take=ti,
                    path=str(path),
                    seed=91000 * lid + ti,
                    sample_rate=int(sr),
                    duration_s=round(dur, 3),
                    spoken_s=round(lex1 - lex0, 3),
                    lex_start_s=round(lex0, 3),
                    lex_end_s=round(lex1, 3),
                    tail_s=round(dur - lex1, 3),
                    wer=round(w, 4),
                    median_f0_hz=round(med, 2),
                    f0_iqr_hz=round(iqr, 2),
                    over_cap=bool((lex1 - lex0) > cap),
                    transcript=hyp,
                )
            )
            flag = "  OVER CAP" if (lex1 - lex0) > cap else ""
            print(
                f"  line{lid} take{ti}: {dur:5.2f}s  spoken {lex1 - lex0:4.2f}s  "
                f"lead {lex0:4.2f}s  tail {dur - lex1:4.2f}s  wer={w:.3f}  "
                f"F0 {med:.0f} Hz (IQR {iqr:.1f}){flag}",
                flush=True,
            )

        good = [t for t in takes if t["wer"] <= 0.0 and not t["over_cap"]]
        print(
            f"  line{lid}: {len(good)}/{N_TAKES} word-perfect and inside cap, "
            f"F0 {sorted(round(t['median_f0_hz']) for t in good)}\n",
            flush=True,
        )
        manifest.append(dict(line=lid, text=text, start=start, cap_s=cap, takes=takes))

    (OUT / "manifest.json").write_text(
        json.dumps(
            dict(
                prompt_wav=PROMPT_WAV,
                prompt_text=PROMPT_TEXT,
                model="stepfun-ai/Step-Audio-EditX",
                n_takes=N_TAKES,
                trimmed=False,
                note="Raw model output. Lexical span measured for placement, never cut.",
                lines=manifest,
            ),
            indent=2,
        )
    )
    print(f"wrote {OUT / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
