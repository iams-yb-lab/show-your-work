"""Voice processing. Two halves, and only one of them is still current.

🔴 **`saturate`, `drift`, `room_ir`, `breath` and `humanise` are a rejected experiment.** They
exist to manufacture humanity after synthesis, and that whole idea was rejected twice: the
outputs read as "very AI", and a later early-reflection pass was "a robot with echoes". Do not
reach for them in new work. They stay for reproducing historical cuts — the assembly film's
pre-v7.2 mixes and the intro film's `scored.mp4` were made with them.

`deess` and `compress` are ordinary corrective tools and carry no such verdict.

The current method is in [`../natural-voice/README.md`](../natural-voice/README.md): preserve a
convincing model performance, its endings and its bandwidth, then apply minimal corrective EQ.
Nothing downstream tries to add realism.

The rejected half's original hypothesis is kept below, because knowing *why* it was tried is
what stops it being tried again.

Make synthesised speech sound like a person in a room, rather than a file.

Neural TTS is intelligible and well-acted and still reads as a machine, and the reasons are
mostly not the voice model:

  It is perfectly dry. No recording of a human has ever had no room in it. The ear uses early
  reflections to place a speaker in space, and when there are none the voice sits nowhere --
  which is the single largest tell, and the cheapest to fix.

  It has no microphone. A narrator works a cardioid a hand's width away, which lifts the chest
  around 150 Hz by a couple of dB, and the resulting signal is compressed and lightly
  saturated on the way to tape. None of that happens to a WAV that came off an API.

  It is metronomic. Every phrase gets the same measured delivery, and the gaps between
  sentences are identical. Humans vary their rate constantly and pause irregularly.

  It never breathes. A narrator audibly takes air before a long line. TTS never does, and
  after 84 seconds the absence is felt even when it is not noticed.

So the chain is: de-ess, chest lift, presence, compress, saturate, drift, room. Plus breaths,
which the mixer places because they belong to the gaps between lines rather than to the lines.
Every stage is deliberately gentle -- the goal is to stop it sounding processed, and stacking
obvious processing is a way to make something sound more processed, not less.
"""

from __future__ import annotations

import numpy as np

from dsp import SR, bell, convolve_fft, highpass, lowpass, movavg, shelf, slide_max, spectral


def deess(x: np.ndarray, thresh_db: float = -30.0, ratio: float = 3.0) -> np.ndarray:
    """Duck 5-9 kHz only while it is loud. TTS sibilance is consistent and hot, and a static
    cut would dull every vowel to fix a few consonants."""
    sib = spectral(x, lambda f: (f >= 4500) * lowpass(f, 9500, 2))
    env = movavg(slide_max(np.abs(sib), int(0.004 * SR)), int(0.010 * SR))
    over_db = 20 * np.log10(np.maximum(env, 1e-9)) - thresh_db
    cut_db = np.minimum(over_db, 0.0) * 0.0 + np.maximum(over_db, 0.0) * (1.0 / ratio - 1.0)
    return x + sib * (10 ** (cut_db / 20.0) - 1.0)


def compress(x: np.ndarray, thresh_db: float = -24.0, ratio: float = 3.5,
             attack: float = 0.008, release: float = 0.16) -> np.ndarray:
    """A broadcast-ish compressor. Not for loudness -- for the *sound* of one: consonants held
    back, tails pulled up, so the voice stays in one place instead of breathing in level."""
    env = slide_max(np.abs(x), int(attack * SR))
    env = movavg(env, int(release * SR))
    lvl = 20 * np.log10(np.maximum(env, 1e-9))
    over = np.maximum(lvl - thresh_db, 0.0)
    gain_db = -over * (1.0 - 1.0 / ratio)
    # Make-up, so the chain does not quietly change the level the mixer was tuned against.
    return x * 10 ** ((gain_db + over.max() * (1.0 - 1.0 / ratio) * 0.6) / 20.0)


def saturate(x: np.ndarray, amount: float = 1.25) -> np.ndarray:
    """🔴 REJECTED — manufactures humanity after synthesis; see the module
    docstring. Kept for historical cuts only.

    A whisper of odd-order curve. Adds the harmonics a preamp would and, more usefully,
    rounds the hardest consonant peaks so they stop sounding digitally exact."""
    return np.tanh(x * amount) / np.tanh(amount)


