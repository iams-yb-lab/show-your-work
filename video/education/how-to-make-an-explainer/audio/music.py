#!/usr/bin/env python3
"""
music.py — a calm bed the length of the master, with a mark on every scene cut.

Tonal synthesis only: no samples, nothing placed by ear. The structure comes from the film's own scene
table, so the music cannot drift out of agreement with the picture — if a scene moves, this moves.

Two rules it exists to obey:

  * **the narration is the subject.** Nothing here is allowed to compete: no drums, no transient
    percussion, no melody in the range the voice occupies, no build that arrives mid-sentence.
  * **a mark lands on the cut, not on a word.** Each scene begins with a hole before its first word —
    1.0 s, recorded in master.json — and that is where the bell goes.

    python3 audio/music.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

AUDIO = Path(__file__).resolve().parent


def video_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "engine").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree")


VIDEO = video_root(AUDIO)
WORK = VIDEO / "out/education/how-to-make-an-explainer"
SR = 48_000

# F major, bright and moving rather than solemn: I – vi – IV – V with an added ninth on each chord,
# which is what makes a major triad sound glad instead of plain. The pad still sits below the voice's
# fundamental range so nothing masks speech; the brightness is carried by the arpeggio above it.
ROOT = 53                     # F3
PROGRESSION = [(0, 4, 7, 14), (9, 12, 16, 23), (5, 9, 12, 19), (7, 11, 14, 21)]
BPM = 92.0
BEAT = 60.0 / BPM
BAR = 4.0 * BEAT


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def env(n: int, attack: float, release: float) -> np.ndarray:
    curve = np.ones(n, dtype=np.float32)
    a = min(n, int(round(attack * SR)))
    r = min(n, int(round(release * SR)))
    if a:
        curve[:a] = np.sin(np.linspace(0, math.pi / 2, a, dtype=np.float32)) ** 2
    if r:
        curve[-r:] *= np.sin(np.linspace(math.pi / 2, 0, r, dtype=np.float32)) ** 2
    return curve


def add(out: np.ndarray, start: float, dur: float, midi: float, amp: float,
        attack: float, release: float, partials=(1.0, 0.30, 0.12), pan: float = 0.0) -> None:
    a = max(0, int(round(start * SR)))
    b = min(out.shape[1], int(round((start + dur) * SR)))
    if b <= a:
        return
    t = np.arange(b - a, dtype=np.float32) / SR
    tone = np.zeros(b - a, dtype=np.float32)
    for index, weight in enumerate(partials, 1):
        # A little detune per partial: two oscillators a few cents apart read as an instrument
        # rather than an oscillator, and it costs nothing.
        tone += weight * np.sin(2 * math.pi * hz(midi) * index * t)
        tone += weight * 0.6 * np.sin(2 * math.pi * hz(midi + 0.04) * index * t)
    tone *= env(len(tone), attack, release) * amp
    left, right = math.sqrt((1 - pan) / 2), math.sqrt((1 + pan) / 2)
    out[0, a:b] += tone * left
    out[1, a:b] += tone * right


def energy(scenes: list[dict], duration: float) -> callable:
    """One level per scene, interpolated smoothly, so the bed lifts at a cut and never mid-line."""
    shape = [0.55, 0.62, 0.70, 0.74, 0.72, 0.80, 0.70, 0.86]
    points = [(0.0, shape[0])]
    for index, scene in enumerate(scenes):
        points.append((scene["in_s"], shape[min(index, len(shape) - 1)]))
    points.append((duration, shape[-1] * 0.7))

    def at(time: float) -> float:
        for (t0, e0), (t1, e1) in zip(points, points[1:]):
            if t0 <= time <= t1:
                f = (time - t0) / max(t1 - t0, 1e-9)
                return e0 + (e1 - e0) * (f * f * (3 - 2 * f))
        return points[-1][1]
    return at


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=WORK / "music/bed.wav")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    master = json.loads((WORK / "master.json").read_text(encoding="utf-8"))
    duration = master["duration_s"]
    scenes = master["scenes"]
    level = energy(scenes, duration)
    out = np.zeros((2, int(round(duration * SR))), dtype=np.float32)

    # Pad: the chord, two bars each, overlapping so there is no gap between changes.
    bar = 0
    while bar * BAR < duration:
        chord = PROGRESSION[(bar // 2) % len(PROGRESSION)]
        start = bar * BAR
        loud = level(start)
        for voice, interval in enumerate(chord):
            add(out, start, BAR * 2.2, ROOT + interval, 0.050 * loud, 0.9, 1.4,
                pan=(-0.35, 0.0, 0.35, 0.18)[voice % 4])
        # A light arpeggio over the chord — eighth notes, alternating pan, each one short and soft.
        # This is where the gladness comes from, and it stays an octave above the voice so it reads as
        # sparkle rather than as another speaker.
        figure = [chord[0] + 12, chord[2] + 12, chord[3] + 12, chord[1] + 12,
                  chord[3] + 12, chord[2] + 12, chord[0] + 19, chord[2] + 12]
        for step in range(16):
            at = start + step * BEAT / 2
            if at >= duration:
                break
            note = figure[step % len(figure)]
            add(out, at, BEAT * 0.9, ROOT + note, 0.020 * level(at), 0.012, BEAT * 0.8,
                partials=(1.0, 0.18, 0.06), pan=0.30 if step % 2 else -0.30)
        bar += 2

    # Pedal: the root, an octave down, continuous. It is what makes the bed feel held rather than
    # played, and it lives below everything the voice does.
    for bar in range(0, int(duration / (BAR * 4)) + 1):
        add(out, bar * BAR * 4, BAR * 4.4, ROOT - 12, 0.05 * level(bar * BAR * 4), 1.6, 2.0,
            partials=(1.0, 0.12))

    # One bell on each scene cut, inside the hole before the first word.
    marks = []
    for index, scene in enumerate(scenes):
        at = scene["in_s"] + 0.10
        for partial, weight in ((0, 1.0), (12, 0.45), (19, 0.22)):
            add(out, at, 3.2, ROOT + 12 + partial, 0.030 * weight * level(at), 0.004, 3.0,
                partials=(1.0, 0.05), pan=0.12 if index % 2 else -0.12)
        marks.append(round(at, 3))

    # Air: filtered noise, very quiet, to stop the bed sounding like a synthesizer test tone.
    rng = np.random.default_rng(20260813)
    noise = rng.standard_normal(out.shape[1]).astype(np.float32)
    kernel = np.hanning(2048).astype(np.float32)
    kernel /= kernel.sum()
    air = np.convolve(noise, kernel, mode="same")
    air /= max(float(np.max(np.abs(air))), 1e-9)
    ramp = np.array([level(i / SR) for i in range(0, out.shape[1], 512)], dtype=np.float32)
    ramp = np.interp(np.arange(out.shape[1]), np.arange(len(ramp)) * 512, ramp).astype(np.float32)
    out += 0.012 * air * ramp

    fade = int(2.5 * SR)
    out[:, :fade] *= np.linspace(0, 1, fade, dtype=np.float32) ** 2
    out[:, -fade:] *= np.linspace(1, 0, fade, dtype=np.float32) ** 2

    peak = float(np.max(np.abs(out)))
    if peak > 0.98:
        out *= 0.98 / peak
    sf.write(args.out, out.T, SR, subtype="FLOAT")

    record = {
        "path": str(args.out), "duration_s": round(out.shape[1] / SR, 3), "sample_rate": SR,
        "channels": 2, "peak": round(float(np.max(np.abs(out))), 4),
        "key": "F major", "bpm": BPM, "progression": PROGRESSION,
        "scene_marks_s": marks, "energy_per_scene": [round(level(s["in_s"]), 3) for s in scenes],
        "no_percussion": True, "no_sidechain_ducking": True,
    }
    (WORK / "music.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"bed: {args.out}")
    print(f"  {record['duration_s']:.1f} s, peak {record['peak']:.3f}, "
          f"{len(marks)} scene marks at {', '.join(f'{m:.1f}' for m in marks)} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
