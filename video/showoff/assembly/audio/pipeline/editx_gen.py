"""Step-Audio-EditX narration: clone the deep onyx voice, then add
model-generated breaths where the script breathes.

Loads the 3B model once. Per line: 4 clone takes (different seeds),
Whisper-verified, best picked by duration fit. Lines with '...' then get
one paralinguistic edit pass inserting [breath] at those boundaries —
kept only if it still verifies and fits the slot; otherwise the plain
clone ships. Everything written to editx/ with a mix_final-compatible
manifest.
"""
import json, re, sys, difflib, shutil, os
from pathlib import Path

os.environ["PATH"] += os.pathsep + r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"

IMPL = Path(os.environ["TEMP"]) / "editx-node" / "step_audio_impl"
os.chdir(IMPL)
sys.path.insert(0, str(IMPL))

import numpy as np, torch, librosa, soundfile as sf

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
OUT = MEDIA / "editx"
OUT.mkdir(parents=True, exist_ok=True)

PROMPT_WAV = str(MEDIA / "onyx_prompt.wav")
PROMPT_TEXT = ("In the beginning, there was only silence. Then, from the silence, an instrument was born. "
               "Patient, precise, and calm beyond measure, it waited for its purpose.")

LINES = [
    (1, "It all begins with a bare board... and an idea precise enough to become real.", 2.23, 6.0, 11.0),
    (2, "A thousandth of a degree... that is the promise written into every trace.", 14.50, 6.0, 10.0),
    (3, "Then, piece by piece, purpose takes form.", 28.70, 4.0, 9.0),
    (4, "Power. Sensing. Control. Every component answers the same demand.", 46.73, 5.5, 9.0),
    (5, "And at its heart — a sentinel, listening for the faintest whisper of heat.", 57.80, 6.0, 9.5),
    (6, "Until the instrument stands complete... ready to master the invisible frontier between heat... and control.", 72.72, 6.5, 9.6),
]
N_TAKES = 4

def breath_text(text):
    # a breath where the script already pauses
    return text.replace("... ", "... [breath] ")

def norm_words(s):
    s = re.sub(r"\[.*?\]", " ", s)
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()

def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs / max(1, len(ref))

def trim(y, sr, pad_s=0.06):
    iv = librosa.effects.split(y, top_db=40)
    if len(iv) == 0:
        return y
    a = max(0, iv[0][0] - int(pad_s * sr))
    b = min(len(y), iv[-1][1] + int(pad_s * sr))
    return y[a:b]

def median_f0(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else float("nan")

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
    print("models loaded", flush=True)

    import whisper
    asr = whisper.load_model("base.en", device="cuda")
    def transcribe(path):
        return asr.transcribe(str(path), language="en")["text"].strip()

    manifest = []
    for lid, text, start, tgt, cap in LINES:
        takes = []
        for ti in range(1, N_TAKES + 1):
            torch.manual_seed(31000 * lid + ti)
            audio, sr = engine.clone(PROMPT_WAV, PROMPT_TEXT, text)
            y = trim(to_numpy(audio), sr)
            dur = len(y) / sr
            path = OUT / f"line{lid}_take{ti}.wav"
            sf.write(str(path), y, sr)
            hyp = transcribe(path)
            w = wer(norm_words(text), norm_words(hyp))
            f0 = median_f0(y, sr)
            takes.append(dict(take=ti, kind="clone", path=str(path), dur=round(dur, 2),
                              wer=round(w, 3), f0=round(f0, 1), hyp=hyp))
            print(f"line{lid} take{ti}: {dur:.2f}s wer={w:.3f} f0={f0:.0f}Hz :: {hyp!r}", flush=True)

        ok = [t for t in takes if t["wer"] <= 0.05 and t["dur"] <= cap]
        pool = ok if ok else [t for t in takes if t["dur"] <= cap] or takes
        pool.sort(key=lambda t: (abs(t["dur"] - tgt), -t["dur"]))
        best = dict(pool[0])

        if "..." in text:
            try:
                torch.manual_seed(61000 + lid)
                audio, sr = engine.edit(best["path"], text, "paralinguistic", "", breath_text(text))
                y = trim(to_numpy(audio), sr)
                dur = len(y) / sr
                bpath = OUT / f"line{lid}_breath.wav"
                sf.write(str(bpath), y, sr)
                hyp = transcribe(bpath)
                w = wer(norm_words(text), norm_words(hyp))
                f0 = median_f0(y, sr)
                print(f"line{lid} breath: {dur:.2f}s wer={w:.3f} f0={f0:.0f}Hz :: {hyp!r}", flush=True)
                if w <= 0.08 and dur <= cap:
                    best = dict(take="breath", kind="breath-edit", path=str(bpath), dur=round(dur, 2),
                                wer=round(w, 3), f0=round(f0, 1), hyp=hyp)
                else:
                    print(f"line{lid} breath REJECTED (wer or cap), keeping plain clone", flush=True)
            except Exception as e:
                print(f"line{lid} breath edit failed: {e} — keeping plain clone", flush=True)

        shutil.copyfile(best["path"], OUT / f"line{lid}_best.wav")
        manifest.append(dict(line=lid, text=text, start=start, chosen=best, takes=takes))
        print(f"line{lid} CHOSEN {best['kind']} take={best['take']} ({best['dur']}s, f0={best['f0']}Hz)", flush=True)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
