"""Signal primitives shared by the mixer and the voice chain.

Zero-phase frequency-domain filtering throughout, and no recursive loops anywhere: an 84 s
buffer at 48 kHz is four million samples, and a per-sample IIR in Python is minutes where an
FFT is milliseconds. Everything here is numpy and the standard library.
"""

from __future__ import annotations

import numpy as np

SR = 48000


def spectral(x: np.ndarray, curve) -> np.ndarray:
    """Apply a frequency-domain gain curve, evaluated at the real FFT bin frequencies."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    return np.fft.irfft(np.fft.rfft(x) * curve(f), n)


def lowpass(f, cut, order=2):
    return 1.0 / (1.0 + (f / max(cut, 1e-6)) ** (2 * order)) ** 0.5


def highpass(f, cut, order=2):
    r = (f / max(cut, 1e-6)) ** (2 * order)
    return (r / (1.0 + r)) ** 0.5


def bandpass(f, lo, hi, order=2):
    return highpass(f, lo, order) * lowpass(f, hi, order)


def shelf(f, hz, gain_db, low=True):
    """A gentle first-order-ish shelf. `low` shelves below `hz`, otherwise above it."""
    g = 10 ** (gain_db / 20.0)
    w = 1.0 / (1.0 + (f / max(hz, 1e-6)) ** 2) if low else 1.0 - 1.0 / (1.0 + (f / max(hz, 1e-6)) ** 2)
    return 1.0 + (g - 1.0) * w


def bell(f, hz, gain_db, q=1.0):
    """One peaking band. Used for presence lifts, where a shelf would take too much with it."""
    g = 10 ** (gain_db / 20.0)
    w = hz / max(q, 0.1)
    return 1.0 + (g - 1.0) / (1.0 + ((f - hz) / w) ** 2)


def resonator(f, centre, q=12.0):
    w = centre / max(q, 0.5)
    return 1.0 / (1.0 + ((f - centre) / w) ** 2)


def slide_max(x: np.ndarray, w: int) -> np.ndarray:
    """Exact centred sliding-window maximum, O(n) by the van Herk / Gil-Werman two-pass trick.

    A boxcar average cannot stand in for this where transients matter: a 2 ms click inside a
    12 ms window is diluted six times by averaging, and a limiter built on that lets it
    straight through.
    """
    w = max(1, int(w))
    n = len(x)
    pad = (-(n + w - 1)) % w
    xp = np.concatenate([x, np.full(w - 1 + pad, -np.inf)])
    blocks = xp.reshape(-1, w)
    suffix = np.maximum.accumulate(blocks[:, ::-1], axis=1)[:, ::-1].ravel()
    prefix = np.maximum.accumulate(blocks, axis=1).ravel()
    return np.roll(np.maximum(suffix[:n], prefix[w - 1:w - 1 + n]), w // 2)


def movavg(x: np.ndarray, w: int) -> np.ndarray:
    """Boxcar average by cumulative sum -- O(n) rather than O(n*w)."""
    w = max(1, int(w))
    c = np.cumsum(np.concatenate(([0.0], np.pad(x, (w // 2, w), mode="edge"))))
    return (c[w:w + len(x)] - c[:len(x)]) / w


def convolve_fft(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Linear convolution, zero-padded so nothing wraps round."""
    n = len(x) + len(h) - 1
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[:len(x)]


def write_wav24(path, stereo: np.ndarray):
    """24-bit PCM. The audio is muxed into a finished MP4 without re-encoding the video, so
    this is the only place quality can be lost, and 24 bits is more than the AAC stage uses."""
    import wave

    x = np.clip(np.atleast_2d(stereo).T, -1.0, 1.0)
    ints = np.round(x * (2 ** 23 - 1)).astype(np.int32)
    # The low three bytes of each little-endian int32 *are* the 24-bit two's-complement sample,
    # so the whole buffer packs in one view. This was a per-sample struct.pack loop, which is
    # eight million calls for the 84 s film and thirty-two million for the 5:38 one; the output
    # is byte-identical, checked against the loop before it was replaced.
    # ascontiguousarray, not astype: `stereo` arrives transposed, and a view of a transposed
    # array cannot be reinterpreted as bytes.
    raw = np.ascontiguousarray(ints, dtype="<i4").view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(raw)


def read_wav(path) -> np.ndarray:
    """Any bit depth this project produces, returned as (channels, n) floats."""
    import wave

    with wave.open(str(path), "rb") as w:
        width, n, ch = w.getsampwidth(), w.getnframes(), w.getnchannels()
        raw = w.readframes(n)
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(v & 0x800000, v - 0x1000000, v).astype(np.float64) / (2 ** 23)
    else:
        raise SystemExit(f"{path}: unsupported {width * 8}-bit wav")
    return x.reshape(-1, ch).T


def db(x) -> float:
    return 20.0 * np.log10(max(float(np.abs(x).max() if np.ndim(x) else x), 1e-12))


def rms_db(x: np.ndarray) -> float:
    return 20.0 * np.log10(max(float(np.sqrt((x ** 2).mean())), 1e-12))
