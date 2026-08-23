"""Deep documentary voice, attempt A: Chatterbox voice-cloned onto a
deep synthetic reference.

The reference is Chatterbox's own default voice pitch-shifted down —
no real person's voice is involved. Chatterbox extracts a speaker
embedding from it, so the artifacts of the shift don't transfer; the
depth does. Same take grid + Whisper verification as before.
"""
import json, re, sys, difflib, shutil
from pathlib import Path

import numpy as np, torch, torchaudio, librosa, soundfile as sf

OUT = Path(r"C:\Users\<user>\AppData\Local\Temp\temperature-controller-media\chatterbox_deep")
OUT.mkdir(parents=True, exist_ok=True)
SRC = Path(r"C:\Users\<user>\AppData\Local\Temp\temperature-controller-media\chatterbox")

LINES = [
    (1, "It all begins with a bare board... and an idea precise enough to become real.", 2.23, 6.0, 12.0),
    (2, "Then, piece by piece, purpose takes form.", 28.70, 4.0, 9.0),
    (3, "Power. Sensing. Control. Every component answers the same demand.", 46.73, 8.5, 14.0),
    (4, "Until the instrument stands complete... ready to master the invisible frontier between heat... and control.", 72.72, 8.5, 9.6),
]

PARAM_GRID = [
    dict(exaggeration=0.4, cfg_weight=0.3),
    dict(exaggeration=0.5, cfg_weight=0.3),
    dict(exaggeration=0.5, cfg_weight=0.4),
    dict(exaggeration=0.6, cfg_weight=0.3),
]

def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()

def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs / max(1, len(ref))

def trim(wav, sr, thresh_db=-40.0, pad_s=0.06):
    x = wav.squeeze(0)
    k = int(sr * 0.02)
    env = torch.nn.functional.max_pool1d(x.abs().view(1, 1, -1), k, stride=1, padding=k // 2).view(-1)[: x.numel()]
    idx = (env > 10 ** (thresh_db / 20) * env.max()).nonzero()
    if idx.numel() == 0:
        return wav
    a = max(0, int(idx[0]) - int(pad_s * sr))
    b = min(x.numel(), int(idx[-1]) + int(pad_s * sr))
    return x[a:b].unsqueeze(0)

def median_f0(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else float("nan")

def main():
    # build the deep reference from existing default-voice takes
    ref_path = OUT / "deep_reference.wav"
    parts = []
    for f in ["line1_best.wav", "line4_best.wav"]:
        y, sr = librosa.load(str(SRC / f), sr=24000)
        parts.append(y)
    y = np.concatenate(parts)
    print(f"default voice median F0: {median_f0(y, 24000):.1f} Hz", flush=True)
    deep = librosa.effects.pitch_shift(y, sr=24000, n_steps=-3.5)
    sf.write(str(ref_path), deep, 24000)
    print(f"reference median F0 after shift: {median_f0(deep, 24000):.1f} Hz", flush=True)

    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device="cuda")
    sr = model.sr

    from transformers import pipeline
    asr = pipeline("automatic-speech-recognition", model="openai/whisper-base.en", device="cuda")

    manifest = []
    for lid, text, start, tgt, cap in LINES:
        takes = []
        for ti, params in enumerate(PARAM_GRID, 1):
            torch.manual_seed(7000 * lid + ti)
            wav = model.generate(text, audio_prompt_path=str(ref_path), **params)
            wav = trim(wav.cpu(), sr)
            dur = wav.shape[-1] / sr
            path = OUT / f"line{lid}_take{ti}.wav"
            torchaudio.save(str(path), wav, sr)
            hyp = asr({"raw": wav.squeeze(0).numpy(), "sampling_rate": sr})["text"]
            w = wer(norm_words(text), norm_words(hyp))
            f0 = median_f0(wav.squeeze(0).numpy(), sr)
            takes.append(dict(take=ti, path=str(path), dur=round(dur, 2), wer=round(w, 3),
                              f0=round(f0, 1), hyp=hyp.strip(), **params))
            print(f"line{lid} take{ti}: {dur:.2f}s wer={w:.3f} f0={f0:.0f}Hz {params}", flush=True)

        ok = [t for t in takes if t["wer"] <= 0.05 and t["dur"] <= cap]
        pool = ok if ok else [t for t in takes if t["dur"] <= cap] or takes
        pool.sort(key=lambda t: (abs(t["dur"] - tgt), -t["dur"]))
        best = pool[0]
        shutil.copyfile(best["path"], OUT / f"line{lid}_best.wav")
        manifest.append(dict(line=lid, text=text, start=start, chosen=best, takes=takes))
        print(f"line{lid} CHOSEN take{best['take']} ({best['dur']}s, f0={best['f0']}Hz)", flush=True)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    sys.exit(main())
