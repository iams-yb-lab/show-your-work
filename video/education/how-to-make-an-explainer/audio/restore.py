#!/usr/bin/env python3
"""
restore.py — 24 → 48 kHz on the selected takes, with the four gates. Runs in sr-venv.

Chatterbox tops out at 12 kHz of real bandwidth, and that missing octave is the single loudest tell
this project ever found: it reads as a noise-cancelling headset even when the performance is fine.
Restoration is how that is fixed, and it is **optional per section** — the performance is not.

A section keeps its restored version only if all four gates pass:

  words           transcript WER <= 0.12 against what the model was sent
  duration        change <= 1.2 % + 50 ms
  pitch           median F0 change <= 5 Hz
  bandwidth       measurable energy above 12 kHz

Anything else falls back to a clean resample of the same performance. Output is 32-bit float, because
a restored file can sit above full scale and level belongs to delivery.

    python3 audio/restore.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

FFBIN = (r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
         r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin")
if Path(FFBIN).is_dir():
    os.environ["PATH"] += os.pathsep + FFBIN

import librosa  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

AUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIO))


def video_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "engine").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree")


VIDEO = video_root(AUDIO)
WORK = VIDEO / "out/education/how-to-make-an-explainer"
GATES = {"wer": 0.12, "duration_fraction": 0.012, "duration_pad_s": 0.05,
         "f0_hz": 5.0, "hf_ratio": 1e-7}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def norm(text: str) -> list[str]:
    return [w for w in (re.sub(r"[^a-z0-9]", "", t.lower()) for t in text.split()) if w]


def wer(reference: str, hypothesis: str) -> float:
    import difflib
    ref, hyp = norm(reference), norm(hypothesis)
    matcher = difflib.SequenceMatcher(a=ref, b=hyp)
    errors = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in matcher.get_opcodes()
                 if op != "equal")
    return errors / max(1, len(ref))


def median_f0(y: np.ndarray, sr: int) -> float:
    f0, _, _ = librosa.pyin(y, fmin=60, fmax=350, sr=sr)
    f0 = f0[np.isfinite(f0)]
    return float(np.median(f0)) if f0.size else float("nan")


def hf_ratio(y: np.ndarray, sr: int) -> float:
    power = np.abs(np.fft.rfft(y)) ** 2
    freq = np.fft.rfftfreq(len(y), 1 / sr)
    return float(power[freq >= 12_000].sum() / max(power.sum(), 1e-12))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=WORK / "restored")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    generation = json.loads((WORK / "generation.json").read_text(encoding="utf-8"))
    qa = json.loads((WORK / "takes-qa.json").read_text(encoding="utf-8"))
    takes = {(t["section"], t["take"]): t for t in generation["takes"]}

    from clearvoice import ClearVoice
    import whisper

    enhancer = ClearVoice(task="speech_super_resolution", model_names=["MossFormer2_SR_48K"])
    asr = whisper.load_model("base.en", device="cuda")

    report = []
    for section, take_no in sorted(qa["selected"].items()):
        take = takes[(section, take_no)]
        source = Path(take["path"])
        target = args.out / f"{section}.wav"

        original, original_sr = librosa.load(source, sr=None, mono=True)
        clean = librosa.resample(original, orig_sr=original_sr, target_sr=48_000)

        result = enhancer(input_path=str(source), online_write=False)
        restored = np.asarray(result, dtype=np.float32).squeeze()
        if np.max(np.abs(restored)) > 0:
            # ClearVoice returns its own scale; match it back to the performance it came from so the
            # gates compare like with like and nothing is quietly made louder.
            restored *= float(np.max(np.abs(original))) / float(np.max(np.abs(restored)))

        before, after = len(original) / original_sr, len(restored) / 48_000
        heard = None
        probe = args.out / f"_probe_{section}.wav"
        sf.write(probe, restored / max(1.0, float(np.max(np.abs(restored)))), 48_000, subtype="FLOAT")
        heard = asr.transcribe(str(probe), language="en", fp16=True,
                              condition_on_previous_text=False)["text"].strip()
        probe.unlink(missing_ok=True)

        f0_before, f0_after = median_f0(original, original_sr), median_f0(restored, 48_000)
        checks = {
            "wer": round(wer(take["said"], heard), 4),
            "duration_change_s": round(abs(after - before), 4),
            "duration_allowance_s": round(before * GATES["duration_fraction"] + GATES["duration_pad_s"], 4),
            "f0_change_hz": round(abs(f0_after - f0_before), 2),
            "hf_ratio": hf_ratio(restored, 48_000),
        }
        accepted = (checks["wer"] <= GATES["wer"]
                    and checks["duration_change_s"] <= checks["duration_allowance_s"]
                    and checks["f0_change_hz"] <= GATES["f0_hz"]
                    and checks["hf_ratio"] > GATES["hf_ratio"])

        chosen = restored if accepted else clean
        sf.write(target, chosen, 48_000, subtype="FLOAT")
        row = {
            "section": section, "take": take_no, "source": str(source), "path": str(target),
            "restoration_accepted": bool(accepted), "checks": checks,
            "duration_before_s": round(before, 3), "duration_after_s": round(len(chosen) / 48_000, 3),
            "f0_before_hz": round(f0_before, 2), "f0_after_hz": round(f0_after, 2),
            "peak": round(float(np.max(np.abs(chosen))), 4),
            "hf_ratio_delivered": hf_ratio(chosen, 48_000),
            "transcript": heard, "sha256": sha256(target),
        }
        report.append(row)
        print(f"  [{section}] {'restored ' if accepted else 'resampled'}  "
              f"WER {checks['wer']:.3f}  ΔF0 {checks['f0_change_hz']:4.1f} Hz  "
              f"Δt {checks['duration_change_s']:.3f}/{checks['duration_allowance_s']:.3f} s  "
              f">12 kHz {row['hf_ratio_delivered']:.2e}", flush=True)

    out = {
        "aimed_at": "one selected take per section, 24 kHz in, 48 kHz out",
        "gates": GATES,
        "restored": sum(r["restoration_accepted"] for r in report),
        "fallback": sum(not r["restoration_accepted"] for r in report),
        "sections": report,
    }
    path = WORK / "restore.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{out['restored']} restored, {out['fallback']} clean resample; record: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
