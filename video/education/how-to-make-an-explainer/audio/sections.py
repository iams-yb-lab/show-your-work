#!/usr/bin/env python3
"""
sections.py — turn the script into the units that get generated, and nothing else.

A performance section is one continuous take. The script marks them with `[A]`, `[B]`, …; this module
parses them out with their spoken text, so no other tool has to re-read the markdown or guess where a
performance begins. Every downstream step imports from here.

Pronunciation aliases are applied to what the model is *sent*. The script text itself is never
changed to hide a generation problem, and both forms are kept side by side.

    python3 audio/sections.py            # list the sections
    python3 audio/sections.py --json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FILM = Path(__file__).resolve().parent.parent
SCRIPT = FILM / "script/voiceover-script.md"

SCENE = re.compile(r"^##\s+Scene\s+(\d+)\s+—\s+(.+?)\s*$")
CUE = re.compile(r"^(\d+)\.\s+(.*\S)$")
MARK = re.compile(r"^\[([A-Z]+)\]\s*")
TRACE = re.compile(r"\s*→\s*.+?$")

# Sent to the model only. The displayed script and the captions keep the original spelling.
ALIASES = {
    "VS Code": "V S Code",
    # Chatterbox reads "Claude" as /klɒd/ — a transcriber heard "CLOD" on every take of section R.
    # It is the one brand name in the film, so it gets a spelling the model says correctly.
    "Claude": "Clawd",
}


def spoken(text: str) -> str:
    for original, said in ALIASES.items():
        text = text.replace(original, said)
    # Chatterbox reads a bare em dash as a word break, not a pause; a comma performs it.
    return text.replace("—", ",")


def load() -> list[dict]:
    sections: list[dict] = []
    scene = None
    for raw in SCRIPT.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if m := SCENE.match(line):
            scene = {"n": int(m.group(1)), "title": m.group(2)}
            continue
        if scene is None:
            continue
        if not (m := CUE.match(line)):
            continue
        body = TRACE.sub("", m.group(2))
        mark = MARK.match(body)
        if mark:
            sections.append({
                "id": mark.group(1), "scene": scene["n"], "scene_title": scene["title"],
                "lines": [], "cues": [],
            })
            body = MARK.sub("", body)
        if not sections:
            raise SystemExit(f"line {m.group(1)} appears before any [X] performance mark")
        sections[-1]["cues"].append(int(m.group(1)))
        sections[-1]["lines"].append(body)

    for s in sections:
        s["text"] = " ".join(s["lines"])
        s["said"] = spoken(s["text"])
        s["words"] = len([t for t in s["text"].split() if re.search(r"[A-Za-z0-9]", t)])
    return sections


def by_id(section_id: str) -> dict:
    for s in load():
        if s["id"] == section_id:
            return s
    raise KeyError(section_id)


def main(argv: list[str]) -> int:
    sections = load()
    if "--json" in argv:
        print(json.dumps(sections, indent=2))
        return 0
    print(f"{len(sections)} performance sections, "
          f"{sum(s['words'] for s in sections)} words")
    for s in sections:
        cues = f"{s['cues'][0]}–{s['cues'][-1]}" if len(s['cues']) > 1 else str(s['cues'][0])
        print(f"  [{s['id']:<2}] scene {s['scene']}  lines {cues:<7} {s['words']:>3} words  "
              f"{s['text'][:56]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