def drift(x: np.ndarray, cents: float = 4.0, seed: int = 7) -> np.ndarray:
    """🔴 REJECTED — manufactures humanity after synthesis; see the module
    docstring. Kept for historical cuts only.

    Micro pitch drift, by modulating a fractional delay with two slow incommensurate LFOs.

    A perfectly steady pitch is the giveaway that nothing physical produced it. Four cents is
    below the threshold of hearing it *as* pitch movement; what it removes is the steadiness.
    Two LFOs rather than one, because a single sine reads as vibrato.
    """
    gen = np.random.default_rng(seed)
    t = np.arange(len(x)) / SR
    ratio = cents / 1200.0 * np.log(2) * 12 / 12          # fractional pitch deviation
    lfo = np.zeros(len(x))
    for hz, w in ((0.27, 0.6), (0.41, 0.4)):
        lfo += w * np.sin(2 * np.pi * hz * t + gen.uniform(0, 6.28))
    delay = lfo * (ratio / (2 * np.pi * 0.30)) * SR       # samples
    idx = np.clip(np.arange(len(x)) - delay, 0, len(x) - 1)
    return np.interp(idx, np.arange(len(x)), x)


def room_ir(seconds: float = 0.42, seed: int = 3):
    """🔴 REJECTED — manufactures humanity after synthesis; see the module
    docstring. Kept for historical cuts only.

    A small, dead-ish narration room: a handful of early reflections, then a short diffuse
    tail rolled off top and bottom. Returned as a stereo pair from two noise draws, which is
    what makes the room wider than the voice standing in it."""
    gen = np.random.default_rng(seed)
    n = int(seconds * SR)
    out = []
    for ch in range(2):
        h = np.zeros(n)
        # Early reflections: a few surfaces, 9-46 ms out, alternating sign as real ones do.
        for ms, amp in ((9.3, 0.38), (13.7, -0.30), (19.1, 0.24), (27.4, -0.19),
                        (33.8, 0.15), (41.2, -0.12), (46.0, 0.09)):
            i = int((ms + ch * 1.7) * SR / 1000)
            if i < n:
                h[i] += amp
        # Diffuse tail. RT60 about 0.42 s, which is a treated room and not a hall.
        tail = gen.standard_normal(n) * np.exp(-np.arange(n) / SR / 0.068)
        h += tail * 0.30
        h = spectral(h, lambda f: lowpass(f, 5200, 2) * highpass(f, 220, 2))
        out.append(h / np.abs(h).sum() * 1.6)
    return out


def breath(duration: float = 0.34, seed: int = 11) -> np.ndarray:
    """🔴 REJECTED — manufactures humanity after synthesis; see the module
    docstring. Kept for historical cuts only.

    An inhale. Filtered noise with a slow rise and a faster fall, which is the shape of air
    through a throat and nothing like the shape of a click."""
    gen = np.random.default_rng(seed)
    n = int(duration * SR)
    t = np.arange(n) / SR
    x = gen.standard_normal(n)
    x = spectral(x, lambda f: bell(f, 700, 6.0, 0.8) * bell(f, 2400, 4.0, 1.2)
                 * lowpass(f, 4800, 2) * highpass(f, 320, 2))
    env = (t / (duration * 0.62)) ** 1.5 * np.exp(-np.maximum(t - duration * 0.62, 0) / 0.09)
    return x * np.clip(env, 0.0, 1.0)


def humanise(x: np.ndarray, wet: float = 0.13, seed: int = 5):
    """🔴 REJECTED — manufactures humanity after synthesis; see the module
    docstring. Kept for historical cuts only.

    The whole chain, mono in, stereo out. Order matters: shape and dynamics on the dry
    signal, then put the finished voice in a room -- reverberating a signal and *then*
    compressing it pumps the room, which sounds like a plugin rather than a place.

    Deliberately does *not* normalise. Levelling each line to the same peak would make every
    sentence equally loud, and a narrator whose every sentence is equally loud is the thing
    being fixed here. The caller applies one gain to all of them.
    """
    x = spectral(x, lambda f: highpass(f, 75, 3))
    x = deess(x)
    x = spectral(x, lambda f: shelf(f, 165, 2.2, low=True) * bell(f, 3100, 1.6, 1.1)
                 * shelf(f, 9000, -1.5, low=False))
    x = compress(x)
    x = saturate(x)
    x = drift(x, seed=seed)
    left, right = room_ir(seed=seed)
    dry = np.stack([x, x])
    wetsig = np.stack([convolve_fft(x, left), convolve_fft(x, right)])
    return dry * (1.0 - wet) + wetsig * wet
