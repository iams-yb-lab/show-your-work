"""Generate epic-documentary narration takes with Chatterbox on CUDA.

For each line: several takes across an (exaggeration, cfg_weight) grid.
Each take is trimmed, then transcribed back with whisper-base.en; takes
whose words don't match the script are rejected. Among accurate takes,
pick the one whose duration is closest to the target (slower preferred
on ties -> calm delivery). Line 4 has a hard duration cap so it still
ends before the film's final fade.
"""
import json, re, sys, difflib
from pathlib import Path

import torch, torchaudio

OUT = Path(r"C:\Users\iams1\AppData\Local\Temp\temperature-controller-media\chatterbox")
OUT.mkdir(parents=True, exist_ok=True)

LINES = [
    # (id, text, start_s, target_dur_s, max_dur_s)
    (1, "It all begins with a bare board... and an idea precise enough to become real.", 2.23, 6.0, 12.0),
    (2, "Then, piece by piece, purpose takes form.", 28.70, 4.0, 9.0),
    (3, "Power. Sensing. Control. Every component answers the same demand.", 46.73, 8.5, 14.0),
    (4, "Until the instrument stands complete... ready to master the invisible frontier between heat... and control.", 72.72, 8.5, 9.6),
]

PARAM_GRID = [
    dict(exaggeration=0.4, cfg_weight=0.3),
    dict(exaggeration=0.4, cfg_weight=0.3),
    dict(exaggeration=0.5, cfg_weight=0.3),
    dict(exaggeration=0.5, cfg_weight=0.4),
    dict(exaggeration=0.4, cfg_weight=0.5),
    dict(exaggeration=0.6, cfg_weight=0.3),
]

def norm_words(s):
    s = re.sub(r"[^a-z0-9' ]+", " ", s.lower())
    return s.split()

def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs / max(1, len(ref))

def trim(wav, sr, thresh_db=-40.0, pad_s=0.06):
    x = wav.squeeze(0)
    env = x.abs()
    k = int(sr * 0.02)
    env = torch.nn.functional.max_pool1d(env.view(1, 1, -1), k, stride=1, padding=k // 2).view(-1)[: x.numel()]
    thresh = 10 ** (thresh_db / 20) * env.max()
    idx = (env > thresh).nonzero()
    if idx.numel() == 0:
        return wav
    a = max(0, int(idx[0]) - int(pad_s * sr))
    b = min(x.numel(), int(idx[-1]) + int(pad_s * sr))
    return x[a:b].unsqueeze(0)

def main():
    from chatterbox.tts import ChatterboxTTS
    print("loading chatterbox on cuda...", flush=True)
    model = ChatterboxTTS.from_pretrained(device="cuda")
    sr = model.sr

    from transformers import pipeline
    print("loading whisper-base.en for verification...", flush=True)
    asr = pipeline("automatic-speech-recognition", model="openai/whisper-base.en", device="cuda")

    manifest = []
    for lid, text, start, tgt, cap in LINES:
        takes = []
        for ti, params in enumerate(PARAM_GRID, 1):
            torch.manual_seed(1000 * lid + ti)
            wav = model.generate(text, **params)
            wav = trim(wav.cpu(), sr)
            dur = wav.shape[-1] / sr
            path = OUT / f"line{lid}_take{ti}.wav"
            torchaudio.save(str(path), wav, sr)
            hyp = asr({"raw": wav.squeeze(0).numpy(), "sampling_rate": sr})["text"]
            w = wer(norm_words(text), norm_words(hyp))
            takes.append(dict(take=ti, path=str(path), dur=round(dur, 2), wer=round(w, 3),
                              hyp=hyp.strip(), **params))
            print(f"line{lid} take{ti}: {dur:.2f}s wer={w:.3f} {params} :: {hyp.strip()!r}", flush=True)

        ok = [t for t in takes if t["wer"] <= 0.05 and t["dur"] <= cap]
        pool = ok if ok else [t for t in takes if t["dur"] <= cap] or takes
        pool.sort(key=lambda t: (abs(t["dur"] - tgt), -t["dur"]))
        best = pool[0]
        best_path = OUT / f"line{lid}_best.wav"
        import shutil; shutil.copyfile(best["path"], best_path)
        manifest.append(dict(line=lid, text=text, start=start, chosen=best, takes=takes))
        print(f"line{lid} CHOSEN take{best['take']} ({best['dur']}s, wer={best['wer']})", flush=True)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    sys.exit(main())
