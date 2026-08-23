"""Deep documentary voice, attempt B: Kokoro-82M preset narrator voices.

am_onyx is Kokoro's deep male voice; am_michael a warmer mid-deep one.
Two speeds each (calm = slightly under 1.0). Same Whisper verification
and F0 measurement so the two attempts can be compared on numbers.
"""
import json, re, sys, difflib, shutil
from pathlib import Path

import numpy as np, torch, soundfile as sf, librosa

OUT = Path(r"C:\Users\<user>\AppData\Local\Temp\temperature-controller-media\kokoro")
OUT.mkdir(parents=True, exist_ok=True)

LINES = [
    (1, "It all begins with a bare board... and an idea precise enough to become real.", 2.23, 6.0, 11.0),
    (2, "A thousandth of a degree... that is the promise written into every trace.", 14.50, 6.0, 10.0),
    (3, "Then, piece by piece, purpose takes form.", 28.70, 4.0, 9.0),
    (4, "Power. Sensing. Control. Every component answers the same demand.", 46.73, 5.5, 9.0),
    (5, "And at its heart — a sentinel, listening for the faintest whisper of heat.", 57.80, 6.0, 9.5),
    (6, "Until the instrument stands complete... ready to master the invisible frontier between heat... and control.", 72.72, 6.5, 9.6),
]

VARIANTS = [
    dict(voice="am_onyx", speed=0.85),
    dict(voice="am_onyx", speed=0.88),
    dict(voice="am_onyx", speed=0.92),
    dict(voice="am_onyx", speed=0.95),
]

def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()

def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs / max(1, len(ref))

def median_f0(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else float("nan")

def trim(y, sr, thresh_db=-40.0, pad_s=0.06):
    intervals = librosa.effects.split(y, top_db=-thresh_db)
    if len(intervals) == 0:
        return y
    a = max(0, intervals[0][0] - int(pad_s * sr))
    b = min(len(y), intervals[-1][1] + int(pad_s * sr))
    return y[a:b]

def main():
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a", device="cuda")
    sr = 24000

    from transformers import pipeline as hf_pipeline
    asr = hf_pipeline("automatic-speech-recognition", model="openai/whisper-base.en", device="cuda")

    manifest = []
    for lid, text, start, tgt, cap in LINES:
        takes = []
        for ti, v in enumerate(VARIANTS, 1):
            chunks = [audio for _, _, audio in pipe(text, voice=v["voice"], speed=v["speed"])]
            y = torch.cat([c if isinstance(c, torch.Tensor) else torch.tensor(c) for c in chunks]).numpy().astype(np.float32)
            y = trim(y, sr)
            dur = len(y) / sr
            path = OUT / f"line{lid}_take{ti}_{v['voice']}.wav"
            sf.write(str(path), y, sr)
            hyp = asr({"raw": y, "sampling_rate": sr})["text"]
            w = wer(norm_words(text), norm_words(hyp))
            f0 = median_f0(y, sr)
            takes.append(dict(take=ti, path=str(path), dur=round(dur, 2), wer=round(w, 3),
                              f0=round(f0, 1), hyp=hyp.strip(), **v))
            print(f"line{lid} take{ti}: {dur:.2f}s wer={w:.3f} f0={f0:.0f}Hz {v}", flush=True)

        ok = [t for t in takes if t["wer"] <= 0.05 and t["dur"] <= cap]
        pool = ok if ok else [t for t in takes if t["dur"] <= cap] or takes
        pool.sort(key=lambda t: (abs(t["dur"] - tgt), -t["dur"]))
        best = pool[0]
        shutil.copyfile(best["path"], OUT / f"line{lid}_best.wav")
        manifest.append(dict(line=lid, text=text, start=start, chosen=best, takes=takes))
        print(f"line{lid} CHOSEN take{best['take']} ({best['voice']}, {best['dur']}s, f0={best['f0']}Hz)", flush=True)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    sys.exit(main())
