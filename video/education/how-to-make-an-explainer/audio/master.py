#!/usr/bin/env python3
"""
master.py — EQ the sections, lay them out in time, freeze one master. Runs in editx-venv.

This is where the film's clock is created. Everything downstream — captions, the scene table, the
picture — is measured off the file this writes, and nothing upstream is allowed to be re-timed to fit
a picture that does not exist yet.

Layout rules, all of them from the method rather than invented here:

  * sections play in script order, untrimmed: the model's own onset and decay are kept;
  * a short gap inside a scene, a longer one at a scene break, so a cut can land on the break;
  * a hole at the top of every scene before its first word, HOLE_S, inside the 0.7–1.9 s the
    reference film uses, so a music mark has somewhere to sit;
  * scene in-points are contiguous — each scene ends exactly where the next begins — so the table
    sums to the file duration with nothing unaccounted for.

Level is set once, downward, at the end. The profile's EQ curve is applied through the shared engine
so this film and the last one are filtered by the same code.

    python3 audio/master.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

AUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIO))
from sections import load  # noqa: E402


def video_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "engine").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree")


VIDEO = video_root(AUDIO)
sys.path.insert(0, str(VIDEO / "engine"))
import dsp  # noqa: E402
from mix_audio import lufs, true_peak_db  # noqa: E402

WORK = VIDEO / "out/education/how-to-make-an-explainer"
PROFILE = json.loads((VIDEO / "natural-voice/profiles/warm-natural/profile.json")
                     .read_text(encoding="utf-8"))
EQ = PROFILE["proven_education_v2_eq"]

SR = 48_000
GAP_IN_SCENE_S = 0.32
GAP_AT_SCENE_BREAK_S = 1.35
HOLE_S = 1.00          # scene in-point to its first word
TAIL_S = 1.60          # after the last word
TARGET_LUFS = -16.0    # per-cue narration level the approved mix used; music comes later
CEILING_DBTP = -1.5    # a master that still has room for the music bus on top


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def eq(x: np.ndarray) -> np.ndarray:
    """The profile's curve, applied with the engine's own zero-phase filters."""
    def curve(f):
        return (dsp.highpass(f, EQ["highpass_hz"], order=2)
                * dsp.bell(f, EQ["body"]["frequency_hz"], EQ["body"]["gain_db"], EQ["body"]["q"])
                * dsp.bell(f, EQ["boxiness"]["frequency_hz"], EQ["boxiness"]["gain_db"],
                           EQ["boxiness"]["q"])
                * dsp.bell(f, EQ["presence"]["frequency_hz"], EQ["presence"]["gain_db"],
                           EQ["presence"]["q"])
                * dsp.shelf(f, EQ["air_shelf"]["frequency_hz"], EQ["air_shelf"]["gain_db"],
                            low=False))
    return dsp.spectral(x, curve)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=WORK / "master")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    restore = json.loads((WORK / "restore.json").read_text(encoding="utf-8"))
    by_id = {r["section"]: r for r in restore["sections"]}
    script = load()
    missing = [s["id"] for s in script if s["id"] not in by_id]
    if missing:
        raise SystemExit(f"no restored audio for section(s): {missing}")

    pieces, placement, cursor = [], [], HOLE_S
    pieces.append(np.zeros(int(round(HOLE_S * SR)), dtype=np.float32))
    previous_scene = script[0]["scene"]

    for index, section in enumerate(script):
        if index:
            at_break = section["scene"] != previous_scene
            gap = GAP_AT_SCENE_BREAK_S if at_break else GAP_IN_SCENE_S
            # A scene break spends part of its gap as the next scene's hole, so the hole is real
            # silence rather than a number in a table.
            pieces.append(np.zeros(int(round(gap * SR)), dtype=np.float32))
            cursor += gap
        y, rate = sf.read(by_id[section["id"]]["path"], dtype="float32", always_2d=False)
        if rate != SR:
            raise SystemExit(f"{section['id']}: expected {SR} Hz, got {rate}")
        if y.ndim > 1:
            y = y.mean(axis=1)
        filtered = eq(y).astype(np.float32)
        pieces.append(filtered)
        placement.append({
            "section": section["id"], "scene": section["scene"],
            "scene_title": section["scene_title"], "cues": section["cues"],
            "start_s": round(cursor, 3), "duration_s": round(len(filtered) / SR, 3),
            "end_s": round(cursor + len(filtered) / SR, 3),
            "restored": by_id[section["id"]]["restoration_accepted"],
            "take": by_id[section["id"]]["take"],
        })
        cursor += len(filtered) / SR
        previous_scene = section["scene"]

    pieces.append(np.zeros(int(round(TAIL_S * SR)), dtype=np.float32))
    mono = np.concatenate(pieces)

    # One static gain, downward, measured on the assembled file rather than on its parts.
    measured = lufs(np.stack([mono, mono]))
    gain_db = TARGET_LUFS - measured
    peak_after = true_peak_db(np.stack([mono, mono])) + gain_db
    if peak_after > CEILING_DBTP:
        gain_db -= peak_after - CEILING_DBTP
    mono = (mono * 10 ** (gain_db / 20.0)).astype(np.float32)

    final_lufs = lufs(np.stack([mono, mono]))
    final_tp = true_peak_db(np.stack([mono, mono]))
    if final_tp > CEILING_DBTP + 0.05:
        raise SystemExit(f"true peak {final_tp:+.2f} dBTP over the ceiling — refusing to write")

    path = args.out / "narration-master.wav"
    sf.write(path, mono, SR, subtype="PCM_24")

    # Per-section files for the listening pass, sliced out of the finished master rather than built
    # from the parts — so what gets audited is byte-for-byte what is in the film, and a section that
    # sounds wrong here is wrong there too. Numbered in script order so the audit has an order.
    review = args.out / "sections"
    review.mkdir(parents=True, exist_ok=True)
    for order, row in enumerate(placement, 1):
        clip = mono[int(round(row["start_s"] * SR)):int(round(row["end_s"] * SR))]
        slice_path = review / f"{order:02d}_{row['section']}_scene{row['scene']}.wav"
        sf.write(slice_path, clip, SR, subtype="PCM_24")
        row["review_path"] = str(slice_path)
        row["review_true_peak_dbtp"] = round(true_peak_db(np.stack([clip, clip])), 2)
        row["review_lufs"] = round(lufs(np.stack([clip, clip])), 2)
    # Measure the artifact handed over, not its sources: a slice is something this code built, and it
    # can be broken in ways the master is not.
    if over := [r for r in placement if r["review_true_peak_dbtp"] > -1.0]:
        raise SystemExit(f"delivered slices above -1 dBTP: {[r['section'] for r in over]}")

    scenes, order = [], []
    for row in placement:
        if not order or order[-1]["scene"] != row["scene"]:
            order.append({"scene": row["scene"], "title": row["scene_title"],
                          "first_start": row["start_s"], "last_end": row["end_s"]})
        else:
            order[-1]["last_end"] = row["end_s"]
    total = len(mono) / SR
    for i, s in enumerate(order):
        in_s = round(s["first_start"] - HOLE_S, 3) if i else 0.0
        out_s = round(order[i + 1]["first_start"] - HOLE_S, 3) if i + 1 < len(order) else round(total, 3)
        scenes.append({"scene": s["scene"], "title": s["title"], "in_s": in_s, "out_s": out_s,
                       "duration_s": round(out_s - in_s, 3),
                       "hole_s": round(s["first_start"] - in_s, 3)})

    record = {
        "path": str(path), "sha256": sha256(path), "sample_rate": SR, "channels": 1,
        "duration_s": round(total, 3),
        "integrated_lufs": round(final_lufs, 2), "true_peak_dbtp": round(final_tp, 2),
        "gain_applied_db": round(gain_db, 2),
        "targets": {"lufs": TARGET_LUFS, "ceiling_dbtp": CEILING_DBTP},
        "layout": {"hole_s": HOLE_S, "gap_in_scene_s": GAP_IN_SCENE_S,
                   "gap_at_scene_break_s": GAP_AT_SCENE_BREAK_S, "tail_s": TAIL_S},
        "eq": EQ, "sections": placement, "scenes": scenes,
        "scene_table_sums_to_file": abs(sum(s["duration_s"] for s in scenes) - total) < 0.001,
    }
    (WORK / "master.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"master: {path}")
    print(f"  {total / 60:.0f}:{total % 60:04.1f}  {final_lufs:+.2f} LUFS  {final_tp:+.2f} dBTP  "
          f"(gain {gain_db:+.2f} dB)")
    print(f"  {len(placement)} sections, {len(scenes)} scenes, "
          f"table sums to file: {record['scene_table_sums_to_file']}")
    for s in scenes:
        print(f"    scene {s['scene']}  {s['in_s']:7.3f} → {s['out_s']:7.3f}  "
              f"{s['duration_s']:6.3f} s  hole {s['hole_s']:.2f}  {s['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
