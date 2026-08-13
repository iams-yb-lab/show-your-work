#!/usr/bin/env python3
"""
script_stats.py — measure and police the script before a line of it is recorded.

Stage 2's cross-check. It never opens the source document to judge *whether* a claim is true — that
is the human's job — but it does insist that every line names where it came from, that no line
smuggles in the vocabulary the brief banned, and that the whole thing fits the runtime that was
decided at stage 0.

    python3 tools/script_stats.py            # table, exits non-zero on a violation
    python3 tools/script_stats.py --json

Note what each check is aimed at, because a check aimed at the wrong artifact manufactures failures.
Everything here is about a *written script*: the predicted duration is a prediction, not a
measurement, and it gets replaced wholesale by the recording at stage 3.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_numbers import words  # one definition of "word", shared with the number pass

FILM = Path(__file__).resolve().parent.parent
SCRIPT = FILM / "script/voiceover-script.md"

SCENE = re.compile(r"^##\s+Scene\s+(\d+)\s+—\s+(.+?)\s*$")
CUE = re.compile(r"^(\d+)\.\s+(.*\S)$")
SECTION_MARK = re.compile(r"^\[([A-Z]+)\]\s*")
TRACE = re.compile(r"\s*→\s*(.+?)\s*$")

# Decided at stage 0: the narration carries no working vocabulary at all. The picture labels these
# words on screen instead, so the viewer leaves able to read the skill's files without having been
# lectured mid-sentence. Anything here in spoken text is a violation, not a style note.
BANNED_VOCABULARY = [
    "cue", "slot", "cue sheet", "timecode", "narration master", "tolerance", "gate ",
    "lufs", "dbtp", "true peak", "wpm", "words per minute", "sample rate", "waveform",
]
# The film may not claim how anything sounds — this repo has no instrument for it.
BANNED_TASTE = ["sounds natural", "sounds human", "sounds like a real", "indistinguishable",
                "lifelike", "studio quality", "professional voice"]
# Nothing specific to the hardware this repo happens to be about.
BANNED_SUBJECT = ["thermistor", "thermoelectric", "millikelvin", "kelvin", "ppm", "ratiometric",
                  "designator", "lcsc", "setpoint", "pid"]

# TRIAL.wpm, the only end-to-end rate this repo has actually seen: words over a finished master,
# silence included. A prediction, and labelled as one everywhere it appears.
RATE_WPM = 188.4


def parse():
    scenes, cues = [], []
    for raw in SCRIPT.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if m := SCENE.match(line):
            scenes.append({"n": int(m.group(1)), "title": m.group(2), "cues": []})
            continue
        if not scenes:
            continue
        if m := CUE.match(line):
            body = m.group(2)
            trace = TRACE.search(body)
            spoken = TRACE.sub("", body)
            section = None
            if mark := SECTION_MARK.match(spoken):
                section = mark.group(1)
                spoken = SECTION_MARK.sub("", spoken)
            cue = {
                "n": int(m.group(1)),
                "scene": scenes[-1]["n"],
                "section": section,
                "spoken": spoken,
                "trace": trace.group(1) if trace else None,
                "words": words(spoken),
            }
            cues.append(cue)
            scenes[-1]["cues"].append(cue)
    return scenes, cues


def violations(cues):
    out = []
    for c in cues:
        low = c["spoken"].lower()
        if not c["trace"]:
            out.append((c["n"], "no trace — every line names the section it came from"))
        for term in BANNED_VOCABULARY:
            if term in low:
                out.append((c["n"], f"working vocabulary spoken: {term!r} — the picture labels it"))
        for term in BANNED_TASTE:
            if term in low:
                out.append((c["n"], f"taste claim about sound: {term!r} — nothing measures this"))
        for term in BANNED_SUBJECT:
            if re.search(rf"\b{re.escape(term)}\b", low):
                out.append((c["n"], f"subject-specific term: {term!r} — the film must travel"))
    return out


SPELLED = (r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|twenty|"
           r"thirty|forty|fifty|hundred")
UNIT = (r"second|seconds|minute|minutes|word|words|frame|frames|percent|times|"
        r"soundtracks|takes|scenes|lines")
# A quantitative claim, not an enumerator. "Two. Everything in it is true" is counting the points of
# an argument; "about two seconds" is a number that must be a rounding of a row in NUMBERS.md.
QUANTITY = re.compile(
    rf"\b(?:\d+(?:\.\d+)?|(?:about|roughly|around|nearly|over)\s+(?:{SPELLED}))\b"
    rf"|\b(?:{SPELLED})\s+(?:\w+\s+)?(?:{UNIT})\b", re.I)


def numbers_for_review(cues):
    """Quantitative claims in spoken text. Not a failure — a short list for a human to check against
    NUMBERS.md, because rounding is legal and inventing is not. Enumerators are excluded: a script
    that says "One." to open an argument is not making a measurement."""
    found = []
    for c in cues:
        hits = sorted({h.strip() for h in QUANTITY.findall(c["spoken"])} |
                      {m.group(0).strip() for m in QUANTITY.finditer(c["spoken"])})
        if hits:
            found.append((c["n"], [h for h in hits if h]))
    return found


def main(argv):
    scenes, cues = parse()
    total_words = sum(c["words"] for c in cues)
    predicted = total_words / RATE_WPM * 60
    bad = violations(cues)

    report = {
        "scenes": len(scenes),
        "cues": len(cues),
        "words": total_words,
        "performance_sections": len({c["section"] for c in cues if c["section"]}),
        "predicted_runtime_s": round(predicted, 1),
        "rate_wpm_assumed": RATE_WPM,
        "per_scene": [{"n": s["n"], "title": s["title"], "cues": len(s["cues"]),
                       "words": sum(c["words"] for c in s["cues"]),
                       "predicted_s": round(sum(c["words"] for c in s["cues"]) / RATE_WPM * 60, 1)}
                      for s in scenes],
        "violations": [{"cue": n, "problem": p} for n, p in bad],
        "numbers_to_check": [{"cue": n, "found": h} for n, h in numbers_for_review(cues)],
    }

    if "--json" in argv:
        print(json.dumps(report, indent=2))
        return 1 if bad else 0

    print(f"{report['scenes']} scenes, {report['cues']} lines, {report['words']} words, "
          f"{report['performance_sections']} performance sections")
    print(f"predicted {int(predicted // 60)}:{predicted % 60:04.1f} at {RATE_WPM} wpm — "
          f"A PREDICTION. Stage 3 replaces it with the recording.")
    longest = max(cues, key=lambda c: c["words"])
    print(f"longest line {longest['n']}: {longest['words']} words "
          f"(~{longest['words'] / RATE_WPM * 60:.1f} s)")
    for s in report["per_scene"]:
        print(f"  scene {s['n']}  {s['cues']:>2} lines  {s['words']:>3} words  "
              f"~{s['predicted_s']:>5.1f} s   {s['title']}")
    if report["numbers_to_check"]:
        print("numbers spoken — check each against NUMBERS.md by hand:")
        for row in report["numbers_to_check"]:
            print(f"  line {row['cue']}: {', '.join(row['found'])}")
    if bad:
        print(f"\n{len(bad)} violation(s):")
        for row in report["violations"]:
            print(f"  line {row['cue']}: {row['problem']}")
        return 1
    print("no violations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
