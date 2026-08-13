#!/usr/bin/env python3
"""
take_qa.py — transcribe and measure every raw take, then pick one per section. Runs in editx-venv.

Two jobs, in this order, because the method's order is not negotiable: **reject wrong words before
judging anything else**, then choose. And the choice is made *for the narrator*, not for the line —
among the word-perfect takes, the one whose median pitch sits closest to the profile's, so the same
person is speaking in every section.

This is aimed at RAW TAKES. It carries no level or peak limit of any kind: a raw take is allowed to
sit above full scale, and reducing it is delivery's job, not QA's.

    python3 audio/take_qa.py                      # every take in the generation record
    python3 audio/take_qa.py --sections A,L,Q,R
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

FFMPEG_BIN = (r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
              r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin")
if Path(FFMPEG_BIN).is_dir():
    os.environ["PATH"] += os.pathsep + FFMPEG_BIN

AUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIO))


def video_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "engine").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree")


VIDEO = video_root(AUDIO)
WORK = VIDEO / "out/education/how-to-make-an-explainer"
PROFILE = json.loads((VIDEO / "natural-voice/profiles/warm-natural/profile.json")
                     .read_text(encoding="utf-8"))
PROFILE_F0 = PROFILE["prompt_selection"]["median_f0_hz"]

# Chosen by ear, section → take, and it beats every measurement below except the word check.
# "I think take 2 is the best" — on the audition passages, 2026-08-13.
EAR = {"A": 2, "L": 2, "Q": 2, "R": 2}

# Rate ceiling for *dropped* words only — substitutions are rejected outright, at any rate. 6 %
# because the transcriber drops boundary words that the voice demonstrably spoke (see below).
WER_CEILING = 0.06


# Tokens that mean the same event, so a transcriber's spelling is not mistaken for a wrong word.
# Each group is here because it was *measured*, and each keeps the distinction that matters:
#   claude   the model is sent "Clawd" and says it correctly; whisper writes "Claude" or "Cloud".
#            **"clod" is deliberately not in this group** — that is the mispronunciation the alias
#            exists to fix, and it has to stay detectable.
#   youd     "you'd" is transcribed as "you" often enough that it says nothing about the voice.
EQUIVALENT = [
    {"claude", "clawd", "cloud"},
    {"youd", "you"},
]
CANON = {token: sorted(group)[0] for group in EQUIVALENT for token in group}

# The transcriber writes digits for spoken number words — "three" comes back as "3" in six sections
# here. That is orthography, not a wrong word, so both spellings collapse to one token.
NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
           "eleven", "twelve", "thirteen"]
CANON.update({str(value): word for value, word in enumerate(NUMBERS)})


def words(text: str) -> list[str]:
    """Compare like with like: case, punctuation and internal apostrophes all removed, so a
    transcriber writing "don't" and a script writing "don't" produce the same token. A quote mark
    left in place once made 5 % of a word-perfect take unmatchable. Then the equivalence groups
    above collapse spellings of the same spoken word."""
    out = []
    for token in text.split():
        stripped = re.sub(r"[^a-z0-9]", "", token.lower())
        if stripped:
            out.append(CANON.get(stripped, stripped))
    return out


def align(reference: str, hypothesis: str) -> tuple[float, list[dict]]:
    """Word-level edit distance *and the edits themselves*.

    The rate alone is not enough and this film proved it: a take that said "Document last" where the
    script says "Sound last" scored 0.013 and passed a 2 % ceiling, while inverting the sentence it
    was in. One substitution in the wrong place is not a small error, so the edits are reported and
    a human decides — a rate cannot know which word was load-bearing."""
    ref, hyp = words(reference), words(hypothesis)
    if not ref:
        return 0.0, []
    n, m = len(ref), len(hyp)
    cost = np.zeros((n + 1, m + 1), dtype=np.int32)
    cost[:, 0] = np.arange(n + 1)
    cost[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i, j] = min(cost[i - 1, j] + 1, cost[i, j - 1] + 1,
                             cost[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    edits, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and cost[i, j] == cost[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] != hyp[j - 1]:
                edits.append({"op": "substitute", "script": ref[i - 1], "heard": hyp[j - 1],
                              "at_word": i})
            i, j = i - 1, j - 1
        elif i > 0 and cost[i, j] == cost[i - 1, j] + 1:
            edits.append({"op": "drop", "script": ref[i - 1], "heard": None, "at_word": i})
            i -= 1
        else:
            edits.append({"op": "add", "script": None, "heard": hyp[j - 1], "at_word": i})
            j -= 1
    # float(), not the numpy scalar the matrix hands back: json cannot serialise np.float64, and it
    # fails at write time, after every take has been transcribed.
    return float(cost[n, m]) / n, list(reversed(edits))


def wer(reference: str, hypothesis: str) -> float:
    return align(reference, hypothesis)[0]


def median_f0(y: np.ndarray, sr: int) -> float:
    f0, voiced, _ = librosa.pyin(y, fmin=60, fmax=350, sr=sr, frame_length=2048)
    voiced_f0 = f0[np.isfinite(f0)]
    return float(np.median(voiced_f0)) if voiced_f0.size else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--rescore", action="store_true",
                    help="reuse transcripts already measured; redo only the scoring")
    args = ap.parse_args()

    record = json.loads((WORK / "generation.json").read_text(encoding="utf-8"))
    wanted = {s.strip().upper() for s in args.sections.split(",")} if args.sections else None
    takes = [t for t in record["takes"] if not wanted or t["section"] in wanted]
    if not takes:
        raise SystemExit("no takes match")

    # Transcribing is the expensive half; scoring is the half that gets calibrated. So transcripts
    # are cached and --rescore replays them. Changing an equivalence group then costs seconds rather
    # than an hour, which is the difference between calibrating a gate and living with a wrong one.
    cache = {}
    if (previous := WORK / "takes-qa.json").exists():
        cache = {(r["section"], r["take"]): r
                 for r in json.loads(previous.read_text(encoding="utf-8"))["takes"]}

    model = None
    if not args.rescore and any((t["section"], t["take"]) not in cache for t in takes):
        import whisper
        model = whisper.load_model(args.model)
        print(f"whisper {args.model} loaded", flush=True)
    print(f"{len(takes)} take(s), {len(cache)} cached", flush=True)

    rows = []
    for take in takes:
        cached = cache.get((take["section"], take["take"]))
        if cached and (args.rescore or model is None):
            heard, measured = cached["transcript"], cached
        elif model is None:
            print(f"  [{take['section']}] take {take['take']}: no cached transcript", flush=True)
            continue
        else:
            y, sr = sf.read(take["path"], dtype="float32", always_2d=False)
            if y.ndim > 1:
                y = y.mean(axis=1)
            y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
            # Peak-normalise only the copy handed to the transcriber: whisper is not the deliverable,
            # and a take above full scale would otherwise be clipped by its own front end.
            # condition_on_previous_text=False, deliberately: with it on, whisper carries its own
            # earlier output forward as a prompt and "corrects" a later line into an earlier parallel
            # phrase. Four takes of section Q reported "Document last" where the script says "Sound
            # last", and "Document last," appears two lines earlier in the same passage. A
            # transcriber that edits its own transcript cannot judge whether the voice was right.
            heard = model.transcribe(y16 / max(1.0, float(np.max(np.abs(y16)))), language="en",
                                     fp16=False, temperature=0.0,
                                     condition_on_previous_text=False)["text"].strip()
            measured = {"duration_s": round(len(y) / sr, 3),
                        "peak": round(float(np.max(np.abs(y))), 4),
                        "median_f0_hz": round(median_f0(y, sr), 2)}
        row = {
            "section": take["section"], "take": take["take"], "seed": take["seed"],
            "path": take["path"], "duration_s": measured["duration_s"],
            "peak": measured["peak"],
            "above_full_scale": bool(measured["peak"] > 1.0),
            "median_f0_hz": measured["median_f0_hz"],
            "transcript": heard,
            "wer_vs_script": round(wer(take["text"], heard), 4),
            "wer_vs_spoken": round(wer(take["said"], heard), 4),
        }
        against = take["said"] if row["wer_vs_spoken"] <= row["wer_vs_script"] else take["text"]
        row["wer"], row["edits"] = align(against, heard)
        row["wer"] = round(row["wer"], 4)
        # Word boundaries are the transcriber's opinion, not the voice's: "at every one" comes back
        # as "at everyone", which is the same sound and the same meaning. So if the two texts are
        # identical once every boundary is removed, the take is word-perfect whatever the alignment
        # said — and the alignment's "substitution" was an artifact of where the spaces landed.
        row["same_ignoring_word_breaks"] = "".join(words(against)) == "".join(words(heard))
        if row["same_ignoring_word_breaks"]:
            # The rate came from the alignment this rule just invalidated, so it goes too. Leaving
            # it in place rejected a word-perfect take of section D on a 7 % rate with zero edits.
            row["edits"], row["wer"] = [], 0.0
        row["substitutions"] = [e for e in row["edits"] if e["op"] == "substitute"]
        row["drops"] = [e for e in row["edits"] if e["op"] == "drop"]
        # **A substitution rejects the take; a drop does not.** Measured, not assumed: four takes of
        # section Q reported "sound" missing before "last and nothing sets the clock", and
        # transcribing that sentence *alone* returned "Sound last and nothing sets the clock". The
        # voice said the word; whisper loses the first word of a segment. A transcriber's
        # segmentation artifact is not evidence about the performance, so drops are reported and a
        # human decides, while a substitution — which changes what the film says — is fatal.
        row["words_ok"] = row["wer"] <= WER_CEILING and not row["substitutions"]
        row["f0_offset_hz"] = round(abs(row["median_f0_hz"] - PROFILE_F0), 2)
        rows.append(row)
        verdict = "words ok" if row["words_ok"] else "REJECTED"
        print(f"  [{row['section']}] take {row['take']}  {row['duration_s']:6.2f} s  "
              f"WER {row['wer']:.3f}  F0 {row['median_f0_hz']:6.1f} Hz "
              f"({row['f0_offset_hz']:+.1f} vs profile)  {verdict}", flush=True)
        for e in row["edits"]:
            print(f"        {e['op']:<10} script={e['script']!r} heard={e['heard']!r}", flush=True)

    selected, overridden, flagged = {}, {}, {}
    for section in sorted({r["section"] for r in rows}):
        candidates = [r for r in rows if r["section"] == section and r["words_ok"]]
        if not candidates:
            # No clean take, so the section is *not* dropped: the closest one is used and flagged for
            # a human to listen to. Some substitutions are genuinely undecidable from text — "in
            # order" against "an order" is the same sound — and a listener settles in three seconds
            # what more seeds might never settle.
            fallback = min((r for r in rows if r["section"] == section), key=lambda r: r["wer"])
            selected[section] = fallback["take"]
            flagged[section] = {
                "take": fallback["take"], "wer": fallback["wer"],
                "listen_for": [f"{e['script']!r} may have come out as {e['heard']!r}"
                               for e in fallback["substitutions"]],
            }
            print(f"  [{section}] no clean take — using take {fallback['take']} and flagging it: "
                  f"{'; '.join(flagged[section]['listen_for'])}", flush=True)
            continue
        # Select for the narrator: closest to the profile's own median pitch.
        best = min(candidates, key=lambda r: r["f0_offset_hz"])
        selected[section] = best["take"]
        # A human verdict outranks the pitch rule — ears are the authority here, metrics are not.
        # It does not outrank the word check: a take that says the wrong word cannot be chosen by
        # anyone, so the override is refused out loud rather than applied quietly.
        if (want := EAR.get(section)) is not None:
            chosen = next((r for r in candidates if r["take"] == want), None)
            if chosen:
                selected[section] = want
                overridden[section] = "human verdict"
            else:
                bad = next((r for r in rows if r["section"] == section and r["take"] == want), None)
                why = ("wrong words: " + ", ".join(f"{e['script']!r}→{e['heard']!r}"
                                                  for e in bad["substitutions"])) if bad else "no such take"
                overridden[section] = f"refused ({why}); kept take {best['take']}"
                print(f"  [{section}] override to take {want} REFUSED — {why}", flush=True)

    out = {
        "aimed_at": "raw takes",
        "wer_ceiling": WER_CEILING,
        "profile_median_f0_hz": PROFILE_F0,
        "selection_rule": "no substitutions first, then the human verdict, then median F0",
        "chosen_by_ear": EAR,
        "override_outcome": overridden,
        "flagged_for_listening": flagged,
        "whisper_model": args.model,
        "takes": rows,
        "selected": selected,
    }
    path = WORK / "takes-qa.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"selected: {selected}\nrecord: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
