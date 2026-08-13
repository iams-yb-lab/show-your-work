"""Measure a rendered soundtrack against the cue sheet, from the audio alone.

    python tools/check_score.py --wav out/audio/score_cold.wav --cues out/audio/cues.json

The mixer places every sound from a frame number, so checking it against the same frame
numbers proves nothing. This runs an onset detector over the finished audio -- spectral flux,
which knows nothing about the cue sheet -- and asks where the onsets actually landed. An
off-by-one-frame conversion, a layer that silently failed, or a tick buried under the music
all show up here and cannot show up in the mixer's own output.

Onsets are reported in frames, because that is the unit the film is cut in and 1/30 s is the
tolerance that matters: an error under half a frame is inaudible as sync.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

HOP = 128          # 2.67 ms -- a fifth of a frame, so a frame of error is 12 hops
WIN = 512


def read_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        sr, n, width = w.getframerate(), w.getnframes(), w.getsampwidth()
        raw = w.readframes(n)
    if width != 3:
        raise SystemExit(f"expected 24-bit, got {width * 8}-bit")
    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
    v = (b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16))
    v = np.where(v & 0x800000, v - 0x1000000, v).astype(np.float64) / (2 ** 23)
    return v.reshape(-1, 2).T, sr


def flux(mono: np.ndarray, sr: int):
    """Spectral flux: the sum of positive magnitude changes between neighbouring frames. It
    peaks where energy arrives, which is what an onset is."""
    n = (len(mono) - WIN) // HOP + 1
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    win = np.hanning(WIN)
    mag = np.abs(np.fft.rfft(mono[idx] * win, axis=1))
    d = np.diff(mag, axis=0, prepend=mag[:1])
    f = np.maximum(d, 0.0).sum(axis=1)
    # Timestamp each frame at the *centre* of its window. Using the start biases every
    # measured onset late by WIN/2 -- 5.3 ms, which is 0.16 of a frame, and is exactly the
    # systematic error the first run of this tool reported as a median.
    return f / max(f.max(), 1e-12), (np.arange(n) * HOP + WIN / 2) / sr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", type=Path, required=True)
    ap.add_argument("--cues", type=Path, default=Path("out/audio/cues.json"))
    ap.add_argument("--tol", type=float, default=1.0, help="frames of tolerance")
    ap.add_argument("--voice", type=Path, help="vo_*.wav directory, to check intelligibility")
    args = ap.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    fps = cues["fps"]
    audio, sr = read_wav(args.wav)
    mono = audio.mean(axis=0)
    f, ft = flux(mono, sr)

    print(f"{args.wav.name}: {len(mono) / sr:.3f} s, {sr} Hz, "
          f"peak {20 * math.log10(max(np.abs(audio).max(), 1e-12)):+.2f} dBFS")
    dead = float((np.abs(mono) < 1e-5).mean())
    print(f"  silence: {dead * 100:.2f} % of samples below -100 dBFS")

    def onset_error(frame: int, tol_frames: float):
        """Frames between the cue and the nearest flux peak, or None if there is no rise."""
        t0 = (frame - 1) / fps
        lo, hi = t0 - tol_frames / fps, t0 + tol_frames / fps
        sel = (ft >= lo) & (ft <= hi)
        if not sel.any():
            return None
        seg, segt = f[sel], ft[sel]
        before = (ft >= t0 - 0.35) & (ft < t0 - 0.05)
        base = float(np.median(f[before])) if before.any() else 0.0
        k = int(np.argmax(seg))
        if seg[k] < max(base * 1.8, 0.02):
            return None
        return (segt[k] - t0) * fps

    def energy_rise(frame: int, window: float = 0.25) -> float:
        """dB of rise across a cue, for events with no transient in them. A mask film settling
        onto a board is a swell, not an impact -- spectral flux is the wrong instrument for it
        and reports a real sound as missing."""
        t0 = (frame - 1) / fps
        a = mono[int((t0 - window) * sr):int(t0 * sr)]
        b = mono[int(t0 * sr):int((t0 + window) * sr)]
        if not len(a) or not len(b):
            return 0.0
        return 20 * math.log10(max(float(np.sqrt((b ** 2).mean())), 1e-12)
                               / max(float(np.sqrt((a ** 2).mean())), 1e-12))

    groups = [
        ("component landings", [p["land"] for p in cues["parts"]]),
        ("hero landings", [h["land"] for h in cues["heroes"]]),
    ]
    for name, frames in groups:
        errs = [onset_error(fr, args.tol) for fr in frames]
        hit = [e for e in errs if e is not None]
        if not hit:
            print(f"  {name:22s} 0/{len(frames)} detected")
            continue
        a = np.abs(hit)
        print(f"  {name:22s} {len(hit)}/{len(frames)} detected within "
              f"{args.tol:.0f} frame  |err| median {np.median(a):.2f} fr "
              f"({np.median(a) / fps * 1000:.1f} ms), worst {a.max():.2f} fr")

    soft = [("film contact top", cues["fab"]["film_contact"][0]),
            ("film contact bottom", cues["fab"]["film_contact"][1]),
            ("silkscreen starts", cues["fab"]["silk"][0])]
    for name, fr in soft:
        print(f"  {name:22s} {energy_rise(fr):+5.1f} dB across the cue (a swell, not a hit)")

    # Section loudness, so the arc can be read as numbers: fabrication should sit well under
    # the swarm, and the tail should fall away rather than stop.
    print("\n  short-term level by section (RMS, dBFS)")
    fab = cues["fab"]
    sections = [
        ("copper", 1, fab["copper_end"]),
        ("etch + coat", fab["copper_end"], fab["pads"][0]),
        ("plate + print", fab["pads"][0], fab["done"]),
        ("swarm", fab["populate"], cues["waves"][-1]["land_last"]),
        ("heroes", cues["heroes"][0]["spawn"], cues["heroes"][-1]["land"]),
        ("finale", cues["heroes"][-1]["land"], cues["frames"]),
    ]
    for name, a, b in sections:
        i, j = int((a - 1) / fps * sr), int((b - 1) / fps * sr)
        seg = mono[i:j]
        rms = 20 * math.log10(max(float(np.sqrt((seg ** 2).mean())), 1e-12))
        print(f"    {name:14s} f{a:5d}-{b:<5d} {(b - a) / fps:5.1f} s   {rms:6.1f}")

    if args.voice:
        # Intelligibility, measured rather than assumed: the narrator has to be clearly in
        # front of the music in the band that carries speech. Each line's window is compared
        # with the music-only stretches, in 300-3400 Hz only, so the pedal and the shimmer
        # cannot flatter the result.
        lines = sorted(int(p.stem.split("_")[1]) for p in args.voice.glob("vo_*.wav"))
        spoken = np.zeros(len(mono), dtype=bool)
        for fr in lines:
            d = wave.open(str(args.voice / f"vo_{fr:04d}.wav"), "rb")
            dur = d.getnframes() / d.getframerate()
            d.close()
            i = int((fr - 1) / fps * sr)
            spoken[i:i + int(dur * sr)] = True
        vf = np.fft.rfftfreq(len(mono), 1.0 / sr)
        band = np.fft.irfft(np.fft.rfft(mono) * ((vf >= 300) & (vf <= 3400)), len(mono))
        on = 20 * math.log10(max(float(np.sqrt((band[spoken] ** 2).mean())), 1e-12))
        off = 20 * math.log10(max(float(np.sqrt((band[~spoken] ** 2).mean())), 1e-12))
        print(f"\n  narration: {len(lines)} lines, {spoken.mean() * 100:.0f} % of the film "
              f"has speech in it")
        print(f"    300-3400 Hz  speech {on:+.1f} dB  vs music-only {off:+.1f} dB  "
              f"= {on - off:+.1f} dB in front")

    # Stereo width and low end, the two things a synthesised mix most easily gets wrong.
    mid = (audio[0] + audio[1]) / 2
    side = (audio[0] - audio[1]) / 2
    ratio = float(np.sqrt((side ** 2).mean()) / max(np.sqrt((mid ** 2).mean()), 1e-12))
    spec = np.abs(np.fft.rfft(mono))
    freq = np.fft.rfftfreq(len(mono), 1.0 / sr)
    bands = ((20, 80), (80, 300), (300, 1500), (1500, 6000), (6000, 20000))

    def split(power):
        total = float(power.sum())
        return "  ".join(
            f"{lo}-{hi} {power[(freq >= lo) & (freq < hi)].sum() / total * 100:4.1f}%"
            for lo, hi in bands)

    # Raw power always over-reports the bottom octaves, because equal energy there is far
    # quieter to a listener. A-weighting is what decides whether a mix is actually bass-heavy
    # or merely bass-present, so both are printed and the second is the one to read.
    f2 = np.maximum(freq, 1.0) ** 2
    ra = (12194.0 ** 2 * f2 ** 2) / ((f2 + 20.6 ** 2)
                                     * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2))
                                     * (f2 + 12194.0 ** 2))
    aw = ra * 10 ** (2.0 / 20.0)
    print(f"\n  side/mid {ratio:.3f}")
    print(f"    raw        {split(spec ** 2)}")
    print(f"    A-weighted {split((spec * aw) ** 2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
