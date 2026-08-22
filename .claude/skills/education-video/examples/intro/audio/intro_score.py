"""Synthesise the intro film's soundtrack from the film's own nine-scene cut.

    python video/tools/intro_score.py --out video/out/audio/score.wav
    python video/tools/intro_score.py --no-voice --window 0 60 --variant warm \
        --out video/out/audio/sample.wav

Nothing is sampled and nothing is placed by ear: every structural moment is a scene boundary
out of `intro_cues.py`, and every narration line sits at the timecode the script gives it.
numpy and the standard library only, plus the shared engine in `video/engine`.

**F major, and the harmony moves.** The first version of this file borrowed the assembly film's
pitch set -- D E F G A C over a D drone -- and was rejected in one word: depressing. It earned
it. That set contains the minor third, so every chord in it was a D minor chord, and a static
pedal under a slow sine pad is the texture of a requiem. This one is in F major, uses only
major and suspended chords (no minor triad appears anywhere), gives every scene a progression
that cycles rather than one chord that sits, and moves the bass note with it. The brief is warm
and welcoming, so:

  A plucked arpeggio carries it, not a drone. A struck tone with a 0.5 s decay running eighth
  notes through the chord is what makes a bed feel alive; a held pad is what makes one feel
  like weather. The pad is still there, underneath, as glue.

  The bass moves every two bars. One note per chord, following the progression. A root that
  never changes for five and a half minutes is the single biggest reason the first cut sounded
  like mourning.

  No scene is sad, including the one about failure. `Blind` is the scene where the instrument
  is being fooled, and it says so with a suspended chord that will not resolve until the scene
  ends -- tension, which is not the same as sorrow. `Tie` alternates IV and V and resolves to
  neither, because two candidates that will not separate is an unfinished thought, not a sad
  one. `Join` resolves to I with the ninth open, which is the sound of an invitation.

  Each scene still holds a whole number of bars of its own (`intro_cues.py` divides its
  length), so no bar crosses a cut and there is no tempo map.

The music is levelled to its own loudness target and the narration to its, so the distance
between them is set once and survives mastering; then the whole mix is taken to -14 LUFS /
-1 dBTP by the engine's BS.1770-4 meter and true-peak limiter.
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

from dsp import (SR, bell, highpass, lowpass, movavg, read_wav,  # noqa: E402
                 shelf, slide_max, spectral, write_wav24)
from mix_audio import (Mix, fade, lufs, master, midi_hz, partial,  # noqa: E402
                       rng_for, smoothstep)

DUCK_DB = 8.0
XFADE = 2.0

# F2. Low enough to be a bass, high enough that a laptop reproduces it -- 87.3 Hz, where the
# first cut's 36.7 Hz pedal was inaudible on everything and still owned the peaks.
ROOT = 41

# Chords as semitones above the root, named by degree. Every one is major or suspended: the
# minor triad is absent from the whole film on purpose, and that is the difference between
# this and the version that was rejected.
I = (0, 4, 7, 14)             # F A C  + the ninth (G), which is the warmth
I7 = (0, 4, 7, 11)            # Fmaj7  -- softer, used where the film is settled
IV = (5, 9, 12, 19)           # Bb D F + the ninth (C)
V = (7, 11, 14, 21)           # C E G  + the ninth (D)
SUS = (7, 12, 14, 19)         # Csus4  -- C F G, unresolved without being sad

# One entry per scene, in the film's order.
#   prog       chords, cycled every `bars` bars
#   pluck      density of the arpeggio, 0 = silent
#   level      the whole scene's weight
#   mark       the section bell at the cut
SCENES = {
    "Opening":   dict(prog=(I,), bars=4, pluck=0.35, level=0.70, mark=0.0),
    "Target":    dict(prog=(IV, I), bars=4, pluck=0.75, level=0.90, mark=0.55, shimmer=True),
    "Loop":      dict(prog=(I, IV, V, IV), bars=4, pluck=1.00, level=1.00, mark=0.70),
    "Stability": dict(prog=(I7, V), bars=4, pluck=0.70, level=0.85, mark=0.60),
    "Blind":     dict(prog=(SUS, IV), bars=5, pluck=0.30, level=0.80, mark=0.50),
    "Ruler":     dict(prog=(I, IV), bars=7, pluck=0.55, level=0.90, mark=0.60, converge=6.0),
    "Arms":      dict(prog=(IV, I, V, I), bars=4, pluck=1.00, level=1.00, mark=0.85,
                      shimmer=True),
    "Tie":       dict(prog=(IV, V), bars=4, pluck=0.60, level=0.85, mark=0.60),
    "Join":      dict(prog=(I, IV, V, I), bars=4, pluck=0.85, level=1.00, mark=0.75),
}

# The arpeggio's shape: indices into the chord, up and back down, so it turns around rather
# than running off the top. A pattern that repeats every six eighths against a four-beat bar
# lands differently in each bar, which is what stops it sounding like a loop.
PATTERN = (0, 1, 2, 3, 2, 1)
VELOCITY = (1.0, 0.72, 0.84, 0.68, 0.80, 0.66)

VARIANTS = {
    # tone      pluck partials + decay      register  arpeggio subdivision
    "warm": dict(stack=((1.0, 1.0, 0.55), (2.0, 0.34, 0.34), (3.01, 0.11, 0.20),
                        (4.98, 0.04, 0.12)), octave=2, div=8, pad_cut=3000.0, shimmer=0.020,
                 why="music box: soft strike, long-ish decay, few partials"),
    "bright": dict(stack=((1.0, 1.0, 0.40), (2.0, 0.46, 0.26), (3.01, 0.22, 0.16),
                          (4.98, 0.10, 0.10), (7.02, 0.04, 0.06)), octave=2, div=12,
                   pad_cut=4200.0, shimmer=0.030,
                   why="electric piano: more partials, faster arpeggio, more air"),
    "open": dict(stack=(), octave=2, div=8, pad_cut=3400.0, shimmer=0.026,
                 why="no arpeggio at all: warm pad and a moving bass, wide and slow"),
}


def chord_at(s: dict, t: float):
    """The chord sounding at t inside a scene, from its progression and bar length."""
    sc = SCENES[s["name"]]
    k = int(max(0.0, t - s["start"]) / (s["bar"] * sc["bars"]))
    return sc["prog"][k % len(sc["prog"])]


def chord_spans(s: dict):
    """Every (start, end, chord) block in a scene, so each layer can render blocks rather than
    evaluate a chord per sample."""
    sc = SCENES[s["name"]]
    span = s["bar"] * sc["bars"]
    out, t = [], s["start"]
    while t < s["end"] - 1e-6:
        out.append((t, min(t + span, s["end"]), chord_at(s, t + 1e-6)))
        t += span
    return out


def layer_bass(mix: Mix, scenes: list) -> np.ndarray:
    """One note per chord, an octave below the pad. Warm rather than deep: a sine with a second
    harmonic on it and a slow attack, so it arrives rather than thumps."""
    out = np.zeros(mix.n)
    gen = rng_for("intro-bass")
    for s in scenes:
        for t0, t1, chord in chord_spans(s):
            hz = midi_hz(ROOT + chord[0])
            a, b = int(t0 * SR), min(mix.n, int((t1 + 0.6) * SR))
            if b <= a:
                continue
            t = (np.arange(b - a)) / SR
            v = (np.sin(2 * math.pi * hz * t + gen.uniform(0, 6.28))
                 + 0.28 * np.sin(2 * math.pi * hz * 2 * t + gen.uniform(0, 6.28))
                 + 0.08 * np.sin(2 * math.pi * hz * 3 * t + gen.uniform(0, 6.28)))
            # Attack over 0.25 s, hold, then release into the next chord's attack.
            env = smoothstep(t / 0.25) * (1.0 - smoothstep((t - (t1 - t0)) / 0.6))
            out[a:b] += v * env * SCENES[s["name"]]["level"]
    return spectral(out, lambda f: lowpass(f, 900, 2) * highpass(f, 55, 2)) * 0.085


def layer_pad(mix: Mix, scenes: list, variant: dict, ch: int) -> np.ndarray:
    """The chord itself, held, as glue under the arpeggio. Warm stack -- harmonics 1 to 5 with
    a gentle roll-off -- rather than the glassy stretched partials the first cut used.

    Rendered once per channel with its own phases: two decorrelated renders of the same notes
    are real width, whereas panning one mono render to both sides is none at all.
    """
    out = np.zeros(mix.n)
    for s in scenes:
        sc = SCENES[s["name"]]
        gen = rng_for(f"intro-pad-{s['name']}-{ch}")
        for t0, t1, chord in chord_spans(s):
            a = max(0, int((t0 - XFADE / 2) * SR))
            b = min(mix.n, int((t1 + XFADE / 2) * SR))
            if b <= a:
                continue
            t = mix.t[a:b]
            env = (fade(t, t0 - XFADE / 2, t0 + XFADE / 2)
                   * (1.0 - fade(t, t1 - XFADE / 2, t1 + XFADE / 2)))
            seg = np.zeros(b - a)
            for k, semi in enumerate(chord):
                hz = midi_hz(ROOT + 12 + semi)
                cents = 0.0
                if "converge" in sc and k == len(chord) - 1:
                    # Ratiometric cancellation: two voices six cents apart at the cut,
                    # converging to unison as the point lands, so the beat between them slows
                    # to nothing rather than being switched off.
                    u = (t - s["start"]) / s["dur"]
                    cents = sc["converge"] * (1.0 - smoothstep(u)) ** 1.5
                    seg += voice(hz, t - t0, 0.0, gen) * 0.5
                seg += voice(hz, t - t0, cents, gen)
            out[a:b] += seg * env / len(chord) * sc["level"]
    out = spectral(out, lambda f: lowpass(f, variant["pad_cut"], 2) * highpass(f, 110, 2)
                   * shelf(f, 320, 2.0, low=True))
    return out * 0.055


def voice(hz: float, t: np.ndarray, cents, gen) -> np.ndarray:
    """One held note, warm stack. `cents` may be an array, which is what makes the convergence
    continuous; the phase is integrated so a moving pitch cannot click."""
    out = np.zeros_like(t)
    ratio = 2.0 ** (np.asarray(cents) / 1200.0)
    for h, amp in ((1.0, 1.0), (2.0, 0.42), (3.0, 0.22), (4.0, 0.11), (5.0, 0.05)):
        lfo = 0.88 + 0.12 * np.sin(2 * math.pi * gen.uniform(0.03, 0.08) * t
                                   + gen.uniform(0, 6.28))
        if np.ndim(ratio):
            ph = 2 * math.pi * np.cumsum(np.full_like(t, hz * h) * ratio) / SR
        else:
            ph = 2 * math.pi * hz * h * ratio * t
        out += np.sin(ph + gen.uniform(0, 6.28)) * amp * lfo
    return out


def pluck(hz: float, variant: dict, gen) -> np.ndarray:
    """One struck note. Fast attack, partials that decay at their own rates -- the top ones
    first, which is what a struck object does and what a sine with an envelope does not."""
    stack = variant["stack"]
    n = int(max(d for _h, _a, d in stack) * 4.2 * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for h, amp, dec in stack:
        out += np.sin(2 * math.pi * hz * h * tt + gen.uniform(0, 6.28)) * amp * np.exp(-tt / dec)
    # 1.5 ms of noise at the strike. Almost inaudible alone; it is the difference between a
    # note starting and an object being hit.
    out += gen.standard_normal(n) * np.exp(-tt / 0.0015) * 0.05
    # The attack, so nothing clicks: 3 ms is a hammer, not a fade.
    out *= np.clip(tt / 0.003, 0.0, 1.0)
    return spectral(out, lambda f: highpass(f, 200, 2) * lowpass(f, 9000, 2))


def layer_pluck(mix: Mix, scenes: list, variant: dict):
    """The arpeggio, eighth notes (or triplets) through the chord that is sounding. Returns
    stereo: consecutive notes alternate slightly left and right, which is what gives a music
    box its width without any reverb."""
    if not variant["stack"]:
        return np.zeros((2, mix.n))
    out = np.zeros((2, mix.n))
    gen = rng_for("intro-pluck")
    for s in scenes:
        sc = SCENES[s["name"]]
        if sc["pluck"] <= 0:
            continue
        step = s["bar"] / variant["div"]
        k = 0
        while True:
            t0 = s["start"] + k * step
            if t0 >= s["end"]:
                break
            chord = chord_at(s, t0 + 1e-6)
            idx = PATTERN[k % len(PATTERN)]
            semi = chord[idx % len(chord)] + 12 * (idx // len(chord))
            hz = midi_hz(ROOT + 12 * variant["octave"] + semi)
            amp = VELOCITY[k % len(VELOCITY)] * sc["pluck"] * sc["level"]
            # In and out over two bars at each end of the scene, so the arpeggio arrives and
            # leaves instead of switching on.
            u = min((t0 - s["start"]) / (2 * s["bar"]), (s["end"] - t0) / (2 * s["bar"]), 1.0)
            note = pluck(hz, variant, gen) * amp * max(u, 0.0)
            pan = 0.30 * (1 if k % 2 else -1) * (0.6 + 0.4 * (idx / 3.0))
            ang = (pan + 1.0) * math.pi / 4.0
            i = int(t0 * SR)
            j = min(mix.n, i + len(note))
            if j > i:
                out[0, i:j] += note[:j - i] * math.cos(ang)
                out[1, i:j] += note[:j - i] * math.sin(ang)
            k += 1
    return out * 0.070


def layer_marks(mix: Mix, scenes: list) -> np.ndarray:
    """One bell at each scene boundary, and nothing else anywhere. Nine events in five and a
    half minutes; the film has nine sections and this is the only layer that says so. Each
    lands in the gap the film's own cut already leaves before the next line.

    Tuned to the chord the new scene opens on, with the partials only lightly stretched -- a
    struck-metal series is bright and a little sour, and this one is meant to be a welcome.
    """
    out = np.zeros((2, mix.n))
    for s in scenes:
        sc = SCENES[s["name"]]
        if sc["mark"] <= 0 or s["start"] < 0.05:
            continue
        chord = sc["prog"][0]
        n = int(6.0 * SR)
        b = np.zeros((2, n))
        for k, semi in enumerate(chord):
            hz = midi_hz(ROOT + 24 + semi)
            v = np.zeros(n)
            for h, amp, dec in ((1.0, 1.0, 2.8), (2.0, 0.34, 1.3), (4.01, 0.10, 0.6)):
                v += partial(n, hz * h, dec * (0.8 + 0.2 * k)) * amp
            pan = (k / max(len(chord) - 1, 1) - 0.5) * 0.8
            ang = (pan + 1.0) * math.pi / 4.0
            b[0] += v * math.cos(ang)
            b[1] += v * math.sin(ang)
        i = int(s["start"] * SR)
        k = min(n, mix.n - i)
        if k > 0:
            out[:, i:i + k] += b[:, :k] / len(chord) * sc["mark"]
    return np.stack([spectral(c, lambda f: highpass(f, 250, 2)) for c in out]) * 0.045


def layer_shimmer(mix: Mix, scenes: list, variant: dict) -> np.ndarray:
    """Air over the two scenes that open out: the plot zooming four decades, and the hero shot
    of the board. High enough to stay clear of speech entirely."""
    out = np.zeros(mix.n)
    for s in scenes:
        sc = SCENES[s["name"]]
        if not sc.get("shimmer"):
            continue
        a, b = max(0, int(s["start"] * SR)), min(mix.n, int(s["end"] * SR))
        if b <= a:
            continue
        t = mix.t[a:b]
        gen = rng_for(f"intro-shimmer-{s['name']}")
        seg = np.zeros(b - a)
        for semi in sc["prog"][0]:
            hz = midi_hz(ROOT + 36 + semi)
            seg += np.sin(2 * math.pi * hz * (t - s["start"]) + gen.uniform(0, 6.28)) * 0.5
        u = np.clip((t - s["start"]) / max(s["dur"], 1e-6), 0, 1)
        out[a:b] += spectral(seg, lambda f: bell(f, 3000, 3.0, 1.2) * highpass(f, 1800, 2)) \
            * np.sin(math.pi * u) ** 0.8
    return out * variant["shimmer"]


def place_voice(mix: Mix, vo: Path, offset: float):
    """The narration, placed from `narration.json` -- which carries the exact start of every
    line, including the one that had to begin early to fit. Returns the stereo voice bus and
    the gain curve the music follows.

    The duck holds across a whole sentence instead of pumping between syllables: it opens 0.4 s
    before he starts and closes 0.8 s after he stops, which is a mix move rather than an
    audible one.
    """
    meta = json.loads((vo / "narration.json").read_text(encoding="utf-8"))
    files = {int(p.stem.split("_")[1]): p for p in vo.glob("vo_*.wav")}
    mono = np.zeros(mix.n)
    used = 0
    for line in meta["lines"]:
        p = files.get(line["frame"])
        if p is None:
            raise SystemExit(f"{vo}: narration.json expects vo_{line['frame']:04d}.wav")
        i = int(round((line["start"] - offset) * SR))
        x = read_wav(p)[0]
        if i + len(x) <= 0 or i >= mix.n:
            continue
        a = max(0, i)
        x = x[max(0, -i):]
        k = min(len(x), mix.n - a)
        if k > 0:
            mono[a:a + k] += x[:k]
            used += 1
    env = movavg(np.abs(mono), int(0.05 * SR))
    env = movavg(slide_max(env, int(1.2 * SR)), int(0.4 * SR))
    presence = np.clip(env / max(np.percentile(env, 99), 1e-9), 0.0, 1.0) ** 0.5
    duck = 10 ** (-DUCK_DB * presence / 20.0)
    # Centred, and mono on purpose: a documentary narrator sits in the middle of the picture.
    # The only thing done to him here is the low cut, at the frequency the bass lives.
    v = spectral(mono, lambda f: highpass(f, 85, 2))
    return np.stack([v, v]), duck, meta, used


def to_lufs(x: np.ndarray, target: float) -> np.ndarray:
    return x * 10 ** ((target - lufs(x)) / 20.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", type=Path, default=OUT / "audio" / "cues.json")
    ap.add_argument("--vo", type=Path, default=OUT / "audio" / "vo")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--variant", choices=tuple(VARIANTS), default="warm")
    ap.add_argument("--no-voice", action="store_true", help="music only")
    ap.add_argument("--window", type=float, nargs=2, metavar=("FROM", "TO"),
                    help="render only this stretch, for auditioning a variant quickly")
    ap.add_argument("--music-lufs", type=float, default=-27.0,
                    help="the bed's own loudness before mastering")
    ap.add_argument("--voice-lufs", type=float, default=-16.0,
                    help="the narration's own loudness before mastering")
    ap.add_argument("--lufs", type=float, default=-14.0, help="final target; YouTube's")
    ap.add_argument("--peak", type=float, default=-1.0, help="dBTP ceiling")
    args = ap.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    variant = VARIANTS[args.variant]
    full = cues["duration"]
    lo, hi = args.window if args.window else (0.0, full)
    scenes = []
    for s in cues["scenes"]:
        if s["end"] <= lo or s["start"] >= hi:
            continue
        t = dict(s)
        t["start"] -= lo
        t["end"] -= lo
        scenes.append(t)
    mix = Mix(hi - lo)
    print(f"{args.variant}: {variant['why']}")
    print(f"  {hi - lo:.2f} s of {full:.2f} s, {len(scenes)} scene(s), root "
          f"{midi_hz(ROOT):.2f} Hz, arpeggio 1/{variant['div']} of a bar")
    for s in scenes:
        sc = SCENES[s["name"]]
        names = "-".join({str(I): "I", str(I7): "I7", str(IV): "IV", str(V): "V",
                          str(SUS): "sus"}.get(str(c), "?") for c in sc["prog"])
        print(f"  {s['start'] + lo:7.2f} {s['name']:10s} {s['bars']:3d} bars  {names:14s}"
              f" every {sc['bars']} bars  pluck {sc['pluck']:.2f}  mark {sc['mark']:.2f}")

    music = np.stack([layer_pad(mix, scenes, variant, ch) for ch in (0, 1)])
    for mono_layer in (layer_bass(mix, scenes), layer_shimmer(mix, scenes, variant)):
        music += np.stack([mono_layer, mono_layer])
    music += layer_pluck(mix, scenes, variant)
    music += layer_marks(mix, scenes)
    # In and out, and only where the film actually starts and ends.
    if lo <= 0.05:
        music *= fade(mix.t, 0.0, 2.0)
    if hi >= full - 0.05:
        music *= 1.0 - fade(mix.t, (hi - lo) - 3.5, hi - lo) ** 0.7
    music = to_lufs(music, args.music_lufs)
    print(f"  music bed at {lufs(music):+.2f} LUFS on its own")

    out = music
    if not args.no_voice:
        v, duck, meta, used = place_voice(mix, args.vo, lo)
        out = music * duck + to_lufs(v, args.voice_lufs)
        print(f"  {used} line(s) of {meta['voice']} placed, chain {meta['chain']}; the bed "
              f"ducks {-20 * math.log10(float(duck.min())):.1f} dB under him over "
              f"{(duck < 0.9).mean() * 100:.0f} % of it")

    # Nothing under 40 Hz survives a laptop, a phone or a projector, and on the systems that
    # can reproduce it it is felt rather than heard. Cutting it is free level everywhere else.
    out = np.stack([spectral(c, lambda f: highpass(f, 40, 3)) for c in out])
    out, loud, tp, clipped = master(out, args.lufs, args.peak)
    write_wav24(args.out, out)
    print(f"  wrote {args.out}  {loud:+.2f} LUFS, {tp:+.2f} dBTP, "
          f"{clipped} sample(s) hit the backstop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
