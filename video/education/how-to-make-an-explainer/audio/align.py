#!/usr/bin/env python3
"""
align.py — cue times and captions, measured off the frozen master. Runs in editx-venv.

**No timing here is arithmetic.** Every cue's start is the time of its first spoken word in the
finished audio, taken from word-level alignment, and every caption sits on speech that already
exists. This is the step that makes the audio the timing authority in fact and not just in principle.

It also checks itself against a number computed a different way: each cue must land inside the section
window that `master.py` recorded while assembling the file. Two independent derivations of the same
timeline, so a mistake in either one shows up here instead of in the finished film.

    python3 audio/align.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

FFBIN = (r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
         r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin")
if Path(FFBIN).is_dir():
    os.environ["PATH"] += os.pathsep + FFBIN

import numpy as np  # noqa: E402

AUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIO))
from sections import load  # noqa: E402
from take_qa import words  # noqa: E402  — one word definition, shared


def video_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "engine").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree")


VIDEO = video_root(AUDIO)
FILM = AUDIO.parent
WORK = VIDEO / "out/education/how-to-make-an-explainer"


def stamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def align_words(script_words: list[str], heard: list[dict]) -> list[int | None]:
    """For each script word, the index of the heard word it corresponds to, or None."""
    ref = script_words
    hyp = [w["word"] for w in heard]
    n, m = len(ref), len(hyp)
    cost = np.zeros((n + 1, m + 1), dtype=np.int32)
    cost[:, 0] = np.arange(n + 1)
    cost[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i, j] = min(cost[i - 1, j] + 1, cost[i, j - 1] + 1,
                             cost[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    mapping: list[int | None] = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        if cost[i, j] == cost[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] == hyp[j - 1]:
                mapping[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif cost[i, j] == cost[i - 1, j] + 1:
            i -= 1
        else:
            j -= 1
    return mapping


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="small.en")
    args = ap.parse_args()

    master = json.loads((WORK / "master.json").read_text(encoding="utf-8"))
    script = load()
    cue_text = {}
    cue_order = []
    for section in script:
        for cue, line in zip(section["cues"], section["lines"]):
            cue_text[cue] = line
            cue_order.append((cue, section["id"], section["scene"], section["scene_title"]))

    import whisper
    model = whisper.load_model(args.model)
    print(f"aligning {master['path']}", flush=True)
    result = model.transcribe(master["path"], language="en", fp16=False, temperature=0.0,
                              condition_on_previous_text=False, word_timestamps=True)
    heard = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            token = re.sub(r"[^a-z0-9]", "", w["word"].lower())
            if token:
                heard.append({"word": token, "start": float(w["start"]), "end": float(w["end"])})

    flat, owner = [], []
    for cue, section_id, scene, _ in cue_order:
        for token in words(cue_text[cue]):
            flat.append(token)
            owner.append(cue)
    mapping = align_words(flat, heard)
    matched = sum(1 for m in mapping if m is not None)

    times: dict[int, dict] = {}
    for index, cue in enumerate(owner):
        if mapping[index] is None:
            continue
        word = heard[mapping[index]]
        row = times.setdefault(cue, {"start": word["start"], "end": word["end"], "words": 0})
        row["start"] = min(row["start"], word["start"])
        row["end"] = max(row["end"], word["end"])
        row["words"] += 1

    section_window = {row["section"]: row for row in master["sections"]}
    cues, problems = [], []
    for position, (cue, section_id, scene, scene_title) in enumerate(cue_order):
        row = times.get(cue)
        if row is None:
            problems.append(f"cue {cue}: no word aligned")
            continue
        window = section_window[section_id]
        inside = window["start_s"] - 0.25 <= row["start"] <= window["end_s"] + 0.25
        if not inside:
            problems.append(f"cue {cue}: starts {row['start']:.2f} s, outside section "
                            f"{section_id} ({window['start_s']:.2f}–{window['end_s']:.2f})")
        cues.append({
            "cue": cue, "section": section_id, "scene": scene, "scene_title": scene_title,
            "start_s": round(row["start"], 3), "end_s": round(row["end"], 3),
            "words_aligned": row["words"], "words_total": len(words(cue_text[cue])),
            "text": cue_text[cue], "inside_section_window": inside,
        })

    for index, row in enumerate(cues):
        nxt = cues[index + 1]["start_s"] if index + 1 < len(cues) else master["duration_s"]
        row["slot_s"] = round(nxt - row["start_s"], 3)

    (WORK / "cues.json").write_text(json.dumps({
        "master": master["path"], "master_sha256": master["sha256"],
        "duration_s": master["duration_s"],
        "words_aligned": matched, "words_total": len(flat),
        "alignment_fraction": round(matched / max(len(flat), 1), 4),
        "whisper_model": args.model, "problems": problems, "cues": cues,
        "scenes": master["scenes"],
    }, indent=2), encoding="utf-8")

    srt = []
    for index, row in enumerate(cues, 1):
        # A caption ends when its words end, not when the next one starts: it marks speech that
        # exists rather than filling the gap after it.
        srt.append(f"{index}\n{stamp(row['start_s'])} --> {stamp(row['end_s'])}\n{row['text']}\n")
    (FILM / "script/captions.srt").write_text("\n".join(srt), encoding="utf-8")

    print(f"  {matched}/{len(flat)} words aligned ({matched / len(flat):.1%})")
    print(f"  {len(cues)} cues timed; {len(problems)} problem(s)")
    for line in problems[:10]:
        print(f"    {line}")
    slots = [row["slot_s"] for row in cues]
    print(f"  slots {min(slots):.1f}–{max(slots):.1f} s, mean {sum(slots) / len(slots):.2f} s")
    print(f"  captions: {FILM / 'script/captions.srt'}")
    print(f"  cue sheet: {WORK / 'cues.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
