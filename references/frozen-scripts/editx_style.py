"""Generic EditX edit pass over a takes dir.

Usage: editx_style.py <src_dir> <out_dir> <edit_type> <edit_info>
e.g.   editx_style.py editx editx_story style story
       editx_style.py editx_slow_takes editx_gentle style gentle

Reads line{N}_fast.wav if present (pre-slow originals) unless src dir's
best files are wanted; edits each with the given style, gates on WER,
slot cap, and F0, falls back to the source take on failure. Writes a
mix_final-compatible dir (line{N}_best.wav + manifest.json).
"""
import os, json, re, difflib, shutil, sys
from pathlib import Path

os.environ["PATH"] += os.pathsep + r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"

IMPL = Path(os.environ["TEMP"]) / "editx-node" / "step_audio_impl"
os.chdir(IMPL)
sys.path.insert(0, str(IMPL))

import numpy as np, torch, librosa, soundfile as sf

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
SRC = MEDIA / sys.argv[1]
OUT = MEDIA / sys.argv[2]
EDIT_TYPE, EDIT_INFO = sys.argv[3], sys.argv[4]
OUT.mkdir(parents=True, exist_ok=True)

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
        src = SRC / f"line{lid}_best.wav"

        torch.manual_seed(113000 + lid)
        audio, sr = engine.edit(str(src), line["text"], EDIT_TYPE, EDIT_INFO, line["text"])
        y = trim(to_numpy(audio), sr)
        dur = len(y) / sr
        dst = OUT / f"line{lid}_best.wav"
        sf.write(str(dst), y, sr)
        hyp = asr.transcribe(str(dst), language="en")["text"].strip()
        w = wer(norm_words(line["text"]), norm_words(hyp))
        f0 = median_f0(y, sr)
        print(f"line{lid} {EDIT_INFO}: {dur:.2f}s wer={w:.3f} f0={f0:.0f}Hz :: {hyp!r}", flush=True)

        if w <= 0.05 and dur <= CAPS[lid] and 70 <= f0 <= 105:
            line["chosen"] = dict(take=EDIT_INFO, kind=f"{EDIT_TYPE}-edit", path=str(dst),
                                  dur=round(dur, 2), wer=round(w, 3), f0=round(f0, 1), hyp=hyp)
            print(f"line{lid} ACCEPTED", flush=True)
        else:
            print(f"line{lid} REJECTED (gates) — falling back to source take", flush=True)
            shutil.copyfile(src, dst)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
