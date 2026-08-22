"""Move the ~69.7 s bass pulse (Teensy landing bloom) to ~71.0 s (1:11).

Complementary band split at 240 Hz (low = zero-phase FFT lowpass, high =
original minus low, so recombination is exact). In the low band only:
the pulse segment [69.68, 72.28) is lifted out, the hole is patched with
the adjacent steady-pedal bed [68.30, 69.60), and the segment is put back
1.30 s later with raised-cosine crossfades at every seam. Also nudges
line 5's start to 58.9 s (after the ADC bell strike at 57.3 s decays).
Writes cinematic_score_v2.wav; the original WAV is not modified.
"""
import os, sys, json, math
from pathlib import Path

import numpy as np, soundfile as sf

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / ".claude" / "skills" / "_shared").is_dir())
                            / ".claude" / "skills" / "_shared" / "audio"))
from dsp import SR, lowpass, spectral  # noqa: E402

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
SPLIT_HZ = 240
SHIFT = 1.30
T_ON, T_OFF = 69.68, 72.28   # pulse segment in the original
FILL_SRC = 68.30             # steady bed, same length as the hole (1.30 s)
XF = 0.05                    # 50 ms crossfades

def xfade_replace(dst, seg, i0):
    """Write seg into dst at i0 with raised-cosine edges blending into dst."""
    n = len(seg)
    w = np.ones(n)
    k = int(XF * SR)
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, k))
    w[:k] = ramp
    w[-k:] = ramp[::-1]
    dst[i0:i0 + n] = dst[i0:i0 + n] * (1 - w) + seg * w

def main():
    y, sr = sf.read(str(MEDIA / "cinematic_score.wav"), always_2d=True)
    assert sr == SR
    y = y.T.copy()

    a, b = int(T_ON * SR), int(T_OFF * SR)
    hole = int(SHIFT * SR)
    fa = int(FILL_SRC * SR)

    for ch in range(2):
        low = spectral(y[ch], lambda f: lowpass(f, SPLIT_HZ, 2))
        high = y[ch] - low
        pulse = low[a:b].copy()
        fill = low[fa:fa + hole].copy()
        xfade_replace(low, fill, a)                  # patch the vacated 1.3 s with bed
        xfade_replace(low, pulse, a + hole)          # pulse lands 1.3 s later
        y[ch] = high + low

    sf.write(str(MEDIA / "cinematic_score_v2.wav"), y.T, SR, subtype="PCM_24")

    # verify: low-band envelope around the move
    m = y.mean(axis=0)
    low = spectral(m, lambda f: lowpass(f, 150, 2))
    for t0 in [x * 0.25 for x in range(4 * 69, 4 * 74)]:
        seg = low[int(t0 * SR):int((t0 + 0.25) * SR)]
        db = 20 * math.log10(np.sqrt((seg ** 2).mean()) + 1e-12)
        print(f"{t0:6.2f}s  {db:6.1f} dB", flush=True)

    mpath = MEDIA / "editx_consistent_sr" / "manifest.json"
    manifest = json.loads(mpath.read_text())
    for line in manifest:
        if line["line"] == 5:
            line["start"] = 58.9
    mpath.write_text(json.dumps(manifest, indent=2))
    print("line 5 start -> 58.9 s; wrote cinematic_score_v2.wav", flush=True)

if __name__ == "__main__":
    main()
