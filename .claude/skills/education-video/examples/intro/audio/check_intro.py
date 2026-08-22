"""Measure a finished intro-film mix back out of the audio, against the film's own schedule.

    python video/tools/check_intro.py --wav video/out/audio/score.wav

The mixer places everything from a timecode, so checking it against the same timecodes proves
nothing. What can be checked is whether the finished audio actually contains what the schedule
says, using instruments that never saw the cue sheet:

  * a spectral-flux onset detector, asked where the nine section marks landed;
  * the speech band alone, asked how far in front of the bed the narrator is;
  * the BS.1770-4 gated meter and the 4x-oversampled true-peak meter;
  * an A-weighted band split, because raw power always over-reports the bottom octaves and
    the assembly film lost 81 % of its energy to an inaudible 36.7 Hz before anyone looked.

What none of this measures is whether it sounds any good. There is no instrument for that here.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intro_env import OUT  # noqa: E402

from check_score import flux  # noqa: E402
from dsp import SR, read_wav  # noqa: E402
from mix_audio import lufs, true_peak_db  # noqa: E402

FPS = 30


def band_rms(x: np.ndarray, lo: float, hi: float, sel=None) -> float:
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    y = np.fft.irfft(np.fft.rfft(x) * ((f >= lo) & (f <= hi)), len(x))
    y = y if sel is None else y[sel]
    return 20 * math.log10(max(float(np.sqrt((y ** 2).mean())), 1e-12))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", type=Path, default=OUT / "audio" / "score.wav")
    ap.add_argument("--cues", type=Path, default=OUT / "audio" / "cues.json")
    ap.add_argument("--vo", type=Path, default=OUT / "audio" / "vo")
    ap.add_argument("--tol", type=float, default=2.0, help="frames of tolerance")
    args = ap.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    audio = read_wav(args.wav)
    mono = audio.mean(axis=0)
    dur = audio.shape[1] / SR
    print(f"{args.wav.name}: {dur:.3f} s vs {cues['duration']:.3f} s of film, "
          f"peak {20 * math.log10(max(float(np.abs(audio).max()), 1e-12)):+.2f} dBFS")
    if abs(dur - cues["duration"]) > 0.05:
        print("  LENGTH MISMATCH -- the mix is not the length of the film")

    print(f"  {lufs(audio):+.2f} LUFS integrated, {true_peak_db(audio):+.2f} dBTP")

    # The section marks, found by an onset detector that knows nothing about the schedule.
    f, ft = flux(mono, SR)
    print(f"\n  nine section marks, found by spectral flux (tolerance {args.tol:.0f} frames)")
    errs = []
    for s in cues["scenes"]:
        t0 = s["start"]
        if t0 <= 0.05:
            print(f"    {s['name']:10s} {t0:7.2f} s   no mark by design (the film fades up)")
            continue
        lo, hi = t0 - args.tol / FPS, t0 + args.tol / FPS
        sel = (ft >= lo) & (ft <= hi)
        before = (ft >= t0 - 0.5) & (ft < t0 - 0.1)
        base = float(np.median(f[before])) if before.any() else 0.0
        k = int(np.argmax(f[sel])) if sel.any() else -1
        if k < 0 or f[sel][k] < max(base * 1.5, 0.004):
            print(f"    {s['name']:10s} {t0:7.2f} s   NOT FOUND -- the mark is missing or "
                  f"buried")
            continue
        e = (ft[sel][k] - t0) * FPS
        errs.append(abs(e))
        print(f"    {s['name']:10s} {t0:7.2f} s   {e:+.2f} frames ({e / FPS * 1000:+.0f} ms)")
    if errs:
        print(f"    {len(errs)} of 8 found, |error| median {np.median(errs):.2f} frames "
              f"({np.median(errs) / FPS * 1000:.1f} ms), worst {max(errs):.2f}")

    # Intelligibility. Speech band only, so the pedal and the shimmer cannot flatter it.
    nar = args.vo / "narration.json"
    if nar.exists():
        meta = json.loads(nar.read_text(encoding="utf-8"))
        spoken = np.zeros(len(mono), dtype=bool)
        for line in meta["lines"]:
            i = int(line["start"] * SR)
            spoken[i:i + int(line["dur"] * SR)] = True
        on = band_rms(mono, 300, 3400, spoken)
        off = band_rms(mono, 300, 3400, ~spoken)
        print(f"\n  narration: {len(meta['lines'])} lines of {meta['voice']}, chain "
              f"{meta['chain']}, {spoken.mean() * 100:.0f} % of the film has speech in it")
        print(f"    300-3400 Hz   speech {on:+.1f} dB   bed alone {off:+.1f} dB   "
              f"= {on - off:+.1f} dB in front")
        # Per-scene, because an average can hide one section where the bed is too loud.
        print("    by scene:")
        for s in cues["scenes"]:
            a, b = int(s["start"] * SR), min(len(mono), int(s["end"] * SR))
            m = np.zeros(len(mono), dtype=bool)
            m[a:b] = True
            sp, bd = m & spoken, m & ~spoken
            if sp.sum() < SR or bd.sum() < SR // 2:
                continue
            print(f"      {s['name']:10s} {band_rms(mono, 300, 3400, sp):+6.1f} vs "
                  f"{band_rms(mono, 300, 3400, bd):+6.1f} = "
                  f"{band_rms(mono, 300, 3400, sp) - band_rms(mono, 300, 3400, bd):+5.1f} dB")

    # Stereo width and the low end, the two things a synthesised mix most easily gets wrong.
    mid, side = (audio[0] + audio[1]) / 2, (audio[0] - audio[1]) / 2
    ratio = float(np.sqrt((side ** 2).mean()) / max(np.sqrt((mid ** 2).mean()), 1e-12))
    spec = np.abs(np.fft.rfft(mono))
    freq = np.fft.rfftfreq(len(mono), 1.0 / SR)
    bands = ((20, 80), (80, 300), (300, 1500), (1500, 6000), (6000, 20000))

    def split(power):
        total = float(power.sum())
        return "  ".join(f"{lo}-{hi} {power[(freq >= lo) & (freq < hi)].sum() / total * 100:4.1f}%"
                         for lo, hi in bands)

    f2 = np.maximum(freq, 1.0) ** 2
    ra = (12194.0 ** 2 * f2 ** 2) / ((f2 + 20.6 ** 2)
                                     * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2))
                                     * (f2 + 12194.0 ** 2))
    print(f"\n  side/mid {ratio:.3f}")
    print(f"    raw        {split(spec ** 2)}")
    print(f"    A-weighted {split((spec * ra * 10 ** (2.0 / 20.0)) ** 2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
