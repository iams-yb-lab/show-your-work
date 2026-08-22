#!/usr/bin/env python3
"""
handoff.py — generate the prompt the user pastes into Claude Design.

Every timecode in the prompt is read from the measured cue sheet rather than typed, so the prompt
cannot disagree with the audio it was cut from. The only thing authored here is `DIRECTIONS`: one
instruction per cue, in the source document's own vocabulary.

    python3 tools/handoff.py            # writes DESIGN-PROMPT.md
    python3 tools/handoff.py --check    # verify only: every cue has a direction, times agree
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FILM = Path(__file__).resolve().parent.parent


def skills_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "_shared").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a skills tree")


SKILLS = skills_root(FILM)
WORK = SKILLS.parents[1] / "out/education/how-to-make-an-explainer"

REGISTER = """Dark, typographic motion graphics. The film's subject is a process, so the picture is
built from the artifacts of that process rather than from stock imagery: a checklist that ticks, a
document with one fact lit up, a script with each line's seconds drawn beside it, a waveform, a scene
table, a prompt being pasted. Nothing is photographed. One accent colour, used to mean "this is the
thing being talked about right now" and never decoratively. Type is the main character; motion is slow
and purposeful, never bouncy. Every scene opens on a held frame so the music mark lands on the cut."""

# One instruction per cue, in the vocabulary of SOURCE.md. Nothing here introduces an idea the
# narration does not already carry.
DIRECTIONS = {
    1: "A finished thing, drawn as a clean geometric object, complete and still. Then faces or figures appear around it as abstract marks — an audience arriving after the fact.",
    2: "The object shrinks into a video frame: a small player rectangle with a short timeline. Beside it, the words A FEW CLEAN MINUTES.",
    3: "A crowded editing timeline slides in from the side, dense with tracks, and is pushed back out. It should look like work nobody wants.",
    4: "A hand-off gesture, abstract: the object passes from one side of frame to a simple machine outline on the other, which returns it polished.",
    5: "Two labels settle side by side: THINGS IT DECIDES and THINGS YOU DECIDE. The second is the accent colour. Hold.",
    6: "An application window opens, drawn not photographed, with a text box in it. A line of typed instruction appears: install the repository. Then VS CODE appears as a second, equal option.",
    7: "Three struck-through labels stack up: CONFIGURE, EDITING SOFTWARE, DOWNLOADS. Each one greys out as it is dismissed.",
    8: "The window recedes and four numbered plates appear in a row, unlabelled for now — the four stages, arriving as shapes before they get names.",
    9: "A single plate lifts and a small question mark rests on it, with the word APPROVE beneath. It waits, visibly, rather than advancing.",
    10: "Clear to ground. THREE THINGS counts up as three empty rows.",
    11: "Row one fills: a target with one figure standing at its centre and a crowd greyed out behind it. Label AIMED AT SOMEONE.",
    12: "Row two fills: a claim in quotation marks with a thin line drawn from it down to a document beneath. Label TRUE, AND YOU CAN SAY WHY.",
    13: "The same claim, now with a wrong number in it, glowing in the accent colour while a confident waveform runs under it. Uncomfortable, briefly.",
    14: "Row three fills: a caption box drifting a beat behind a waveform, then snapping into place. Label NOTHING SOUNDS WRONG.",
    15: "A viewer figure turns away. No explanation on screen. Hold on the empty frame a moment longer than feels comfortable.",
    16: "The four plates return, now in a single row with an arrow between each. This is the architecture card and it should read as the film's spine.",
    17: "Plate one lights: THE DOCUMENT, with a page of text behind it and one line highlighted.",
    18: "Plate two lights: THE SCRIPT, with lines of narration each carrying a small bar showing its seconds.",
    19: "Plate three lights: THE SOUND, with a waveform, and a clock icon moving from the picture plate onto this one.",
    20: "Plate four lights: THE PICTURE, drawn as frames filling a fixed-width box that is already the right size.",
    21: "A bracket appears around all four plates, labelled CLAUDE. Small motion inside each plate — work happening.",
    22: "Three items step outside the bracket: WHO IT'S FOR, WHAT'S TRUE, YES OR NO. Accent colour, larger than the plates.",
    23: "A number on the document quietly changes from fresh to stale — same digits, different colour — while the machine outline carries on unaware.",
    24: "Scene opens on plate one, enlarged. A conversation forms as two columns of short lines, a document assembling on the right as it goes.",
    25: "Two stamps drop onto figures in that document: MEASURED and PLANNED. Then a duplicated fact appears twice and one copy is struck out.",
    26: "The document turns to face the viewer. A single approval mark waits on it, accent colour.",
    27: "A wrong number in the document is blown up until it fills the frame. Nothing else changes; it just gets bigger.",
    28: "Cut to plate two. The document's lines flow into script lines, and a bar grows beside each one, longer for longer lines. No two bars the same length.",
    29: "A line arrives without a thread back to the document and is refused — it slides out of frame.",
    30: "One script line is held under a cursor while a re-record symbol appears beside it and is crossed out. Label THE LAST CHEAP MOMENT.",
    31: "Cut to plate three. A waveform draws itself left to right and then locks, with a padlock or frozen edge — one file, finished.",
    32: "The picture plate is shown empty and unstarted beside the finished waveform. Emphasise the order: sound solid, picture blank.",
    33: "A picture strip of fixed width. A frame in its middle is changed and the whole strip has to be redrawn — show the redraw cost as the strip flickering back to the start.",
    34: "A sentence drawn as an elastic band that will not compress. Squeeze it and the words visibly crowd; release and they settle.",
    35: "Two boxes, one rigid and one elastic, and whichever is drawn first becomes the container the other must fit inside. Show it both ways.",
    36: "Picture-first: the sentence is cut short, hurried, then spliced from two pieces with a visible seam. All three damages named on screen, briefly.",
    37: "Sound-first: the picture box simply stretches to fit, and a diagram sits a moment longer. Nothing breaks. No label needed.",
    38: "One line of type alone on the ground: THE THING THAT CAN'T BE SQUEEZED SETS THE CLOCK.",
    39: "Captions drop out of the waveform one word at a time, each landing under the sound it belongs to. Then scene-boundary marks fall out of the same waveform.",
    40: "The script and the transcript sit side by side; one word differs and is ringed in the accent colour.",
    41: "Two checkmarks appear beside TIMING and PRONUNCIATION. A third row, SOUNDS LIKE A PERSON, stays empty — no mark is available for it.",
    42: "Two finished soundtrack bars, both showing every check passed, both dropped into a bin. Then a single ear or listener mark replaces them.",
    43: "Cut to plate four. The scene table appears with its durations already filled in, and empty frames waiting inside each row.",
    44: "Everything collapses into one document: a prompt, shown as a single block of text with a copy button.",
    45: "Four contents fly into that block and settle: the scene list, what each scene shows, the look, and file paths.",
    46: "The block is picked up and dropped into a second window. Then a wait — a held frame with a quiet progress mark.",
    47: "A finished video plays back small in frame with a speaker mark lit beside it, next to a rejected alternative: the same frame with a crossed-out silent mark.",
    48: "The four plates return in order, then reverse, and each reversal cracks — one at a time, not all at once.",
    49: "Reversal one: the picture drawn first, and the sentence inside it breaking. Cost label: A RE-RENDER.",
    50: "Reversal two: no document, and the video becomes the place where the thinking happens — errors amplified through a loudspeaker shape.",
    51: "Reversal three: a keystroke versus a whole recording, drawn as two very different sized blocks.",
    52: "Reversal four: no sound, and every duration on the scene table turns into a question mark.",
    53: "Clear to ground. One repository mark, and the words THE LINK IS BELOW THIS VIDEO. No URL on screen.",
    54: "Two lines of type, plain: BUILT AND VERIFIED WITH CLAUDE, and beneath it, OTHER MODELS UNTESTED. The second is deliberately not styled as a warning.",
    55: "The finished object from cue 1 returns, now with an audience around it that is facing it. Hold to the end of the audio.",
}


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    cues = json.loads((WORK / "cues.json").read_text(encoding="utf-8"))
    master = json.loads((WORK / "master.json").read_text(encoding="utf-8"))
    mix = json.loads((WORK / "mix.json").read_text(encoding="utf-8"))

    missing = [c["cue"] for c in cues["cues"] if c["cue"] not in DIRECTIONS]
    extra = [n for n in DIRECTIONS if n not in {c["cue"] for c in cues["cues"]}]
    scenes = cues["scenes"]
    table_sum = sum(s["duration_s"] for s in scenes)
    problems = []
    if missing:
        problems.append(f"cues with no direction: {missing}")
    if extra:
        problems.append(f"directions for cues that do not exist: {extra}")
    if abs(table_sum - mix["duration_s"]) > 0.05:
        problems.append(f"scene table sums to {table_sum:.3f} s, audio is {mix['duration_s']:.3f} s")
    for cue in cues["cues"]:
        scene = next(s for s in scenes if s["scene"] == cue["scene"])
        if not (scene["in_s"] - 0.05 <= cue["start_s"] <= scene["out_s"] + 0.05):
            problems.append(f"cue {cue['cue']} at {cue['start_s']} s is outside scene {scene['scene']}")
    if problems:
        print("HANDOFF NOT READY")
        for line in problems:
            print(f"  {line}")
        return 1
    print(f"checks pass: {len(cues['cues'])} cues, {len(scenes)} scenes, "
          f"table {table_sum:.3f} s vs audio {mix['duration_s']:.3f} s")
    if args.check:
        return 0

    lines = []
    w = lines.append
    w("# Paste this into Claude Design")
    w("")
    w("You are drawing the picture for a finished explainer video. **The audio already exists and is")
    w("final.** Every duration below is decided; nothing about the sound may be re-cut, re-timed or")
    w("regenerated to suit the picture. The picture fills the time it is given.")
    w("")
    w("## What you are delivering")
    w("")
    w("**A self-contained HTML bundle that plays the film — not a video file.** You cannot encode video;")
    w("your encoder only fires from a human clicking Export, so do not try, and do not ask for ffmpeg to")
    w("be run on your side. Hand back the page. Rendering it to a 1080p file is done here.")
    w("")
    w("Two things about that page, because they are the ones that go wrong:")
    w("")
    w(f"- **Embed the combined audio track named below** — narration *and music*, {mix['duration_s']:.1f} s.")
    w("  A bundle that carries the narration alone is silent where the music should be, and that has")
    w("  already happened once on this film.")
    w("- **Leave burned-in captions off.** The caption file ships separately; frames with subtitles baked")
    w("  into them cannot be un-baked.")
    w("")
    w("## Where everything is")
    w("")
    w("| file | what it is |")
    w("|---|---|")
    w(f"| `{mix['path']}` | **the audio for the page** — narration and music, lossless 48 kHz stereo, "
      f"{mix['delivered']['lufs']:+.2f} LUFS, {mix['delivered']['true_peak_dbtp']:+.2f} dBTP. Use this one. |")
    w(f"| `{master['path']}` | narration only, no music. **Not this one** — it is the mistake to avoid. |")
    w(f"| `{FILM / 'script/captions.srt'}` | captions, timed off the audio, one entry per line of narration |")
    w(f"| `{WORK / 'cues.json'}` | the machine-readable cue sheet this prompt was generated from |")
    w(f"| `{FILM / 'images/MANIFEST.md'}` | the image manifest. **It is deliberately empty** — nothing in this film is photographed. |")
    w(f"| `{FILM / 'SOURCE.md'}` | the source document, if you need the meaning behind a line |")
    w("")
    w("## Delivery spec")
    w("")
    w("- **1920×1080, 16:9, 30 fps** — the page must render at that size without cropping or letterboxing")
    w(f"- **Exactly {mix['duration_s']:.1f} s of timeline**, ending when the audio ends")
    w("- Captions available but **off by default**; the `.srt` is delivered separately")
    w("")
    w("## The look")
    w("")
    for paragraph in REGISTER.strip().split("\n"):
        w(paragraph)
    w("")
    w("## Scene table — locked")
    w("")
    w("| scene | title | in | out | duration | hole before first word |")
    w("|---|---|---|---|---|---|")
    for s in scenes:
        w(f"| {s['scene']} | {s['title']} | {clock(s['in_s'])} | {clock(s['out_s'])} | "
          f"{s['duration_s']:.1f} s | {s['hole_s']:.2f} s |")
    w("")
    w("**Scene boundaries came from the audio and are contiguous** — each scene ends exactly where the")
    w(f"next begins, and the table sums to the file duration. The hole at the top of every scene is")
    w("silence with a music mark in it: put the cut there, and hold the first frame of the new scene")
    w("through it. Do not speak-over it and do not fill it with motion.")
    w("")
    w("## Cue sheet, with one instruction per line")
    w("")
    w("`start` is when the words begin. `slot` is how long that line has before the next one starts —")
    w("that is the time its visual has, and no more.")
    w("")
    for s in scenes:
        w(f"### Scene {s['scene']} — {s['title']}  ({clock(s['in_s'])} → {clock(s['out_s'])})")
        w("")
        for cue in [c for c in cues["cues"] if c["scene"] == s["scene"]]:
            w(f"**{clock(cue['start_s'])}** · slot {cue['slot_s']:.1f} s · line {cue['cue']}")
            w("")
            w(f"> {cue['text']}")
            w("")
            w(f"{DIRECTIONS[cue['cue']]}")
            w("")
    w("## Do not draw")
    w("")
    w("- **No photographs, no stock imagery, no logos.** The image manifest is empty on purpose.")
    w("- **No hardware, circuit boards, lab equipment or scientific instruments.** The film has to work")
    w("  for whatever the viewer built; naming a field narrows it.")
    w("- **No URLs, repository names, skill names or file paths on screen.** The link lives in the video")
    w("  description. Cue 53 says so out loud.")
    w("- **No product UI screenshots or recognisable brand chrome.** Draw a generic app window instead.")
    w("- **No tolerances, gate names, checklists internals, loudness figures or engineering plumbing.**")
    w("  The viewer came for a clear video, not for a quality system.")
    w("- **No claim about how anything sounds** — not natural, not human, not studio quality.")
    w("- **No number that is not spoken in the line it sits under.**")
    w("- **No bouncy, springy or comedic motion**, and no whooshes, ticks or transitions implying sound;")
    w("  the audio is finished and cannot accommodate them.")
    w("")
    w("## Hand back the page, and say four things about it")
    w("")
    w("No rendering, no muxing, no export click. Just the bundle, plus these four facts so the render on")
    w("this side does not have to be guessed at:")
    w("")
    w("1. **which audio you embedded**, by filename, and whether it is the combined mix or narration only;")
    w("2. **the page's total timeline length**, in seconds, to three decimals;")
    w("3. **how the page is driven** — does it play on load, on a click, or from a JS timeline object, and")
    w("   is there a single call or variable that seeks to a given second;")
    w("4. **anything in it that is not deterministic** — random seeds, `Date.now()`, animations tied to")
    w("   wall-clock time rather than the timeline. A frame-by-frame render of a page that drifts will")
    w("   not match the audio, and that is the one failure that is invisible until the whole film is out.")
    w("")
    w("**You have everything. Nothing here needs to be asked back.**")

    out = FILM / "DESIGN-PROMPT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
