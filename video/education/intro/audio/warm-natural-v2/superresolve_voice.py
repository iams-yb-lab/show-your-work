"""Restore the approved 24 kHz voice clips to 48 kHz with strict fallback gates."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

FFBIN = (r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
         r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin")
FFMPEG = str(Path(FFBIN) / "ffmpeg.exe")
os.environ["PATH"] += os.pathsep + FFBIN

import librosa
import numpy as np
import soundfile as sf


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def norm_words(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    text = re.sub(r"\b22\s*k\b", "twenty two k", text)
    aliases = {
        r"\bpid\b": "p i d", r"\bpwm\b": "p w m", r"\bad\b": "a d",
        r"\bad7124\b": "a d seven one two four", r"\bii\b": "two",
        r"\b1968\b": "nineteen sixty eight", r"\b7124\b": "seven one two four",
    }
    for pattern, replacement in aliases.items():
        text = re.sub(pattern, replacement, text)
    text = text.replace("set point", "setpoint")
    text = text.replace("ratio metric", "ratiometric").replace("ratio-metric", "ratiometric")
    text = text.replace("thermo electric", "thermoelectric").replace("thermo-electric", "thermoelectric")
    text = text.replace("milli kelvin", "millikelvin").replace("milli-kelvin", "millikelvin")
    text = text.replace("ther miss ter", "thermistor").replace("ther-miss-ter", "thermistor")
    numbers = {
        "24": "twenty four", "22": "twenty two", "25": "twenty five", "8": "eight",
        "4.1": "four point one", "2.5": "two point five", "0.21": "zero point two one",
        "50": "fifty", "44": "forty four", "1": "one", "2": "two", "3": "three",
        "4": "four",
    }
    for old, new in numbers.items():
        text = re.sub(rf"(?<![\w.]){re.escape(old)}(?![\w.])", new, text)
    return re.sub(r"[^a-z0-9' ]+", " ", text).split()


def wer(reference: str, hypothesis: str) -> float:
    expected, observed = norm_words(reference), norm_words(hypothesis)
    matcher = difflib.SequenceMatcher(a=expected, b=observed)
    errors = sum(
        max(i2 - i1, j2 - j1)
        for operation, i1, i2, j1, j2 in matcher.get_opcodes()
        if operation != "equal"
    )
    return errors / max(1, len(expected))


def median_f0(audio: np.ndarray, sample_rate: int) -> float:
    f0, _, _ = librosa.pyin(audio, fmin=50, fmax=300, sr=sample_rate)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else 999.0


def high_frequency_ratio(audio: np.ndarray, sample_rate: int) -> float:
    power = np.abs(np.fft.rfft(audio)) ** 2
    frequency = np.fft.rfftfreq(len(audio), 1 / sample_rate)
    return float(power[frequency >= 12_000].sum() / max(power.sum(), 1e-12))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args()
    source_dir, out = args.src.resolve(), args.out.resolve()
    checkpoint = args.checkpoint.resolve()
    out.mkdir(parents=True, exist_ok=True)

    from clearvoice import ClearVoice
    import whisper

    enhancer = ClearVoice(task="speech_super_resolution", model_names=["MossFormer2_SR_48K"])
    asr = whisper.load_model("base.en", device="cuda")
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    report: list[dict] = []

    for entry in manifest:
        line_id = entry["line"]
        source = source_dir / f"line{line_id:02d}_best.wav"
        target = out / f"line{line_id:02d}_best.wav"
        result = enhancer(input_path=str(source), online_write=False)
        restored = np.asarray(result, dtype=np.float32).squeeze()
        sf.write(target, restored, 48_000, subtype="PCM_24")

        original, original_rate = librosa.load(source, sr=None, mono=True)
        before_duration = len(original) / original_rate
        after_duration = len(restored) / 48_000
        f0_before = median_f0(original, original_rate)
        f0_after = median_f0(restored, 48_000)
        hypothesis = asr.transcribe(str(target), language="en", fp16=True)["text"].strip()
        accuracy = wer(entry["spoken"], hypothesis)
        hf_ratio = high_frequency_ratio(restored, 48_000)
        accepted = (
            accuracy <= 0.12
            and abs(after_duration - before_duration) <= before_duration * 0.012 + 0.05
            and abs(f0_after - f0_before) <= 5.0
            and hf_ratio > 1e-7
        )
        if not accepted:
            # Restoration is optional; the approved performance is not.
            subprocess.run(
                [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
                 "-ar", "48000", "-c:a", "pcm_s24le", str(target)],
                check=True,
            )
        row = {
            "line": line_id,
            "duration_before": before_duration,
            "duration_after": after_duration,
            "wer": accuracy,
            "f0_before": f0_before,
            "f0_after": f0_after,
            "high_frequency_ratio": hf_ratio,
            "restoration_accepted": accepted,
            "hypothesis": hypothesis,
            "output_sha256": sha256(target),
        }
        report.append(row)
        print(
            f"cue {line_id:02d}: {'restored' if accepted else 'clean resample fallback'}; "
            f"WER={accuracy:.3f}; F0={f0_before:.1f}->{f0_after:.1f}",
            flush=True,
        )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out / "sr-report.json").write_text(
        json.dumps({
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": sha256(checkpoint),
            "restored": sum(item["restoration_accepted"] for item in report),
            "fallback": sum(not item["restoration_accepted"] for item in report),
            "lines": report,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"DONE: {sum(item['restoration_accepted'] for item in report)}/49 restored", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
