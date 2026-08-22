r"""Choose ONE narrator across all six lines.

v7's correction, kept: every earlier generator picked each line's take on its
own merits — duration fit, per-line gates — and the result was a narrator whose
character changed between lines inside one video. Per-line optimisation trades
away exactly what a narrator is. So nothing here scores a take against its own
line's needs, and duration deliberately does not appear in the cost at all; the
cap was already applied at generation.

One change from `pipeline/consistency_select.py`. That version anchored on the
pool median and let each line pick the take nearest it, which is only optimal
if the pool median happens to be a register all six lines can actually reach.
Prompt B wanders 8 Hz take to take, so the anchor matters more here: this
searches every take in the pool as a candidate anchor, builds the best six-set
for each, and keeps the set with the tightest cross-line spread.

Run in `%TEMP%\sr-venv` (librosa only). Reads `takes/`, writes `chosen/`.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import librosa

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See video/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / ".claude" / "skills" / "natural-voice").is_dir())
ROOT = REPO / "out" / "showoff" / "natural-v8"
SRC = ROOT / "takes"
OUT = ROOT / "chosen"
OUT.mkdir(parents=True, exist_ok=True)


def centroid(path):
    y, sr = librosa.load(str(path), sr=None)
    return float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))


def main():
    man = json.loads((SRC / "manifest.json").read_text())

    pool = {}
    for line in man["lines"]:
        cands = []
        for t in line["takes"]:
            if t["wer"] > 0.0 or t["over_cap"]:
                continue
            cands.append({**t, "centroid": centroid(t["path"])})
        if not cands:
            print(f"line{line['line']}: NO usable take — relaxing the cap", flush=True)
            cands = [{**t, "centroid": centroid(t["path"])}
                     for t in line["takes"] if t["wer"] <= 0.0]
        if not cands:
            print(f"line{line['line']}: no word-perfect take at all. Stopping.", flush=True)
            return 1
        pool[line["line"]] = cands
        print(
            f"line{line['line']}: {len(cands)} usable, "
            f"F0 {sorted(round(c['median_f0_hz']) for c in cands)}",
            flush=True,
        )

    allc = [c for cs in pool.values() for c in cs]
    scale = {
        k: max(1e-6, float(np.median([abs(c[k] - np.median([d[k] for d in allc])) for c in allc])))
        for k in ("median_f0_hz", "f0_iqr_hz", "centroid")
    }

    def pick_for(anchor):
        """Best take per line against one anchor take's register and brightness."""
        out = {}
        for lid, cands in pool.items():
            def cost(c):
                s = 2.0 * abs(c["median_f0_hz"] - anchor["median_f0_hz"]) / scale["median_f0_hz"]
                s += abs(c["centroid"] - anchor["centroid"]) / scale["centroid"]
                # calm: penalise only expressiveness in excess of the anchor's
                s += 0.5 * max(0.0, (c["f0_iqr_hz"] - anchor["f0_iqr_hz"]) / scale["f0_iqr_hz"])
                return s
            out[lid] = min(cands, key=cost)
        return out

    def set_score(sel):
        f0s = [c["median_f0_hz"] for c in sel.values()]
        cents = [c["centroid"] for c in sel.values()]
        iqrs = [c["f0_iqr_hz"] for c in sel.values()]
        f0_range = max(f0s) - min(f0s)
        cent_range = max(cents) - min(cents)
        return (
            f0_range + 0.4 * (cent_range / 100.0) + 0.25 * float(np.mean(iqrs)),
            f0_range,
            cent_range,
            float(np.mean(iqrs)),
        )

    best_sel, best = None, None
    for anchor in allc:
        sel = pick_for(anchor)
        sc = set_score(sel)
        if best is None or sc[0] < best[0]:
            best, best_sel = sc, sel

    score, f0_range, cent_range, mean_iqr = best
    print(
        f"\nbest set: cross-line F0 spread {f0_range:.1f} Hz, "
        f"centroid spread {cent_range:.0f} Hz, mean IQR {mean_iqr:.1f} (score {score:.2f})",
        flush=True,
    )

    chosen_lines = []
    for line in man["lines"]:
        lid = line["line"]
        c = best_sel[lid]
        shutil.copyfile(c["path"], OUT / f"line{lid}_best.wav")
        print(
            f"line{lid} take{c['take']}: F0 {c['median_f0_hz']:.1f} Hz  IQR {c['f0_iqr_hz']:.1f}  "
            f"spoken {c['spoken_s']:.2f}s  lead {c['lex_start_s']:.2f}s  tail {c['tail_s']:.2f}s",
            flush=True,
        )
        chosen_lines.append(
            dict(line=lid, text=line["text"], start=line["start"], cap_s=line["cap_s"],
                 chosen={k: v for k, v in c.items() if k != "transcript"})
        )

    (OUT / "manifest.json").write_text(
        json.dumps(
            dict(
                prompt_wav=man["prompt_wav"],
                selection="joint, anchor-searched; duration excluded by design",
                cross_line_f0_spread_hz=round(f0_range, 2),
                centroid_spread_hz=round(cent_range, 1),
                mean_f0_iqr_hz=round(mean_iqr, 2),
                lines=chosen_lines,
            ),
            indent=2,
        )
    )
    print(f"wrote {OUT / 'manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
