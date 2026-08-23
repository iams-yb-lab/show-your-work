r"""Clone the two audition lines from one prompt, with NOTHING removed.

The single change from `pipeline/editx_gen.py`: there is no `trim()`. v7.2's
generator ran `librosa.effects.split(y, top_db=40)` with a 60 ms pad on every
take *before* writing it, so the releases, breaths and decays were gone before
anything downstream could keep them — and the raw was never saved.
`video/natural-voice/EXPERIMENTS.md` lists that exact operation as rejected.
Here the model's output is written as produced.

Lines 1 and 6 are the audition set: the opening (v7.2's one pace complaint) and
the longest sentence / ending, per the method's QA gate 7.

Takes are plain clones only. v7's consistency correction found that mixing edit
kinds per line is what made the narrator change character between lines, so no
paralinguistic or style edit passes here.

Usage:  python audition_clone.py <prompt.wav> <tag>
Run in `%TEMP%\editx-venv`. Writes to `video/out/showoff/natural-v8/audition/<tag>/`.
"""
import difflib
import json
import os
import re
import shutil
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
OUT_ROOT = REPO / "video" / "out" / "showoff" / "natural-v8" / "audition"

PROMPT_TEXT = (
    "In the beginning, there was only silence. Then, from the silence, an instrument was born. "
    "Patient, precise, and calm beyond measure, it waited for its purpose."
)

LINES = [
    (1, "It all begins with a bare board... and an idea precise enough to become real."),
    (6, "Until the instrument stands complete... ready to master the invisible frontier "
        "between heat... and control."),
]
N_TAKES = 3


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
    """Where the words sit, WITHOUT cutting anything.

    The mix places a line by subtracting this lead-in from the delay, so the
    first word still lands on its anchor while the file keeps its full head and
    tail. Measuring is allowed; trimming is not.
    """
    iv = librosa.effects.split(y, top_db=top_db)
    if len(iv) == 0:
        return 0.0, len(y) / sr
    return float(iv[0][0] / sr), float(iv[-1][1] / sr)


def to_numpy(audio):
    if isinstance(audio, torch.Tensor):
        audio = audio.cpu().numpy()
    return np.asarray(audio, dtype=np.float32).squeeze()


def main():
    prompt_wav = str(Path(sys.argv[1]).resolve())
    tag = sys.argv[2]
    out = OUT_ROOT / tag
    out.mkdir(parents=True, exist_ok=True)

    from tokenizer import StepAudioTokenizer
    from tts import StepAudioTTS
    from model_loader import ModelSource

    models = Path(os.environ["TEMP"]) / "editx-models"
    encoder = StepAudioTokenizer(str(models / "Step-Audio-Tokenizer"), model_source=ModelSource.LOCAL)
    engine = StepAudioTTS(str(models / "Step-Audio-EditX"), encoder, model_source=ModelSource.LOCAL)
    print(f"models loaded; prompt = {prompt_wav}", flush=True)

    import whisper

    asr = whisper.load_model("base.en", device="cuda")

    manifest = []
    for lid, text in LINES:
        takes = []
        for ti in range(1, N_TAKES + 1):
            torch.manual_seed(81000 * lid + ti)
            audio, sr = engine.clone(prompt_wav, PROMPT_TEXT, text)
            y = to_numpy(audio)  # <- written exactly as produced
            path = out / f"line{lid}_take{ti}.wav"
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
                    sample_rate=int(sr),
                    duration_s=round(dur, 3),
                    lex_start_s=round(lex0, 3),
                    lex_end_s=round(lex1, 3),
                    tail_s=round(dur - lex1, 3),
                    wer=round(w, 4),
                    median_f0_hz=round(med, 2),
                    f0_iqr_hz=round(iqr, 2),
                    transcript=hyp,
                )
            )
            print(
                f"  line{lid} take{ti}: {dur:5.2f}s  spoken {lex1 - lex0:4.2f}s  "
                f"tail {dur - lex1:4.2f}s  wer={w:.3f}  F0 {med:.0f} Hz (IQR {iqr:.1f})",
                flush=True,
            )

        # Present the take most representative of THIS narrator, not the
        # best-fitting line: the medoid in (median F0, F0 IQR) among the
        # word-perfect takes. Selecting for fit is what v7 had to undo.
        ok = [t for t in takes if t["wer"] <= 0.05] or takes
        f0s = np.array([t["median_f0_hz"] for t in ok])
        iqrs = np.array([t["f0_iqr_hz"] for t in ok])
        cost = np.abs(f0s - np.median(f0s)) / 2.0 + np.abs(iqrs - np.median(iqrs)) / 8.0
        best = ok[int(np.argmin(cost))]
        # byte copy, not a re-encode: the audition hears the take itself
        shutil.copyfile(best["path"], out / f"line{lid}_audition.wav")
        manifest.append(dict(line=lid, text=text, chosen_take=best["take"], takes=takes))
        print(f"  line{lid} AUDITION take{best['take']}\n", flush=True)

    (out / "manifest.json").write_text(
        json.dumps(dict(prompt_wav=prompt_wav, tag=tag, lines=manifest), indent=2)
    )
    print(f"wrote {out / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
