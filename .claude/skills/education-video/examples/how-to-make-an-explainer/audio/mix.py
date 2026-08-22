#!/usr/bin/env python3
"""
mix.py — narration plus music, one combined audio track, measured after it is built.

The picture will be cut against this file, so it is the last thing in the audio stage that is allowed
to change. Constant music level, no sidechain, no ducking: fast voice-triggered ducking exposes every
phrase boundary and reads as another artifact of the voice.

Everything is measured on the delivered file rather than on its inputs, because the mix is something
this code built and can be broken in ways its parts were not.

    python3 audio/mix.py
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


def skills_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "_shared").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a skills tree")


SKILLS = skills_root(AUDIO)
sys.path.insert(0, str(SKILLS / "_shared" / "audio"))
from mix_audio import lufs, true_peak_db, master as master_bus  # noqa: E402

WORK = SKILLS.parents[1] / "out/education/how-to-make-an-explainer"
SR = 48_000
# The relationship the approved education mix used: speech clearly in front, music well behind, and
# the numbers are the film's own delivery target rather than universal law.
MUSIC_BEHIND_DB = 13.5
TARGET_LUFS = -14.0
CEILING_DBTP = -1.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=WORK / "master/combined-audio.wav")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    record = json.loads((WORK / "master.json").read_text(encoding="utf-8"))
    music_record = json.loads((WORK / "music.json").read_text(encoding="utf-8"))

    voice, rate = sf.read(record["path"], dtype="float32", always_2d=False)
    if rate != SR:
        raise SystemExit(f"narration is {rate} Hz, expected {SR}")
    if voice.ndim > 1:
        voice = voice.mean(axis=1)
    bed, bed_rate = sf.read(music_record["path"], dtype="float32", always_2d=True)
    if bed_rate != SR:
        raise SystemExit(f"music is {bed_rate} Hz, expected {SR}")
    bed = bed.T

    # Lengths come from the same scene table, so a mismatch is a bug rather than something to trim
    # away quietly. Pad the shorter by at most a few samples of rounding.
    if abs(bed.shape[1] - len(voice)) > int(0.05 * SR):
        raise SystemExit(f"music is {bed.shape[1] / SR:.3f} s against narration "
                         f"{len(voice) / SR:.3f} s — regenerate the bed from master.json")
    n = min(bed.shape[1], len(voice))
    voice, bed = voice[:n], bed[:, :n]

    narration = np.stack([voice, voice])
    voice_lufs = lufs(narration)
    bed_lufs = lufs(bed)
    music_gain_db = (voice_lufs - MUSIC_BEHIND_DB) - bed_lufs
    bed_placed = bed * 10 ** (music_gain_db / 20.0)

    mixed = narration + bed_placed
    out, final_lufs, final_tp, clipped = master_bus(mixed, TARGET_LUFS, CEILING_DBTP)
    if final_tp > CEILING_DBTP + 0.05:
        raise SystemExit(f"true peak {final_tp:+.2f} dBTP over the ceiling — refusing to write")

    sf.write(args.out, out.T, SR, subtype="PCM_24")

    report = {
        "path": str(args.out), "sha256": sha256(args.out),
        "duration_s": round(n / SR, 3), "sample_rate": SR, "channels": 2,
        "narration": {"path": record["path"], "lufs": round(float(voice_lufs), 2)},
        "music": {"path": music_record["path"], "lufs_before": round(float(bed_lufs), 2),
                  "gain_applied_db": round(float(music_gain_db), 2),
                  "lufs_placed": round(float(lufs(bed_placed)), 2)},
        "music_behind_db": MUSIC_BEHIND_DB,
        "delivered": {"lufs": round(float(final_lufs), 2), "true_peak_dbtp": round(float(final_tp), 2),
                      "limiter_samples_touched": int(clipped)},
        "targets": {"lufs": TARGET_LUFS, "ceiling_dbtp": CEILING_DBTP},
        "sidechain_ducking": False,
        "scene_marks_s": music_record["scene_marks_s"],
    }
    (WORK / "mix.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"combined: {args.out}")
    print(f"  {n / SR / 60:.0f}:{n / SR % 60:04.1f}  {final_lufs:+.2f} LUFS  {final_tp:+.2f} dBTP")
    print(f"  narration {voice_lufs:+.2f} LUFS, music placed at "
          f"{report['music']['lufs_placed']:+.2f} LUFS ({MUSIC_BEHIND_DB:.1f} dB behind)")
    print(f"  limiter touched {clipped} sample(s); no ducking, constant music level")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
