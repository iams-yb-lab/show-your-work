#!/usr/bin/env python3
"""
verify_numbers.py — re-derive every number this film is allowed to speak as measured.

Stage 1 of the education-video method requires the source document's numbers to be re-derived by
a second pass. This is that pass. Nothing here trusts a figure written in prose: durations come
from the media file, counts come from parsing the scripts, rates are computed from the two.

    python3 tools/verify_numbers.py            # human-readable table
    python3 tools/verify_numbers.py --json     # machine-readable, for SOURCE.md checking

Two subjects:

  reference   the existing 5:38 explainer for this project's instrument, which is the only film
              in this repo whose script, timings and delivered file all still exist together.
  trial       the deliberately deleted generic film, read back out of git. Its script survives;
              its audio does not, so its runtime is *recorded*, never measured here.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Do not anchor on the checkout: walk up until the directory holding engine/ and natural-voice/,
# which *is* the video tree by definition. Code written this way survives being lifted out.
def skills_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "_shared").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree: no ancestor holds both engine/ and natural-voice/")


SKILLS = skills_root(Path(__file__).resolve())
REFERENCE_SCRIPT = SKILLS / "education-video/examples/intro/script/voiceover-script.md"
# The intro film's silent master was deleted on 2026-08-22 — it is a render of the HTML
# bundle beside it, remade by education-video/method/export_html_video.py into out/.
# Render it there first, or pass --reference-media, before asking this script for the
# reference film's duration.
REFERENCE_MEDIA = (SKILLS.parents[1] / "out/education/picture"
                   / "Temperature Controller Intro 1080p.mp4")
TRIAL_SCRIPT_GIT = "3bebc07:video/education/how-to-explain-your-work/script/voiceover-script.md"

SCENE = re.compile(r"^##\s+(.+?)\s*\((\d+:\d+\.\d+)\s*[–-]\s*(\d+:\d+\.\d+)\)")
CUE = re.compile(r"^\*\*(\d+:\d+\.\d+)\*\*\s+\[([\d.]+)s\]\s+(.*\S)")
NUMBERED_CUE = re.compile(r"^\d+\.\s+(.*\S)")
PERFORMANCE_MARK = re.compile(r"^\[[A-Z]+\]\s*")
TRACE = re.compile(r"\s*→.*$")


def clock(text: str) -> float:
    m, s = text.split(":")
    return int(m) * 60 + float(s)


HAS_LETTER_OR_DIGIT = re.compile(r"[A-Za-z0-9]")


def words(text: str) -> int:
    """Whitespace tokens carrying at least one letter or digit.

    A standalone em dash is punctuation, not a word — and this is not pedantry. Both existing
    scripts were counted with a plain `.split()`, which counts one. That inflated the trial film's
    count from 746 to 751 and the reference film's by its own five dashes, and since words-per-
    minute is derived from these, the two films' rates were computed on different definitions and
    were never comparable. One definition, applied to both, is the fix.
    """
    return sum(1 for token in text.split() if HAS_LETTER_OR_DIGIT.search(token))


def tokens(text: str) -> int:
    """The old, naive count. Kept only so the discrepancy above stays mechanically visible."""
    return len(text.split())


def ffprobe(path: Path) -> dict:
    exe = shutil.which("ffprobe") or (
        r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages"
        r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffprobe.exe"
    )
    out = subprocess.run(
        [exe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    probed = json.loads(out)
    stream = probed["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    return {
        "width": stream["width"],
        "height": stream["height"],
        "fps": int(num) / int(den),
        "duration_s": float(probed["format"]["duration"]),
    }


def measure_reference() -> dict:
    scenes, cues = [], []
    for line in REFERENCE_SCRIPT.read_text(encoding="utf-8").splitlines():
        if m := SCENE.match(line):
            scenes.append({"title": m.group(1), "in": clock(m.group(2)), "out": clock(m.group(3))})
        elif m := CUE.match(line):
            cues.append({"start": clock(m.group(1)), "slot": float(m.group(2)),
                         "words": words(m.group(3)), "scene": len(scenes)})

    holes = [c["start"] - s["in"]
             for i, s in enumerate(scenes, 1)
             for c in [next(c for c in cues if c["scene"] == i)]]
    spoken = sum(c["words"] for c in cues)
    slots = [c["slot"] for c in cues]
    table_span = scenes[-1]["out"] - scenes[0]["in"]
    gaps = [round(b["in"] - a["out"], 4) for a, b in zip(scenes, scenes[1:])]
    media = ffprobe(REFERENCE_MEDIA)

    return {
        "scenes": len(scenes),
        "cues": len(cues),
        "words": spoken,
        "scene_table_span_s": round(table_span, 3),
        "scene_table_contiguous": all(g == 0 for g in gaps),
        "media": media,
        "table_vs_file_s": round(abs(table_span - media["duration_s"]), 3),
        "wpm_overall": round(spoken / (media["duration_s"] / 60), 1),
        "slot_min_s": min(slots),
        "slot_max_s": max(slots),
        "slot_mean_s": round(sum(slots) / len(slots), 2),
        "hole_min_s": round(min(holes), 2),
        "hole_max_s": round(max(holes), 2),
        "holes": len(holes),
    }


def measure_trial() -> dict:
    """The trial film's script, read back out of git. Its audio was deleted with it."""
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=True).stdout.strip()
    text = subprocess.run(["git", "show", TRIAL_SCRIPT_GIT], cwd=root,
                          capture_output=True, text=True, check=True).stdout
    lines, sections = [], set()
    for raw in text.splitlines():
        if m := NUMBERED_CUE.match(raw.strip()):
            body = TRACE.sub("", m.group(1))
            if mark := re.match(r"^\[([A-Z]+)\]", body):
                sections.add(mark.group(1))
            lines.append(PERFORMANCE_MARK.sub("", body))
    spoken = sum(words(l) for l in lines)
    return {
        "cues": len(lines),
        "words": spoken,
        "performance_sections": len(sections),
        "recorded_master_s": 237.6,          # RECORDED, not measured: the master was deleted.
        "wpm_from_recorded": round(spoken / (237.6 / 60), 1),
    }


def main(argv: list[str]) -> int:
    result = {"reference": measure_reference(), "trial": measure_trial()}
    if "--json" in argv:
        print(json.dumps(result, indent=2))
        return 0

    r, t = result["reference"], result["trial"]
    print("reference film — measured from script + delivered file")
    print(f"  picture         {r['media']['width']}x{r['media']['height']} @ "
          f"{r['media']['fps']:g} fps, {r['media']['duration_s']:.3f} s")
    print(f"  structure       {r['scenes']} scenes, {r['cues']} cues, {r['words']} words")
    print(f"  scene table     spans {r['scene_table_span_s']:.1f} s, "
          f"contiguous={r['scene_table_contiguous']}, "
          f"disagrees with the file by {r['table_vs_file_s']:.3f} s")
    print(f"  rate            {r['wpm_overall']:.1f} wpm over the whole film, silence included")
    print(f"  slots           {r['slot_min_s']:.1f} – {r['slot_max_s']:.1f} s, "
          f"mean {r['slot_mean_s']:.2f} s")
    print(f"  holes           {r['holes']}, {r['hole_min_s']:.1f} – {r['hole_max_s']:.1f} s")
    print("trial film — script from git; audio deleted, so runtime is recorded not measured")
    print(f"  structure       {t['cues']} cues, {t['words']} words, "
          f"{t['performance_sections']} performance sections")
    print(f"  rate            {t['wpm_from_recorded']:.1f} wpm against a recorded "
          f"{t['recorded_master_s']:.1f} s master")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
