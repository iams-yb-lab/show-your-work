"""Read the intro film's own schedule out of the film, and write it as one cue sheet.

    python education-video/examples/intro/audio/intro_cues.py --out out/audio/cues.json

Nothing here is typed by hand. Two artifacts already carry the timing and they were produced
by whatever drew the pictures:

  * `Temperature Controller Intro.html` embeds `window.OM_SCENES` -- the nine scenes with their
    durations, which is the cut itself.
  * `voiceover-script.md` carries every narration line with the timecode it is spoken at.

Both are parsed, and the section boundaries in the script are checked against the scene
durations in the HTML. They are independent documents, so if one has been edited and the other
has not, that disagreement is the first thing worth knowing and this is where it surfaces.

The film runs at 30 fps and a frame is displayed from t = (frame - 1) / fps, which is the
convention the rest of this project's audio tooling already uses, so every cue is written as a
frame as well as a time.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intro_env import HTML, OUT, REPO, SCRIPT, VIDEO, find_ffprobe  # noqa: E402

FPS = 30

# **1:02.2**  [8.3s]  A Teensy 4.1 compares it with the setpoint ...
LINE = re.compile(r"^\*\*(\d+):(\d+(?:\.\d+)?)\*\*\s+\[([\d.]+)s\]\s+(.+?)\s*$")
# ## The loop  (0:42.3 - 1:21.6)          -- an en dash in the file
HEAD = re.compile(r"^##\s+(.+?)\s+\((\d+):(\d+(?:\.\d+)?)\s*[\u2013-]\s*(\d+):(\d+(?:\.\d+)?)\)")

def frame_of(t: float) -> int:
    """The frame that is on screen at t, under t = (frame - 1) / fps."""
    return int(round(t * FPS)) + 1


def scenes_from_html(path: Path):
    """`window.OM_SCENES` is a JSON array inside a single-quoted JS string, so the double
    quotes and the \\u escapes in it are backslash-escaped one level deeper than JSON."""
    h = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"window\.OM_SCENES\s*=\s*'(.*?)';", h, re.S)
    if not m:
        sys.exit(f"{path.name}: no window.OM_SCENES in the bundle")
    bs = chr(92)
    raw = m.group(1).replace(bs + '"', '"').replace(bs * 2 + "u", bs + "u")
    out, t = [], 0.0
    for d in json.loads(raw):
        out.append(dict(name=d["name"], desc=d.get("desc", ""), start=round(t, 3),
                        end=round(t + d["dur"], 3), dur=float(d["dur"])))
        t += d["dur"]
    return out


def script_sections_and_lines(path: Path):
    heads, lines = [], []
    for row in path.read_text(encoding="utf-8").splitlines():
        h = HEAD.match(row)
        if h:
            heads.append((h.group(1),
                          int(h.group(2)) * 60 + float(h.group(3)),
                          int(h.group(4)) * 60 + float(h.group(5))))
            continue
        m = LINE.match(row)
        if m:
            lines.append(dict(t=round(int(m.group(1)) * 60 + float(m.group(2)), 3),
                              gap=float(m.group(3)), text=m.group(4)))
    return heads, sorted(lines, key=lambda l: l["t"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=HTML)
    ap.add_argument("--script", type=Path, default=SCRIPT)
    ap.add_argument("--video", type=Path, default=VIDEO)
    ap.add_argument("--out", type=Path, default=OUT / "audio" / "cues.json")
    # One bar per scene is the wrong unit and one tempo for the whole film would put a bar
    # across a cut. Each scene instead holds a whole number of bars of about this length, so
    # every scene boundary is a downbeat by construction. See intro_score.py.
    ap.add_argument("--bar", type=float, default=2.40, help="target bar length, seconds")
    args = ap.parse_args()

    scenes = scenes_from_html(args.html)
    heads, lines = script_sections_and_lines(args.script)
    if not lines:
        sys.exit(f"{args.script.name}: no narration lines parsed")

    duration = sum(s["dur"] for s in scenes)
    probed = None
    ffprobe = find_ffprobe()
    if ffprobe and args.video.exists():
        r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=duration,nb_frames,r_frame_rate",
                            "-of", "json", str(args.video)], capture_output=True, text=True)
        st = json.loads(r.stdout)["streams"][0]
        probed = dict(duration=float(st["duration"]), frames=int(st["nb_frames"]),
                      rate=st["r_frame_rate"])

    # Cross-check 1: the scene table against the script's own section headings. Independent
    # documents; a disagreement means one was edited without the other.
    print(f"{len(scenes)} scenes, {duration:.3f} s total")
    worst = 0.0
    for s, h in zip(scenes, heads):
        d = max(abs(s["start"] - h[1]), abs(s["end"] - h[2]))
        worst = max(worst, d)
        print(f"  {s['start']:7.2f} -> {s['end']:7.2f}  {s['dur']:6.2f} s  {s['name']:10s}"
              f"  script says {h[1]:7.2f} -> {h[2]:7.2f}  ({h[0]})  d={d:.2f} s")
    if worst > 0.1:
        sys.exit(f"scene table and script sections disagree by up to {worst:.2f} s")
    print(f"  scene table agrees with the script's sections to {worst * 1000:.0f} ms")

    # Cross-check 2: the picture. The film is the authority on its own length.
    if probed:
        print(f"  {args.video.name}: {probed['duration']:.3f} s, {probed['frames']} frames, "
              f"{probed['rate']} fps")
        if abs(probed["duration"] - duration) > 0.05:
            sys.exit(f"scene durations sum to {duration:.3f} s but the file is "
                     f"{probed['duration']:.3f} s")

    # Each scene gets a whole number of bars of its own, so no bar crosses a cut and no cut
    # needs a tempo map. The count comes from the scene's length; the tempo falls out of it.
    for s in scenes:
        s["bars"] = max(1, int(round(s["dur"] / args.bar)))
        s["bar"] = s["dur"] / s["bars"]
        s["bpm"] = 240.0 / s["bar"]
        s["frame"] = frame_of(s["start"])

    print(f"\n  bars per scene at a {args.bar:.2f} s target:")
    for s in scenes:
        print(f"    {s['name']:10s} {s['bars']:3d} bars of {s['bar']:.4f} s "
              f"= {s['bpm']:7.3f} BPM")
    spread = max(s["bar"] for s in scenes) / min(s["bar"] for s in scenes) - 1.0
    print(f"    tempo spread across the film: {spread * 100:.1f} %")

    # The narration, with the slot each line has before the next one starts. A line that
    # speaks for longer than its slot is the one fault that matters, and intro_narrate.py
    # fixes it by rate rather than by moving the line: the picture is cut to these times.
    for i, l in enumerate(lines):
        l["frame"] = frame_of(l["t"])
        nxt = lines[i + 1]["t"] if i + 1 < len(lines) else duration
        l["slot"] = round(nxt - l["t"], 3)
        l["words"] = len(l["text"].split())
        l["scene"] = next(s["name"] for s in scenes
                          if s["start"] <= l["t"] < s["end"] + 1e-9)
    words = sum(l["words"] for l in lines)
    print(f"\n  {len(lines)} narration lines, {words} words, "
          f"{words / duration * 60:.0f} wpm over the whole film")

    # Every scene begins in a hole -- the film's own cut leaves the narrator quiet across each
    # boundary, which is what makes a section mark in the music free.
    holes = []
    for s in scenes:
        first = min((l["t"] for l in lines if l["t"] >= s["start"]), default=duration)
        holes.append(first - s["start"])
    print(f"  gap between each cut and the next line: "
          f"{min(holes):.2f}-{max(holes):.2f} s (all nine)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dict(fps=FPS, duration=round(duration, 3),
                                        target_bar=args.bar, scenes=scenes, lines=lines,
                                        video=str(args.video), probed=probed),
                                   indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
