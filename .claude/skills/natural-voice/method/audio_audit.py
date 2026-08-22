"""Measure voice files without modifying them.

The report is evidence, not an automatic naturalness score. It makes prompt, raw, restored and
mixed variants comparable while the listening verdict remains human.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dbfs(value: float) -> float:
    return 20.0 * np.log10(max(value, 1e-12))


def measure(path: Path) -> dict:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    f0, _, _ = librosa.pyin(mono, fmin=50, fmax=350, sr=sample_rate)
    voiced_f0 = f0[~np.isnan(f0)]

    spectrum = np.abs(np.fft.rfft(mono.astype(np.float64))) ** 2
    frequency = np.fft.rfftfreq(len(mono), 1.0 / sample_rate)
    total_power = max(float(spectrum.sum()), 1e-18)

    channels = audio.shape[1]
    correlation = None
    if channels == 2:
        correlation = float(np.corrcoef(audio[:, 0], audio[:, 1])[0, 1])

    # Tail measurements are descriptive only. They must never be used as an automatic cut point.
    frame_length = max(1, round(0.020 * sample_rate))
    usable = len(mono) // frame_length * frame_length
    frame_rms = np.sqrt(np.mean(mono[:usable].reshape(-1, frame_length) ** 2, axis=1)) if usable else np.array([])
    active = np.flatnonzero(frame_rms >= 10 ** (-50.0 / 20.0))
    trailing_below_minus_50 = (
        (len(frame_rms) - 1 - active[-1]) * frame_length / sample_rate if active.size else len(mono) / sample_rate
    )

    return {
        "path": str(path),
        "sha256": sha256(path),
        "sample_rate": sample_rate,
        "channels": channels,
        "duration_seconds": len(audio) / sample_rate,
        "peak_dbfs": dbfs(peak),
        "rms_dbfs": dbfs(rms),
        "dc_offset": float(np.mean(mono)),
        "median_f0_hz": float(np.median(voiced_f0)) if voiced_f0.size else None,
        "f0_iqr_hz": (
            float(np.percentile(voiced_f0, 75) - np.percentile(voiced_f0, 25))
            if voiced_f0.size else None
        ),
        "power_ratio_above_8000_hz": float(spectrum[frequency >= 8000].sum() / total_power),
        "power_ratio_above_12000_hz": float(spectrum[frequency >= 12000].sum() / total_power),
        "stereo_correlation": correlation,
        "trailing_seconds_below_minus_50_dbfs": trailing_below_minus_50,
        "warning": "No metric here is a naturalness score; use loudness-matched listening gates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = [measure(path.resolve()) for path in args.files]
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.resolve().write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
