"""Surgical re-take of line 1 only: same voice, unhurried read.

8 fresh clone takes, gated to the approved narrator (WER 0, median F0
82-86.5 Hz, F0 IQR <= 14) and to an unhurried delivery (duration 4.8-7.5 s
pre-stretch). Among survivors: longest internal pause at the ellipsis wins,
duration ~5.4 s breaks ties. Winner replaces editx_consistent/line1_best.wav
(old one kept as line1_best_v71.wav).
"""
import os, sys, re, difflib, shutil
from pathlib import Path

os.environ["PATH"] += os.pathsep + r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"

IMPL = Path(os.environ["TEMP"]) / "editx-node" / "step_audio_impl"
os.chdir(IMPL)
sys.path.insert(0, str(IMPL))

import numpy as np, torch, librosa, soundfile as sf

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
OUT = MEDIA / "editx_line1"
OUT.mkdir(exist_ok=True)

TEXT = "It all begins with a bare board... and an idea precise enough to become real."
PROMPT_WAV = str(MEDIA / "onyx_prompt.wav")
PROMPT_TEXT = ("In the beginning, there was only silence. Then, from the silence, an instrument was born. "
               "Patient, precise, and calm beyond measure, it waited for its purpose.")

def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()

def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs / max(1, len(ref))

def trim(y, sr, pad_s=0.06):
    iv = librosa.effects.split(y, top_db=40)
    if len(iv) == 0:
        return y
    return y[max(0, iv[0][0] - int(pad_s * sr)): min(len(y), iv[-1][1] + int(pad_s * sr))]

def features(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    iv = librosa.effects.split(y, top_db=35)
    gaps = [(iv[i + 1][0] - iv[i][1]) / sr for i in range(len(iv) - 1)] or [0.0]
    return float(np.median(f0)), float(np.percentile(f0, 75) - np.percentile(f0, 25)), max(gaps)

def main():
    from tokenizer import StepAudioTokenizer
    from tts import StepAudioTTS
    from model_loader import ModelSource
    models = Path(os.environ["TEMP"]) / "editx-models"
    encoder = StepAudioTokenizer(str(models / "Step-Audio-Tokenizer"), model_source=ModelSource.LOCAL)
    engine = StepAudioTTS(str(models / "Step-Audio-EditX"), encoder, model_source=ModelSource.LOCAL)
    import whisper
    asr = whisper.load_model("base.en", device="cuda")
    print("models loaded", flush=True)

    cands = []
    for ti in range(1, 9):
        torch.manual_seed(500000 + 17 * ti)
        audio, sr = engine.clone(PROMPT_WAV, PROMPT_TEXT, TEXT)
        y = trim(np.asarray(audio.cpu().numpy() if isinstance(audio, torch.Tensor) else audio,
                            dtype=np.float32).squeeze(), sr)
        dur = len(y) / sr
        path = OUT / f"take{ti}.wav"
        sf.write(str(path), y, sr)
        hyp = asr.transcribe(str(path), language="en")["text"].strip()
        w = wer(norm_words(TEXT), norm_words(hyp))
        f0m, iqr, pause = features(y, sr)
        ok = w == 0.0 and 82.0 <= f0m <= 86.5 and iqr <= 14.0 and 4.8 <= dur <= 7.5
        cands.append(dict(take=ti, path=path, dur=dur, wer=w, f0=f0m, iqr=iqr, pause=pause, ok=ok))
        print(f"take{ti}: {dur:.2f}s wer={w:.3f} f0={f0m:.1f}Hz iqr={iqr:.1f} "
              f"pause={pause*1000:.0f}ms {'OK' if ok else 'rejected'}", flush=True)

    pool = [c for c in cands if c["ok"]]
    if not pool:
        print("NO TAKE SURVIVED THE GATES — nothing replaced", flush=True)
        sys.exit(1)
    pool.sort(key=lambda c: (-round(c["pause"], 1), abs(c["dur"] - 5.4)))
    best = pool[0]
    print(f"CHOSEN take{best['take']}: {best['dur']:.2f}s f0={best['f0']:.1f}Hz "
          f"pause={best['pause']*1000:.0f}ms", flush=True)

    dst = MEDIA / "editx_consistent" / "line1_best.wav"
    shutil.copyfile(dst, MEDIA / "editx_consistent" / "line1_best_v71.wav")
    shutil.copyfile(best["path"], dst)
    print("replaced editx_consistent/line1_best.wav", flush=True)

if __name__ == "__main__":
    main()
