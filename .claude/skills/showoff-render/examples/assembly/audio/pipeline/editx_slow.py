"""Calmer/slower pass: EditX 'speed: slower' edit on each chosen line.

Model-generated retiming (not a time-stretch). Gates: words unchanged,
duration within the (slower) slot cap, F0 still deep. A line failing
gates keeps its current take. Originals preserved as line{N}_fast.wav.
"""
import os, json, re, difflib, shutil, sys
from pathlib import Path

os.environ["PATH"] += os.pathsep + r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"

IMPL = Path(os.environ["TEMP"]) / "editx-node" / "step_audio_impl"
os.chdir(IMPL)
sys.path.insert(0, str(IMPL))

import numpy as np, torch, librosa, soundfile as sf

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
SRC = MEDIA / "editx"

# caps against the *shifted* starts (2.85/14.5/28.7/47.25/57.8/72.95);
# line 6 must still end by ~82.5 s
CAPS = {1: 10.0, 2: 10.5, 3: 9.0, 4: 9.5, 5: 9.5, 6: 8.2}

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

def median_f0(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else float("nan")

def to_numpy(a):
    if isinstance(a, torch.Tensor):
        a = a.cpu().numpy()
    return np.asarray(a, dtype=np.float32).squeeze()

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

    manifest = json.loads((SRC / "manifest.json").read_text())
    for line in manifest:
        lid = line["line"]
        best = SRC / f"line{lid}_best.wav"
        fast = SRC / f"line{lid}_fast.wav"
        if not fast.exists():
            shutil.copyfile(best, fast)
        y0, sr0 = librosa.load(str(fast), sr=None)
        dur0 = len(y0) / sr0

        torch.manual_seed(97000 + lid)
        audio, sr = engine.edit(str(fast), line["text"], "speed", "slower", line["text"])
        y = trim(to_numpy(audio), sr)
        dur = len(y) / sr
        cand = SRC / f"line{lid}_slow.wav"
        sf.write(str(cand), y, sr)
        hyp = asr.transcribe(str(cand), language="en")["text"].strip()
        w = wer(norm_words(line["text"]), norm_words(hyp))
        f0 = median_f0(y, sr)
        print(f"line{lid} slow: {dur0:.2f}->{dur:.2f}s wer={w:.3f} f0={f0:.0f}Hz :: {hyp!r}", flush=True)

        if w <= 0.05 and dur <= CAPS[lid] and dur >= dur0 * 1.02 and 70 <= f0 <= 105:
            shutil.copyfile(cand, best)
            line["chosen"] = dict(take="slow", kind="speed-edit", path=str(cand), dur=round(dur, 2),
                                  wer=round(w, 3), f0=round(f0, 1), hyp=hyp)
            print(f"line{lid} ACCEPTED slower take", flush=True)
        else:
            print(f"line{lid} slower take REJECTED (gates) — keeping previous", flush=True)

    (SRC / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
