"""Synthesise the whole soundtrack for the assembly film from its own cue sheet.

    python tools/mix_audio.py --cues out/audio/cues.json --flow out/audio/flow.csv \
        --variant cold --out out/audio/score_cold.wav

Nothing is sampled and nothing is placed by ear. Every effect is generated here, and every
one of them is positioned by a frame number that came out of `audio_cues.py`, which in turn
re-ran the animation's own schedule. numpy and the standard library only.

Three ideas carry it.

  One harmonic source. There is a single pitch set for the entire film -- D, E, F, G, A, C,
  the sixth degree deliberately absent so the mode never commits to major or minor -- and
  *everything* is drawn from it: the pad, the pulse, the bells, the resonant peak of each
  etch sweep, and the pitch of all 110 component landings. A landing tick is not a sound
  effect that happens to coincide with the music; it is a note of it. That is what stops
  110 transients in nineteen seconds from turning into gravel.

  One note that never moves. A D pedal runs unbroken from the first frame to the last, and
  the harmony above it is the only thing that travels. The film is about holding a
  temperature still while everything else changes, so the score is built the same way.

  The grid comes from the schedule, not from a metronome. The first component sets off on
  frame 880, the ADC lands on 1720 and the Teensy on 2140 -- exactly 28.0 s and then 14.0 s
  apart -- so a bar of exactly 70 frames starting at frame 880 puts both hero landings on
  downbeats with no tempo map and no drift. BAR_FRAMES is that number and it is the only
  place the tempo exists.

Deliberately *not* done: the music never accents a component landing. Scoring every event is
mickey-mousing, and at 110 events it stops being emphasis and becomes noise. The music has
exactly three structural moments -- the first part setting off, the ADC landing, the Teensy
landing -- and the sound effects carry everything else.

A frame is displayed from t = (frame - 1) / fps, so that is the conversion used throughout.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
import sys
import wave
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dsp import (SR, bandpass, highpass, lowpass, movavg, read_wav,  # noqa: E402
                 resonator, slide_max, spectral, write_wav24)
from voice_chain import breath  # noqa: E402

AUDIO_SEED = 20260812
# How far the music drops while the narrator speaks. 9 dB is enough to put him clearly in
# front without the drop itself becoming audible as a move.
DUCK_DB = 9.0

# ------------------------------------------------------------------- the one pitch set
#
# Semitones above D. The sixth degree (B / B-flat) is absent on purpose: with no sixth the
# mode is neither dorian nor aeolian, which is what keeps an 84-second bed from declaring
# itself happy or sad. Every pitch anywhere in this file comes from here.
SCALE = (0, 2, 3, 5, 7, 10)          # D E F G A C
ROOT_MIDI = 38                       # D2 = 73.416 Hz
# The pedal, and how much of each octave. D2 carries it; D1 is seasoning at a quarter of the
# level. The first cut had them equal and 36.7 Hz then held 81 % of the mix's total energy --
# nearly inaudible on any real speaker, but it dominated the peaks, so the limiter spent its
# whole range on sub nobody would hear and everything above it came out quiet.
PEDAL = ((26, 0.25), (38, 1.0))      # D1 + D2, held for the whole film

# One bar = 70 frames = 2.3333 s = 102.857 BPM. See the module docstring: this is not a
# chosen tempo, it is the interval that makes both hero landings fall on downbeats.
BAR_FRAMES = 70
BEATS_PER_BAR = 4


def midi_hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)


def scale_note(degree: int, octave: int = 0) -> int:
    """A midi note from the pitch set. degree may run past the end; it wraps with octaves."""
    return ROOT_MIDI + 12 * (octave + degree // len(SCALE)) + SCALE[degree % len(SCALE)]


# Chord voicings, as scale degrees over the D pedal. The third (F, degree 2) is absent until
# the first component sets off and absent again after the last one lands -- the film starts
# on bare copper and ends on a finished board, and the harmony opens, closes and reopens with
# it. Keys are bar numbers; -1 is everything before the grid starts.
CHORDS = {
    -1: ((0, 1), (4, 1), (1, 2)),               # D A E   -- open fifth, no third
    0: ((0, 1), (2, 1), (4, 1), (1, 2)),        # D F A E -- the third arrives with the parts
    4: ((2, 1), (4, 1), (5, 1), (1, 2)),        # F A C E
    8: ((4, 1), (5, 1), (1, 2), (2, 2)),        # A C E F
    12: ((5, 1), (1, 2), (3, 2), (0, 3)),       # C E G D -- the lift, on the ADC landing
    16: ((2, 1), (4, 1), (5, 1)),               # F A C   -- pull back before the climax
    18: ((0, 1), (2, 1), (4, 1), (0, 2)),       # D F A D -- the Teensy lands
    21: ((0, 1), (4, 1), (1, 2)),               # D A E   -- back where it began
}

# Component class -> (octave for its tick, body decay in seconds, level, low-thud weight).
# Mass reads as pitch: an 0402 is a high short tick, a terminal block is a low one with a
# body under it. The octaves are octaves of the same scale, so the swarm arpeggiates the
# chord that is playing rather than colliding with it.
CLASS_VOICE = {
    "chip_small":   dict(octave=4, decay=0.075, level=0.30, thud=0.00),
    "chip_mid":     dict(octave=3, decay=0.110, level=0.38, thud=0.05),
    "chip_large":   dict(octave=3, decay=0.150, level=0.45, thud=0.12),
    "semi":         dict(octave=4, decay=0.090, level=0.32, thud=0.00),
    "ic":           dict(octave=2, decay=0.260, level=0.60, thud=0.30),
    "magnetic":     dict(octave=2, decay=0.300, level=0.62, thud=0.40),
    "electrolytic": dict(octave=2, decay=0.280, level=0.58, thud=0.35),
    "switch":       dict(octave=3, decay=0.140, level=0.45, thud=0.15),
    "trimmer":      dict(octave=2, decay=0.200, level=0.50, thud=0.20),
    "connector":    dict(octave=1, decay=0.380, level=0.72, thud=0.55),
    "module":       dict(octave=1, decay=0.520, level=0.95, thud=0.85),
}


# ------------------------------------------------------------------------- primitives


class Mix:
    """A stereo buffer with everything addressed in seconds."""

    def __init__(self, duration: float):
        self.n = int(round(duration * SR))
        self.buf = np.zeros((2, self.n))
        self.t = np.arange(self.n) / SR

    def add(self, at: float, mono: np.ndarray, pan: float = 0.0, gain: float = 1.0):
        """Equal-power pan. pan -1 = frame left, +1 = frame right."""
        i = int(round(at * SR))
        if i >= self.n:
            return
        if i < 0:
            mono, i = mono[-i:], 0
        k = mono[:self.n - i] * gain
        a = (pan + 1.0) * math.pi / 4.0
        self.buf[0, i:i + len(k)] += k * math.cos(a)
        self.buf[1, i:i + len(k)] += k * math.sin(a)

    def add_stereo(self, at: float, st: np.ndarray, gain: float = 1.0):
        i = int(round(at * SR))
        k = st[:, :self.n - i] * gain
        self.buf[:, i:i + k.shape[1]] += k


def rng_for(name: str) -> np.random.Generator:
    """A separate deterministic stream per layer, so editing one layer cannot shift the
    noise in another. Same output on both machines, every run.

    The seed is a CRC of the name, not `hash()`. Python salts string hashing per process, so
    the version of this that used `hash()` drew different noise on every single render while
    claiming in this docstring not to -- every phase set, every whoosh and all 110 ticks. It
    was never reproducible and nothing here noticed, because noise sounds like noise.
    """
    return np.random.default_rng(zlib.crc32(f"{AUDIO_SEED}:{name}".encode()))


def smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def fade(t: np.ndarray, t0: float, t1: float) -> np.ndarray:
    """0 before t0, 1 after t1, smooth between. Reversed if t1 < t0."""
    if t1 == t0:
        return (t >= t1).astype(float)
    return smoothstep((t - t0) / (t1 - t0))


def noise(n: int, gen: np.random.Generator) -> np.ndarray:
    return gen.standard_normal(n)


def partial(n: int, hz: float, decay: float, phase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    return np.sin(2 * math.pi * hz * t + phase) * np.exp(-t / max(decay, 1e-4))


# ---------------------------------------------------------------------------- the score


class Score:
    """Bars, chords and the pitch of any given moment. The only thing that knows the grid."""

    def __init__(self, cues: dict):
        self.fps = cues["fps"]
        self.bar0_frame = cues["fab"]["populate"]
        self.bar = BAR_FRAMES / self.fps

    def t(self, frame: float) -> float:
        return (frame - 1.0) / self.fps

    def bar_time(self, b: float) -> float:
        return self.t(self.bar0_frame + b * BAR_FRAMES)

    def bar_at(self, t: float) -> float:
        return (t - self.bar_time(0)) / self.bar

    def chord_at(self, t: float):
        b = self.bar_at(t)
        key = -1
        for k in sorted(CHORDS):
            if b >= k:
                key = k
        return CHORDS[key]

    def note_for(self, t: float, octave: int, index: int) -> int:
        """A chord tone, transposed into the register a class belongs to. Every tick lands on
        a note of the chord that is sounding, which is the whole trick."""
        ch = self.chord_at(t)
        deg, base = ch[index % len(ch)]
        return scale_note(deg, base + octave - 2)


# ------------------------------------------------------------------------------ layers


def layer_pedal(mix: Mix, sc: Score, variant: str, ch: int) -> np.ndarray:
    """The D pedal. Present from the first frame to the last; the only thing that never
    changes. Everything else in the mix is a departure from it.

    Rendered once per channel with its own phase set. Two decorrelated renders of the same
    notes is real stereo width; panning one mono render to both sides is not, and the first
    cut measured 0.126 side/mid because of exactly that.
    """
    t, out = mix.t, np.zeros(mix.n)
    gen = rng_for(f"pedal-{ch}")
    for m, weight in PEDAL:
        hz = midi_hz(m)
        # Two voices a few cents apart give a slow beat rather than a dead tone. The rate is
        # under 0.2 Hz, so it reads as breathing, not as vibrato.
        for cents in (-3.0, 3.0):
            f = hz * 2 ** (cents / 1200.0)
            out += np.sin(2 * math.pi * f * t + gen.uniform(0, 6.28)) * 0.5 * weight
        if variant == "warm":
            out += np.sin(2 * math.pi * hz * 2 * t + gen.uniform(0, 6.28)) * 0.12 * weight
            out += np.sin(2 * math.pi * hz * 3 * t + gen.uniform(0, 6.28)) * 0.06 * weight
        else:
            out += np.sin(2 * math.pi * hz * 3 * t + gen.uniform(0, 6.28)) * 0.04 * weight
    breathe = 0.78 + 0.22 * np.sin(2 * math.pi * 0.043 * t + ch * 1.1)
    env = fade(t, 0.0, 5.0) * (1.0 - fade(t, sc.t(2400), sc.t(2520)) * 0.85)
    return out * breathe * env * 0.10


def layer_pad(mix: Mix, sc: Score, variant: str, busy: np.ndarray, ch: int) -> np.ndarray:
    """The chord above the pedal. One source: every voice is the same generator, only the
    pitch and the entry time differ.

    `busy` is the component-landing density, and the pad ducks under it. When the picture is
    at its busiest the music steps back -- the swarm is the one stretch that does not need
    help, and a pad competing with 107 transients only muddies both.
    """
    out = np.zeros(mix.n)
    gen = rng_for(f"pad-{variant}-{ch}")
    changes = sorted(CHORDS)
    for i, key in enumerate(changes):
        start = sc.bar_time(key) if key >= 0 else 0.0
        end = sc.bar_time(changes[i + 1]) if i + 1 < len(changes) else mix.t[-1] + 4.0
        # Only the window this chord is audible in gets synthesised. Rendering every voice
        # across the whole 84 s and multiplying by an envelope that is zero for most of it
        # is the same output for twenty times the work.
        a, b = max(0, int((start - 2.0) * SR)), min(mix.n, int((end + 2.0) * SR))
        if b <= a:
            continue
        t = mix.t[a:b]
        # 3-second crossfades, so no chord change is ever an edit.
        env = fade(t, start - 1.5, start + 1.5) * (1.0 - fade(t, end - 1.5, end + 1.5))
        voice = np.zeros(b - a)
        for deg, base in CHORDS[key]:
            hz = midi_hz(scale_note(deg, base))
            if variant == "warm":
                # Detuned saws: three per voice, a few cents apart, rolled off hard. The
                # harmonic stack is what makes it warm; the roll-off is what stops it buzzing.
                for cents in (-7.0, 0.0, 7.0):
                    f = hz * 2 ** (cents / 1200.0)
                    for h in range(1, 13):
                        if f * h > 6000:
                            break
                        voice += np.sin(2 * math.pi * f * h * t
                                        + gen.uniform(0, 6.28)) / h * 0.33
            else:
                # Glassy: a handful of partials with the upper ones slightly stretched, which
                # is what a struck bar does and what stops a sine stack sounding like a test
                # tone. Each partial breathes at its own rate.
                for h, amp in ((1, 1.0), (2, 0.42), (3, 0.20), (4.02, 0.12), (6.05, 0.06)):
                    lfo = 0.85 + 0.15 * np.sin(2 * math.pi * gen.uniform(0.02, 0.07) * t
                                               + gen.uniform(0, 6.28))
                    voice += np.sin(2 * math.pi * hz * h * t
                                    + gen.uniform(0, 6.28)) * amp * lfo
        out[a:b] += voice * env / len(CHORDS[key])
    t = mix.t
    out = spectral(out, lambda f: lowpass(f, 3200 if variant == "warm" else 5200, 2)
                   * highpass(f, 80, 2))
    duck = 1.0 - 0.45 * busy
    lift = 0.55 + 0.45 * fade(t, sc.bar_time(0) - 2.0, sc.bar_time(2))
    return out * duck * lift * (0.075 if variant == "warm" else 0.060)


def layer_pulse(mix: Mix, sc: Score, variant: str, busy: np.ndarray) -> np.ndarray:
    """A tuned blip on the beat, from the first component setting off to just after the last
    landing. Its subdivision follows the film: half notes while the swarm is thin, quarters
    while it is dense, half notes again as it resolves."""
    out = np.zeros(mix.n)
    gen = rng_for("pulse")
    beat = sc.bar / BEATS_PER_BAR
    b = 0.0
    while sc.bar_time(b) < sc.bar_time(22):
        t0 = sc.bar_time(b)
        beat_i = int(round((b % 1.0) * BEATS_PER_BAR))
        dense = 4 <= b < 18
        if not dense and beat_i % 2 == 1:
            b += 1.0 / BEATS_PER_BAR
            continue
        strong = beat_i == 0
        i = int(t0 * SR)
        lvl = np.interp(t0, mix.t, busy) if 0 <= t0 < mix.t[-1] else 0.0
        amp = (0.55 if strong else 0.26) * (0.45 + 0.55 * lvl)
        n = int(0.22 * SR)
        note = sc.note_for(t0, octave=3 if strong else 4, index=0 if strong else 2)
        hz = midi_hz(note)
        blip = partial(n, hz, 0.055 if strong else 0.035)
        blip += partial(n, hz * 2.01, 0.025) * 0.35
        if variant == "warm":
            blip = spectral(blip, lambda f: lowpass(f, 2600, 2))
            blip += noise(n, gen) * np.exp(-np.arange(n) / SR / 0.006) * 0.05
        else:
            blip += noise(n, gen) * np.exp(-np.arange(n) / SR / 0.003) * 0.08
        if i + n <= mix.n:
            out[i:i + n] += blip * amp
        b += 1.0 / BEATS_PER_BAR
    fadein = fade(mix.t, sc.bar_time(0) - 0.2, sc.bar_time(1))
    fadeout = 1.0 - fade(mix.t, sc.bar_time(19), sc.bar_time(21.5))
    return out * fadein * fadeout * 0.10


def layer_structure(mix: Mix, sc: Score, variant: str) -> np.ndarray:
    """The three structural moments, and only these three: the first component sets off, the
    ADC lands on the downbeat of bar 12, the Teensy lands on the downbeat of bar 18.

    Everything else the picture does is left to the sound effects. This is the whole
    anti-mickey-mousing policy, expressed as a function with three entries.
    """
    out = np.zeros((2, mix.n))
    for b, weight, oct_ in ((0, 0.55, 1), (12, 0.85, 1), (18, 1.00, 0)):
        t0 = sc.bar_time(b)
        chord = sc.chord_at(t0 + 0.01)
        n = int(6.5 * SR)
        bell = np.zeros((2, n))
        for k, (deg, base) in enumerate(chord):
            hz = midi_hz(scale_note(deg, base + oct_))
            voice = np.zeros(n)
            # Struck-bar partials: 1, 2.76, 5.40 is close to a real bar's series, and the
            # stretch is what makes it read as metal rather than as a chord of sines.
            for h, amp, dec in ((1.0, 1.0, 3.4), (2.76, 0.34, 1.5), (5.40, 0.15, 0.7)):
                voice += partial(n, hz * h, dec * (0.75 + 0.25 * k)) * amp
            # The chord is spread across the field rather than stacked in the centre: low
            # tone left, high tone right, which is how a real set of bars would be laid out.
            pan = (k / max(len(chord) - 1, 1) - 0.5) * 0.9
            a = (pan + 1.0) * math.pi / 4.0
            bell[0] += voice * math.cos(a)
            bell[1] += voice * math.sin(a)
        bell /= len(chord)
        if variant == "cine" and b == 18:
            # The climax gets a sub swell underneath it, arriving *into* the hit rather than
            # after it -- 2.5 s of rise that lands on the frame the Teensy seats.
            rise = int(2.5 * SR)
            tr = np.arange(rise) / SR
            sub = np.sin(2 * math.pi * midi_hz(PEDAL[1][0]) * tr) * smoothstep(tr / 2.5) ** 2
            i0 = int((t0 - 2.5) * SR)
            if i0 > 0:
                out[:, i0:i0 + rise] += sub * 0.55
        i = int(t0 * SR)
        k = min(n, mix.n - i)
        out[:, i:i + k] += bell[:, :k] * weight
    return np.stack([spectral(c, lambda f: highpass(f, 90, 2)) for c in out]) * 0.055


def layer_cine_bed(mix: Mix, sc: Score) -> np.ndarray:
    """`cine` only: a bowed low layer that grows across the heroes and falls away after the
    Teensy. This is the whole difference between a bed and an arc."""
    t = mix.t
    gen = rng_for("cine-bed")
    out = np.zeros(mix.n)
    for deg, base in ((0, 1), (4, 1), (2, 2)):
        hz = midi_hz(scale_note(deg, base))
        v = np.zeros(mix.n)
        for h in range(1, 9):
            v += np.sin(2 * math.pi * hz * h * t + gen.uniform(0, 6.28)) / (h ** 1.4)
        out += v
    out = spectral(out, lambda f: lowpass(f, 1400, 3) * highpass(f, 60, 2))
    swell = (fade(t, sc.bar_time(8), sc.bar_time(18))
             * (1.0 - fade(t, sc.bar_time(18.5), sc.bar_time(22))))
    return out * swell * 0.045


def layer_air(mix: Mix, sc: Score, flow: np.ndarray) -> np.ndarray:
    """Room air, driven by the camera's own measured screen-flow. It rises as the move
    accelerates and dies as it slows, so the space breathes with the shot instead of running
    at a constant level under it. The number comes from camera_flow.py, not from a fader."""
    gen = rng_for("air")
    n = mix.n
    base = spectral(noise(n, gen), lambda f: bandpass(f, 180, 2400, 2))
    top = spectral(noise(n, gen), lambda f: bandpass(f, 2600, 11000, 2))
    frames = np.arange(1, len(flow) + 1)
    at = np.interp(mix.t, (frames - 1) / 30.0, flow)
    # Smooth over ~0.6 s: per-frame flow is spiky and the ear hears a fader move, not a curve.
    at = movavg(at, 0.6 * SR)
    at = at / max(at.max(), 1e-9)
    env = 0.25 + 0.75 * at ** 0.7
    tail = 1.0 - fade(mix.t, sc.t(2440), sc.t(2520)) * 0.9
    return (base * 0.55 + top * 0.20) * env * tail * 0.030


def layer_fabrication(mix: Mix, sc: Score, cues: dict):
    """The five fabrication beats. Each is a process, so each is a sweep or a swell with a
    duration -- none of them is a hit, because nothing in this stretch is an impact."""
    fab = cues["fab"]
    gen = rng_for("fab")

    def sweep(f0, f1, lo, hi, res_note, pan0, pan1, level):
        t0, t1 = sc.t(f0), sc.t(f1)
        n = int((t1 - t0) * SR)
        raw = noise(n, gen)
        # The resonance walks up the scale as the front crosses the board, which is what
        # gives an etch front a direction in pitch as well as in the stereo field.
        body = spectral(raw, lambda f: bandpass(f, lo, hi, 2))
        res = spectral(raw, lambda f: resonator(f, midi_hz(res_note), 9.0))
        x = np.arange(n) / n
        shape = np.sin(math.pi * x) ** 0.6
        mono = (body * 0.7 + res * 0.5) * shape
        step = max(1, n // 240)
        for i in range(0, n, step):
            j = min(n, i + step)
            u = i / max(n - 1, 1)
            mix.add(t0 + i / SR, mono[i:j], pan=pan0 + (pan1 - pan0) * u, gain=level)

    # Two etch fronts, crossing the board in opposite directions -- ETCH['phi_top'] is 22
    # degrees and phi_bot is 201, so the pans are opposed, which is the sound following the
    # geometry rather than a designer's preference.
    sweep(*fab["etch_top"], 700, 5200, scale_note(4, 1), -0.75, 0.75, 0.16)
    sweep(*fab["etch_bot"], 500, 4200, scale_note(0, 1), 0.75, -0.75, 0.16)

    # The mask films fly, then touch 20 frames apart. Two contacts, not one.
    fly_t = sc.t(fab["film_fly"])
    for k, cf in enumerate(fab["film_contact"]):
        ct = sc.t(cf)
        n = int((ct - fly_t) * SR)
        w = spectral(noise(n, gen), lambda f: bandpass(f, 300, 3600, 2))
        env = smoothstep(np.arange(n) / n) ** 2
        mix.add(fly_t, w * env, pan=-0.4 + 0.8 * k, gain=0.075)
        # The settle: air leaving, then the sheet stopping.
        m = int(0.5 * SR)
        settle = spectral(noise(m, gen), lambda f: lowpass(f, 900, 2))
        settle *= np.exp(-np.arange(m) / SR / 0.10)
        settle += partial(m, midi_hz(scale_note(0, 0)), 0.22) * 0.5
        mix.add(ct, settle, pan=-0.3 + 0.6 * k, gain=0.20)

    # Mask openings develop and the pads plate: a shimmer built from the upper partials of
    # the chord that is sounding, so the plating is literally the harmony brightening.
    t0, t1 = sc.t(fab["pads"][0]), sc.t(fab["pads"][1])
    n = int((t1 - t0) * SR)
    sh = np.zeros(n)
    for deg, base in sc.chord_at(t0):
        hz = midi_hz(scale_note(deg, base + 2))
        sh += partial(n, hz, (t1 - t0) * 0.7) * 0.4
    sh *= smoothstep(np.arange(n) / (0.35 * n))
    mix.add(t0, spectral(sh, lambda f: highpass(f, 1800, 2)), pan=0.0, gain=0.055)

    # Silkscreen: fine, dry, granular, and moving. Nothing resonant -- ink is not metal.
    t0, t1 = sc.t(fab["silk"][0]), sc.t(fab["silk"][1])
    n = int((t1 - t0) * SR)
    grain = noise(n, gen) * (gen.random(n) < 0.35)
    grain = spectral(grain, lambda f: bandpass(f, 3000, 9000, 2))
    grain *= np.sin(math.pi * np.arange(n) / n) ** 0.8
    step = max(1, n // 160)
    for i in range(0, n, step):
        j = min(n, i + step)
        mix.add(t0 + i / SR, grain[i:j], pan=0.6 - 1.2 * (i / max(n - 1, 1)), gain=0.085)


def tick(cls: str, hz: float, gen: np.random.Generator, variant: str) -> np.ndarray:
    """One component landing: a transient with a tuned body under it.

    The transient is what makes it an object; the body is what makes it a note. Both are
    needed -- transient alone and 107 of them are gravel, body alone and they are a chime
    that does not touch anything.
    """
    v = CLASS_VOICE[cls]
    n = int((v["decay"] * 4.0 + 0.05) * SR)
    tt = np.arange(n) / SR
    # Contact: 2-4 ms of noise, high and gone.
    click = noise(n, gen) * np.exp(-tt / 0.0022)
    click = spectral(click, lambda f: bandpass(f, 2200, 13000, 2))
    # Body: the note, plus a stretched partial so it has a material rather than a waveform.
    body = partial(n, hz, v["decay"])
    body += partial(n, hz * 2.04, v["decay"] * 0.45) * 0.30
    body += partial(n, hz * 3.11, v["decay"] * 0.22) * 0.12
    out = click * 0.55 + body * 0.75
    if v["thud"] > 0:
        # Mass: a short low pulse under the note, only for parts that have any.
        out += partial(n, hz * 0.5, v["decay"] * 0.7) * v["thud"] * 0.6
    if variant == "warm":
        out = spectral(out, lambda f: lowpass(f, 9000, 2))
    return out * v["level"]


def layer_voice(mix: Mix, sc: Score, vo_dir: Path):
    """The narration, placed by the frame in its filename, plus the duck curve it earns.

    Returns (stereo voice, gain curve for everything else). The music is pulled down while he
    speaks and comes back up between lines -- not a fixed level for the whole film, which
    would waste the long stretches where nobody is talking.
    """
    files = sorted(vo_dir.glob("vo_*.wav"))
    if not files:
        raise SystemExit(f"no vo_*.wav in {vo_dir} -- run tools/narrate.py first")
    stereo = np.zeros((2, mix.n))
    starts = []
    for f in files:
        frame = int(f.stem.split("_")[1])
        x = read_wav(f)
        if x.shape[0] == 1:
            x = np.repeat(x, 2, axis=0)
        i = int(sc.t(frame) * SR)
        k = min(x.shape[1], mix.n - i)
        if k > 0:
            stereo[:, i:i + k] += x[:, :k]
            starts.append((i, x.shape[1]))
    # Breaths. A narrator takes air before speaking again after a pause, and never after a
    # comma -- so one goes in only where at least 2.5 s of silence precedes the line. They sit
    # a little before the line, which is why they are placed here and not baked into the WAVs:
    # the file's t=0 is the start of speech, and that contract keeps the frame timing honest.
    gen = rng_for("breaths")
    last_end = -1e9
    for i, n in sorted(starts):
        if (i - last_end) / SR >= 2.5:
            b = breath(duration=gen.uniform(0.28, 0.40), seed=int(gen.integers(1, 9999)))
            j = i - int(gen.uniform(0.40, 0.52) * SR)
            if j > 0:
                stereo[:, j:j + len(b)] += b * gen.uniform(0.035, 0.055)
        last_end = i + n
    stereo /= max(np.abs(stereo).max(), 1e-9)
    # A gentle low cut: nothing under 85 Hz in a voice is speech, and it is exactly where the
    # pedal lives, so removing it buys clarity for both.
    mono = spectral(stereo.mean(axis=0), lambda f: highpass(f, 85, 2))

    # Presence: hold the duck across a whole sentence rather than pumping between syllables,
    # open 0.4 s before he starts and close 0.8 s after he stops.
    env = movavg(np.abs(mono), int(0.05 * SR))
    env = slide_max(env, int(1.2 * SR))
    env = movavg(env, int(0.4 * SR))
    presence = np.clip(env / max(np.percentile(env, 99), 1e-9), 0.0, 1.0) ** 0.5
    duck = 10 ** (-DUCK_DB * presence / 20.0)
    # The voice keeps the stereo the room gave it. Collapsing it to mono here would throw away
    # the early reflections that are the whole reason it sounds like a person somewhere.
    voice = np.stack([spectral(ch, lambda f: highpass(f, 85, 2)) for ch in stereo]) * 0.62
    return voice, duck


def layer_components(mix: Mix, sc: Score, cues: dict, variant: str,
                     emit: bool = True) -> np.ndarray:
    """All 107 supporting landings, each on its own frame, each on a note of the chord that
    is sounding, each panned to the side of frame it flew in from.

    Returns the landing-density curve, which the pad and the pulse both read: this is the one
    place that knows how busy the picture is.
    """
    gen = rng_for("ticks")
    density = np.zeros(mix.n)
    for k, p in enumerate(sorted(cues["parts"], key=lambda p: p["land"])):
        t0 = sc.t(p["land"])
        v = CLASS_VOICE[p["cls"]]
        note = sc.note_for(t0, v["octave"], index=k)
        hz = midi_hz(note) * (2 ** (gen.uniform(-4, 4) / 1200.0))
        s = tick(p["cls"], hz, gen, variant)
        # Sector is degrees about the view axis, 0 = frame right, 180 = frame left, so the
        # cosine is the pan directly. Held to 0.72 so nothing sits outside the picture.
        pan = math.cos(math.radians(p["sector"])) * 0.72
        # J8 is a showcased subject rather than a hero, and it is the largest thing on the
        # board bar the Teensy: it gets weight without getting a music accent.
        gain = 0.30 * (2.1 if p["ref"] == "J8" else 1.0) * gen.uniform(0.88, 1.12)
        if emit:
            mix.add(t0, s, pan=pan, gain=gain)
        # "How busy does it feel", not "how many landed this frame": each landing contributes
        # a 2-second bump, summed. Adding 107 short bumps is O(107 * w); convolving the whole
        # 84 s buffer with the same window is O(n * w) and a thousand times slower.
        w = int(2.0 * SR)
        bump = np.hanning(w)
        i = max(0, int(t0 * SR) - w // 2)
        density[i:i + w] += bump[:mix.n - i]
    return density / max(density.max(), 1e-9)


def layer_flights(mix: Mix, sc: Score, cues: dict):
    """Movement: one swell per wave, one approach per hero. Not one per part -- 107 whooshes
    is a wind tunnel, and the ticks already say how many things arrived."""
    gen = rng_for("flights")

    def whoosh(t0, t1, lo, hi, pan, level, tail=0.0):
        n = int((t1 + tail - t0) * SR)
        if n <= 0:
            return
        raw = spectral(noise(n, gen), lambda f: bandpass(f, lo, hi, 2))
        x = np.arange(n) / n
        # Rising, then cut short at the arrival: an approach that decays through its own
        # landing sounds like the part kept going.
        env = smoothstep(x / 0.85) ** 1.6 * (1.0 - smoothstep((x - 0.86) / 0.14))
        mix.add(t0, raw * env, pan=pan, gain=level)

    for w in cues["waves"]:
        pan = math.cos(math.radians(w["sector"])) * 0.6
        whoosh(sc.t(w["spawn"]), sc.t(w["land_first"]), 400, 4800, pan, 0.045)

    for h in cues["heroes"]:
        pan = math.cos(math.radians(h["sector"]))
        t0, t1 = sc.t(h["spawn"]), sc.t(h["land"])
        whoosh(t0, t1, 200, 5200, pan * 0.8, 0.085)
        # The seat: a heavier version of the same tick, because it is the same event.
        v = CLASS_VOICE[h["cls"]]
        note = sc.note_for(t1, v["octave"] - 1, index=0)
        s = tick(h["cls"], midi_hz(note), gen, "cold")
        mix.add(t1, s, pan=pan * 0.4, gain=0.85)
        # A short low bloom under the seat, so a hero landing has a floor the swarm does not.
        n = int(1.4 * SR)
        bloom = partial(n, midi_hz(note - 12), 0.45) * 0.5
        mix.add(t1, spectral(bloom, lambda f: lowpass(f, 320, 2)), pan=0.0, gain=0.30)


def layer_finale(mix: Mix, sc: Score, cues: dict):
    """The three light rakes at the end. The camera is retreating and nothing lands any more,
    so these are the only events left -- soft, wide, and pitched high enough to stay out of
    the way of the music resolving underneath them."""
    gen = rng_for("finale")
    rakes = [p["frame"] for p in cues["probes"] if "rake" in p["caption"]]
    for k, f in enumerate(rakes):
        t0 = sc.t(f)
        n = int(2.2 * SR)
        sh = np.zeros(n)
        for deg, base in sc.chord_at(t0):
            sh += partial(n, midi_hz(scale_note(deg, base + 2)), 0.9) * 0.5
        sh *= smoothstep(np.arange(n) / (0.5 * SR))
        sh += spectral(noise(n, gen), lambda f_: bandpass(f_, 4000, 12000, 2)) \
            * np.exp(-np.arange(n) / SR / 0.5) * 0.25
        mix.add(t0, spectral(sh, lambda f_: highpass(f_, 1500, 2)),
                pan=(-0.5, 0.45, -0.2)[k % 3], gain=0.055)


# ------------------------------------------------------------------------- mastering


def k_weight(x: np.ndarray) -> np.ndarray:
    """ITU-R BS.1770 K-weighting: the 1681 Hz high shelf, then the 38 Hz high-pass. Applied
    in the frequency domain, which is exact for the steady state and well inside the
    tolerance that matters for an integrated measurement."""
    n = len(x)
    w = 2 * math.pi * np.fft.rfftfreq(n, 1.0 / SR) / SR
    z = np.exp(-1j * w)
    shelf_b = (1.53512485958697, -2.69169618940638, 1.19839281085285)
    shelf_a = (1.0, -1.69065929318241, 0.73248077421585)
    hp_b = (1.0, -2.0, 1.0)
    hp_a = (1.0, -1.99004745483398, 0.99007225036621)

    def h(b, a):
        return ((b[0] + b[1] * z + b[2] * z ** 2) / (a[0] + a[1] * z + a[2] * z ** 2))

    return np.fft.irfft(np.fft.rfft(x) * h(shelf_b, shelf_a) * h(hp_b, hp_a), n)


def lufs(stereo: np.ndarray) -> float:
    """Gated integrated loudness, BS.1770-4: 400 ms blocks at 75 % overlap, absolute gate at
    -70 LUFS, then a relative gate 10 LU below the ungated mean."""
    kw = np.stack([k_weight(stereo[0]), k_weight(stereo[1])])
    block, hop = int(0.4 * SR), int(0.1 * SR)
    n = (kw.shape[1] - block) // hop + 1
    power = np.empty(n)
    for i in range(n):
        seg = kw[:, i * hop:i * hop + block]
        power[i] = np.sum(np.mean(seg ** 2, axis=1))
    with np.errstate(divide="ignore"):
        loud = -0.691 + 10 * np.log10(np.maximum(power, 1e-30))
    keep = loud > -70.0
    if not keep.any():
        return -np.inf
    gate = -0.691 + 10 * np.log10(power[keep].mean()) - 10.0
    keep &= loud > gate
    return -0.691 + 10 * np.log10(power[keep].mean())


def true_peak_db(stereo: np.ndarray) -> float:
    """4x-oversampled peak, polyphase so it costs one convolution per phase rather than a
    16-million-sample one."""
    taps = 64
    m = np.arange(-taps, taps + 1)
    proto = np.sinc(m / 4.0) * np.hanning(2 * taps + 1)
    peak = 0.0
    for ch in stereo:
        for phase in range(4):
            sub = proto[phase::4]
            peak = max(peak, np.abs(np.convolve(ch, sub, mode="same")).max())
    return 20 * math.log10(max(peak, 1e-12))


def limit(stereo: np.ndarray, ceiling_db: float):
    """Lookahead peak limiter: a smoothed gain curve rather than clipping, so transients
    round off instead of splintering. Returns the audio and the number of samples the
    backstop clip still had to touch, which is reported rather than hidden -- a smoothed
    envelope can undershoot a lone spike, and it is worth knowing when it does."""
    ceiling = 10 ** (ceiling_db / 20.0)
    peak = np.maximum(np.abs(stereo[0]), np.abs(stereo[1]))
    over = np.maximum(peak / ceiling, 1.0)
    w = int(0.010 * SR)
    # Sliding maximum first, so the gain is genuinely down across the whole window a spike
    # sits in, then two short averages to round the corners the max filter leaves.
    env = np.maximum(movavg(movavg(slide_max(over, w), w // 2), w // 2), 1.0)
    out = stereo / env
    clipped = int(np.count_nonzero(np.abs(out) > ceiling))
    return np.clip(out, -ceiling, ceiling), clipped


def master(stereo: np.ndarray, target_lufs: float, ceiling_db: float):
    """Converge on the loudness target *and* the true-peak ceiling together.

    Doing it in one pass does not work: normalising to the target overshoots the ceiling,
    and pulling the whole mix down to fix that undershoots the target. So the gain chases the
    loudness and the limiter's own ceiling chases the inter-sample peaks, and both are
    re-measured every round rather than predicted.
    """
    gain = 10 ** ((target_lufs - lufs(stereo)) / 20.0)
    head = ceiling_db - 0.3
    out, clipped, loud, tp = stereo, 0, -np.inf, 0.0
    for _ in range(6):
        out, clipped = limit(stereo * gain, head)
        loud, tp = lufs(out), true_peak_db(out)
        if tp > ceiling_db:
            head -= (tp - ceiling_db) + 0.05
            continue
        if abs(loud - target_lufs) < 0.12:
            break
        gain *= 10 ** ((target_lufs - loud) / 20.0)
    return out, loud, tp, clipped


# ------------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", type=Path, default=Path("out/audio/cues.json"))
    ap.add_argument("--flow", type=Path, default=Path("out/audio/flow.csv"))
    ap.add_argument("--variant", choices=("cold", "warm", "cine"), default="cold")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--lufs", type=float, default=-14.0, help="YouTube's target")
    ap.add_argument("--peak", type=float, default=-1.0, help="dBTP ceiling")
    ap.add_argument("--no-sfx", action="store_true",
                    help="music (and narration) only -- no effects at all")
    ap.add_argument("--voice", type=Path, help="directory of vo_<frame>.wav from narrate.py")
    args = ap.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    flow = np.array([float(r["flow"]) for r in csv.DictReader(args.flow.open())])
    sc = Score(cues)
    mix = Mix(cues["duration"])
    print(f"{args.variant}: {cues['duration']:.2f} s, bar = {BAR_FRAMES} frames "
          f"({60.0 / (sc.bar / BEATS_PER_BAR):.3f} BPM), grid starts frame "
          f"{sc.bar0_frame} ({sc.bar_time(0):.3f} s)")
    for name, b in (("ADC lands", 12), ("Teensy lands", 18)):
        print(f"  bar {b:2d} at {sc.bar_time(b):7.3f} s  <- {name}")

    # Effects first: the landing density they produce is what the music reads. With --no-sfx
    # the density is still computed -- the pad still has to duck under the swarm and the pulse
    # still has to follow it, whether or not anything is audibly landing.
    if not args.no_sfx:
        layer_fabrication(mix, sc, cues)
    busy = layer_components(mix, sc, cues, args.variant, emit=not args.no_sfx)
    if not args.no_sfx:
        layer_flights(mix, sc, cues)
        layer_finale(mix, sc, cues)
        mix.add_stereo(0.0, np.stack([layer_air(mix, sc, flow)] * 2), gain=1.0)

    # The sustained layers are rendered per channel with independent phases -- decorrelated,
    # not panned. The pulse stays centred: it is the grid, and a grid that wanders is worse
    # than a narrow one.
    music = np.stack([layer_pedal(mix, sc, args.variant, ch)
                      + layer_pad(mix, sc, args.variant, busy, ch) for ch in (0, 1)])
    music += layer_structure(mix, sc, args.variant)
    music += layer_pulse(mix, sc, args.variant, busy)
    if args.variant == "cine":
        music += layer_cine_bed(mix, sc)

    # The camera never stops on the last frame, so neither does the music: it decays out
    # rather than ending. The fades belong to the music alone -- the last line runs to 83.25 s
    # and a master fade from 81.4 would pull the narrator down inside the one sentence that
    # carries the specification.
    music *= (1.0 - fade(mix.t, cues["duration"] - 2.6, cues["duration"]) ** 0.7)
    music *= fade(mix.t, 0.0, 1.2)

    if args.voice:
        voice, duck = layer_voice(mix, sc, args.voice)
        music *= duck
        mix.add_stereo(0.0, voice, gain=1.0)
        print(f"  narration ducks the music by {-20 * math.log10(float(duck.min())):.1f} dB "
              f"at most, over {(duck < 0.9).mean() * 100:.0f} % of the film")
    mix.add_stereo(0.0, music, gain=0.85)

    out = mix.buf
    # A short safety fade at each end, under the voice rather than over it: enough to stop a
    # click on the cut, too short to be heard as a fade.
    out *= fade(mix.t, 0.0, 0.06) * (1.0 - fade(mix.t, cues["duration"] - 0.12,
                                                cues["duration"]))
    # Below 40 Hz there is nothing a laptop, a phone or a projector can reproduce, and on the
    # systems that can it is felt rather than heard. Cutting it steeply is free level
    # everywhere else in the mix.
    out = np.stack([spectral(ch, lambda f: highpass(f, 40, 3)) for ch in out])

    out, final_l, final_tp, clipped = master(out, args.lufs, args.peak)

    write_wav24(args.out, out)
    print(f"  wrote {args.out}  {final_l:+.2f} LUFS, {final_tp:+.2f} dBTP "
          f"(targets {args.lufs:+.1f} / {args.peak:+.1f}), "
          f"{clipped} sample(s) hit the backstop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
