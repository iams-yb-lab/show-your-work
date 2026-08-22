r"""Rebuild the ladder clean: no clipping, no lossy encode.

Same four rungs as `diagnose_ladder.py`, plus the two prompts as reference
rungs. The prompts speak a different passage, so they are not rungs in the
ladder proper — they are the files the student ranked above everything, and
they belong in the comparison at the same level so the gap can be judged
rather than remembered.

All levels come from `compare_lib`, which derives one common target from the
material instead of matching upward into the ceiling. The previous build of
this comparison clipped every delivered file between +0.6 and +3.0 dBFS.

Run in `%TEMP%\sr-venv` (ffmpeg only; no model needed).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import compare_lib

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See video/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "video" / "natural-voice").is_dir())
ROOT = REPO / "video" / "out" / "showoff" / "natural-v8"
B = ROOT / "audition" / "B_slow078"
A = ROOT / "audition" / "A_incumbent"
L = ROOT / "ladder"

LIDS = [1, 6]

SETS = {
    # reference: different words, and the files the student ranked first
    "0a_prompt_A_ref": [ROOT / "prompt_A_incumbent_0.88.wav"],
    "0b_prompt_B_ref": [ROOT / "prompt_B_slower_0.78.wav"],
    # the ladder proper: same words, one variable per rung
    "1_kokoro_direct": [L / f"1_kokoro_direct_line{i}.wav" for i in LIDS],
    "2_editx_raw": [B / f"line{i}_audition.wav" for i in LIDS],
    "3_editx_sr": [B / f"line{i}_sr.wav" for i in LIDS],
    "4_editx_sr_eq": [B / f"line{i}_eq.wav" for i in LIDS],
    # the incumbent narrator, for one more anchor to v7.2
    "5_editx_A_sr_eq": [A / f"line{i}_eq.wav" for i in LIDS],
}


def main():
    print("rebuilding comparison at a headroom-safe common level\n", flush=True)
    report = compare_lib.build(SETS, ROOT / "compare", prefix="cmp_")
    (ROOT / "compare" / "compare-report.json").write_text(json.dumps(report, indent=2))
    print(f"\nwrote {ROOT / 'compare' / 'compare-report.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
