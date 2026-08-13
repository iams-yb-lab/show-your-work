"""Move the climax sub swell's onset ~1 s later, keeping its landing on the
Teensy seat (71.3 s).

The swell is deterministic in mix_audio.py: sin(2π·73.416·t)·smoothstep(t/2.5)²,
placed at 68.8 s, ×0.55, through the bells layer's zero-phase FFT highpass(90,2),
×0.055. All LTI after synthesis, so its exact contribution to the final WAV is
reconstructable up to the master gain — which is recovered by least-squares and
verified by the subtraction residual. New swell: onset 69.8 s, 1.5 s rise, same
peak, same landing.

Reads the repo's dsp.py READ-ONLY for the exact filter. Writes
cinematic_score_v2.wav to the media dir; the original is not modified.
"""
import os, sys, math
from pathlib import Path

import numpy as np, soundfile as sf

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "video" / "engine").is_dir()) / "video" / "engine"))
from dsp import SR, highpass, spectral  # noqa: E402

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
D2 = 440.0 * 2.0 ** ((38 - 69.0) / 12.0)  # midi 38 = 73.416 Hz
T_LAND = 71.3

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

def swell_contribution(n_total, t_start, rise_s):
    n = int(rise_s * SR)
    tr = np.arange(n) / SR
    sub = np.sin(2 * math.pi * D2 * tr) * smoothstep(tr / rise_s) ** 2
    buf = np.zeros(n_total)
    i0 = int(t_start * SR)
    buf[i0:i0 + n] = sub * 0.55
    return spectral(buf, lambda f: highpass(f, 90, 2)) * 0.055

def main():
    y, sr = sf.read(str(MEDIA / "cinematic_score.wav"), always_2d=True)
    assert sr == SR, (sr, SR)
    y = y.T  # (2, n)
    n_total = y.shape[1]

    old = swell_contribution(n_total, T_LAND - 2.5, 2.5)
    a, b = int(68.8 * SR), int(71.3 * SR)
    seg, ref = y[:, a:b], old[a:b]
    g = float((seg @ ref).sum() / (2.0 * (ref @ ref)))  # least-squares master gain
    resid = y.copy()
    resid[0, :] -= g * old
    resid[1, :] -= g * old
    r_seg = resid[:, a:b]
    corr = float(np.abs(seg @ ref).sum() / (np.linalg.norm(seg) * np.linalg.norm(ref) * math.sqrt(2)))
    drop = 20 * math.log10(np.linalg.norm(r_seg) / np.linalg.norm(seg))
    print(f"master gain fit g={g:.4f}, window correlation={corr:.3f}, "
          f"energy after subtraction {drop:+.1f} dB", flush=True)
    if not (0.2 < g < 5.0) or corr < 0.15:
        print("RECONSTRUCTION DOES NOT MATCH — score left untouched, aborting", flush=True)
        sys.exit(1)

    new = swell_contribution(n_total, T_LAND - 1.5, 1.5) * g
    out = resid
    out[0, :] += new
    out[1, :] += new
    peak = float(np.abs(out).max())
    print(f"new swell: onset 69.8 s, lands {T_LAND} s; output peak {peak:.4f}", flush=True)
    sf.write(str(MEDIA / "cinematic_score_v2.wav"), out.T, SR, subtype="PCM_24")
    print("wrote cinematic_score_v2.wav", flush=True)

if __name__ == "__main__":
    main()
