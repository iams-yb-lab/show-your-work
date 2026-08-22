"""Create a bright, welcoming major-key score using tonal synthesis only."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf


SAMPLE_RATE = 48_000
BPM = 104.0
BEAT = 60.0 / BPM
BAR = 4.0 * BEAT


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def envelope(length: int, attack: float, release: float) -> np.ndarray:
    curve = np.ones(length, dtype=np.float32)
    attack_length = min(length, round(attack * SAMPLE_RATE))
    release_length = min(length, round(release * SAMPLE_RATE))
    if attack_length:
        phase = np.linspace(0.0, math.pi / 2.0, attack_length, dtype=np.float32)
        curve[:attack_length] = np.sin(phase) ** 2
    if release_length:
        phase = np.linspace(math.pi / 2.0, 0.0, release_length, dtype=np.float32)
        curve[-release_length:] *= np.sin(phase) ** 2
    return curve


def energy_at(time_seconds: float, duration: float) -> float:
    scale = duration / 338.1
    points = [
        (0.0, 0.20), (18.9 * scale, 0.42), (42.3 * scale, 0.58),
        (81.6 * scale, 0.47), (112.6 * scale, 0.43), (160.9 * scale, 0.57),
        (193.6 * scale, 0.65), (255.2 * scale, 0.70), (301.3 * scale, 0.79),
        (duration, 0.58),
    ]
    for (start_time, start_energy), (end_time, end_energy) in zip(points, points[1:]):
        if start_time <= time_seconds <= end_time:
            fraction = (time_seconds - start_time) / max(end_time - start_time, 1e-9)
            smooth = fraction * fraction * (3.0 - 2.0 * fraction)
            return start_energy + (end_energy - start_energy) * smooth
    return points[-1][1]


def add_note(
    output: np.ndarray,
    start: float,
    duration: float,
    midi: float,
    amplitude: float,
    attack: float,
    release: float,
    brightness: float = 0.12,
    pan: float = 0.0,
    phase_offset: float = 0.0,
) -> None:
    first = max(0, round(start * SAMPLE_RATE))
    last = min(output.shape[1], round((start + duration) * SAMPLE_RATE))
    if last <= first:
        return
    length = last - first
    time = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    frequency = hz(midi)
    # Rounded fundamentals plus quiet harmonics: bright without hiss or percussion noise.
    left = (
        np.sin(2 * np.pi * frequency * 0.9994 * time + phase_offset)
        + brightness * np.sin(2 * np.pi * 2 * frequency * 0.9994 * time + 0.31)
        + brightness * 0.22 * np.sin(2 * np.pi * 3 * frequency * 0.9994 * time + 0.67)
    )
    right = (
        np.sin(2 * np.pi * frequency * 1.0006 * time + phase_offset + 0.06)
        + brightness * np.sin(2 * np.pi * 2 * frequency * 1.0006 * time + 0.39)
        + brightness * 0.22 * np.sin(2 * np.pi * 3 * frequency * 1.0006 * time + 0.74)
    )
    signal = np.stack((left, right)) * envelope(length, attack, release)[None, :] * amplitude
    pan = float(np.clip(pan, -1.0, 1.0))
    signal[0] *= math.sqrt((1.0 - pan) / 2.0) * math.sqrt(2.0)
    signal[1] *= math.sqrt((1.0 + pan) / 2.0) * math.sqrt(2.0)
    output[:, first:last] += signal.astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()
    duration = float(args.duration)
    target = args.out.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    music = np.zeros((2, round(duration * SAMPLE_RATE)), dtype=np.float32)

    # G major. The I-V-vi-IV family reads as optimistic and familiar; secondary patterns
    # keep a five-minute technical introduction from sounding like a short loop.
    progressions = [
        [
            ([43, 55, 59, 62, 67], [67, 71, 74, 79]),  # G(add9)
            ([38, 50, 54, 57, 62], [66, 69, 74, 78]),  # D(add9)
            ([40, 52, 55, 59, 64], [67, 71, 76, 79]),  # Em7
            ([36, 48, 52, 55, 62], [64, 67, 74, 76]),  # C(add9)
        ],
        [
            ([43, 55, 59, 62, 67], [67, 74, 71, 79]),  # G
            ([47, 54, 59, 62, 66], [66, 71, 74, 78]),  # Bm7
            ([36, 48, 52, 55, 62], [64, 67, 71, 76]),  # Cmaj7
            ([38, 50, 54, 57, 64], [66, 69, 76, 78]),  # Dsus2
        ],
    ]
    chord_length = 2.0 * BAR
    time = 0.0
    chord_index = 0
    while time < duration:
        section = int(time // (16.0 * BAR)) % 2
        chord, arpeggio = progressions[section][chord_index % 4]
        energy = energy_at(time + chord_length / 2.0, duration)

        # Wide, low-level major-key pad.
        for voice_index, note in enumerate(chord[1:]):
            add_note(
                music, time, chord_length + 0.30, note, 0.0145 * energy,
                attack=0.62, release=0.86, brightness=0.09,
                pan=-0.54 + voice_index * 0.36,
            )

        # Soft bass pulse on beats one and three. There is no kick or noise transient.
        for bar_index in range(2):
            bar_start = time + bar_index * BAR
            add_note(
                music, bar_start, 1.28 * BEAT, chord[0], 0.042 * energy,
                attack=0.045, release=0.30, brightness=0.045,
                pan=-0.10 if bar_index == 0 else 0.10,
            )
            add_note(
                music, bar_start + 2.0 * BEAT, 0.92 * BEAT, chord[0] + 12,
                0.019 * energy, attack=0.035, release=0.27, brightness=0.07,
                pan=0.08 if bar_index == 0 else -0.08,
            )

        # Friendly, lightly bouncing eighth-note pattern above speech fundamentals.
        order = (0, 2, 1, 3, 1, 2, 0, 2, 1, 3, 2, 1, 0, 2, 3, 2)
        pluck_level = max(0.0, energy - 0.22)
        for step in range(16):
            note = arpeggio[order[(step + chord_index) % len(order)]]
            swing = 0.035 * BEAT if step % 2 else 0.0
            add_note(
                music, time + step * (BEAT / 2.0) + swing, 0.39 * BEAT,
                note, 0.0175 * pluck_level, attack=0.008, release=0.19,
                brightness=0.27, pan=-0.40 if step % 2 == 0 else 0.40,
            )

        # A short pentatonic welcome motif every eight chords, introduced after the opening.
        if time >= 18.0 and chord_index % 8 == 7:
            motif = [74, 76, 79, 76, 74, 71]
            motif_start = time + BAR
            for motif_index, note in enumerate(motif):
                add_note(
                    music, motif_start + motif_index * (BEAT / 2.0), 0.58 * BEAT,
                    note, 0.0115 * energy, attack=0.012, release=0.28,
                    brightness=0.22, pan=0.22,
                )

        chord_index += 1
        time += chord_length

    # Tonal echoes add width; no broadband noise, impulse-response hiss, or pumping.
    for delay_seconds, gain, crossfeed in ((0.19, 0.105, True), (0.37, 0.050, False)):
        delay = round(delay_seconds * SAMPLE_RATE)
        delayed = music[:, :-delay].copy()
        if crossfeed:
            delayed = delayed[::-1]
        music[:, delay:] += delayed * gain

    fade_length = min(round(4.0 * SAMPLE_RATE), music.shape[1] // 2)
    music[:, :fade_length] *= np.linspace(0.0, 1.0, fade_length, dtype=np.float32)[None, :]
    music[:, -fade_length:] *= np.linspace(1.0, 0.0, fade_length, dtype=np.float32)[None, :]
    peak_before = float(np.abs(music).max())
    music *= 0.50 / max(peak_before, 1e-9)
    sf.write(target, music.T, SAMPLE_RATE, subtype="PCM_24")

    report = {
        "path": str(target),
        "duration": duration,
        "sample_rate": SAMPLE_RATE,
        "bpm": BPM,
        "key": "G major",
        "character": "happy, warm, welcoming, lightly energetic",
        "harmony": "I-V-vi-IV and I-iii-IV-V families",
        "noise_sources": 0,
        "percussion_noise": False,
        "sidechain_or_ducking": False,
        "peak": float(np.abs(music).max()),
    }
    (target.parent / "music-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
