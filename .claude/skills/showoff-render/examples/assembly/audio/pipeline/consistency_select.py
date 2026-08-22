"""Re-select takes for ONE consistent narrator across all six lines.

Features per take: median F0 (register), F0 IQR (expressiveness/excitement),
spectral centroid (brightness). Joint selection: minimize distance to the
global median of the pool, plus a calmness penalty on F0 IQR — so the six
chosen takes sound like the same person in the same mood. Word-perfect
takes only. Prints the achieved cross-line spread so it can be judged.
"""
import os, json, shutil
from pathlib import Path

import numpy as np, librosa

MEDIA = Path(os.environ["TEMP"]) / "temperature-controller-media"
SRC = MEDIA / "editx"
OUT = MEDIA / "editx_consistent"
OUT.mkdir(parents=True, exist_ok=True)

START_OVERRIDES = {1: 2.85, 4: 47.25, 6: 72.95}

def feats(path):
    y, sr = librosa.load(str(path), sr=None)
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    return dict(
        f0_med=float(np.median(f0)),
        f0_iqr=float(np.percentile(f0, 75) - np.percentile(f0, 25)),
        centroid=float(np.mean(cent)),
        dur=len(y) / sr,
    )

def main():
    manifest = json.loads((SRC / "manifest.json").read_text())
    pool = {}
    for line in manifest:
        cands = []
        for t in line["takes"]:
            if t["wer"] > 0.0:
                continue
            f = feats(t["path"])
            cands.append({**t, **f})
        pool[line["line"]] = cands
        print(f"line{line['line']}: {len(cands)} word-perfect takes, "
              f"f0 {[round(c['f0_med']) for c in cands]}", flush=True)

    allc = [c for cs in pool.values() for c in cs]
    med = {k: float(np.median([c[k] for c in allc])) for k in ("f0_med", "f0_iqr", "centroid")}
    mad = {k: max(1e-9, float(np.median([abs(c[k] - med[k]) for c in allc]))) for k in med}
    print(f"pool medians: f0={med['f0_med']:.1f}Hz iqr={med['f0_iqr']:.1f} cent={med['centroid']:.0f}Hz", flush=True)

    chosen = {}
    for lid, cands in pool.items():
        def score(c):
            s = 2.0 * abs(c["f0_med"] - med["f0_med"]) / mad["f0_med"]  # register match dominates
            s += abs(c["centroid"] - med["centroid"]) / mad["centroid"]
            s += 0.5 * max(0.0, (c["f0_iqr"] - med["f0_iqr"]) / mad["f0_iqr"])  # calm: penalize excess only
            return s
        best = min(cands, key=score)
        chosen[lid] = best
        shutil.copyfile(best["path"], OUT / f"line{lid}_best.wav")
        print(f"line{lid} CHOSEN take{best['take']}: f0={best['f0_med']:.1f}Hz "
              f"iqr={best['f0_iqr']:.1f} cent={best['centroid']:.0f}Hz dur={best['dur']:.2f}s", flush=True)

    f0s = [c["f0_med"] for c in chosen.values()]
    cents = [c["centroid"] for c in chosen.values()]
    print(f"cross-line spread: f0 {max(f0s)-min(f0s):.1f} Hz (range {min(f0s):.0f}-{max(f0s):.0f}), "
          f"centroid {max(cents)-min(cents):.0f} Hz", flush=True)

    for line in manifest:
        line["start"] = START_OVERRIDES.get(line["line"], line["start"])
        line["chosen"] = {k: v for k, v in chosen[line["line"]].items() if k != "hyp"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
