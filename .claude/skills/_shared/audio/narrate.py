"""Speak the narration table in `narration-assembly-v2.md`, one WAV per line.

    python tools/narrate.py --out out/audio/vo

The markdown table is the only home for the lines and their frames -- this parses it rather
than carrying a copy, so editing a word in the document is the whole edit. Each line becomes
`vo_<frame>.wav` at 48 kHz mono, and the report says whether it fits the gap before the next
one. A line that overruns its slot is the one fault that matters here, because the fix is to
shorten the sentence, not to move it.

Voices come from Microsoft's neural set via `edge-tts`; the local SAPI voices are the old
concatenative ones and sound it. Needs network, and `ffmpeg` to decode the MP3 it returns.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dsp import SR, read_wav, write_wav24  # noqa: E402
from voice_chain import humanise  # noqa: E402

FPS = 30
# The assembly film's script, only as a default -- `--doc` overrides it, and the intro film
# passes its own. This module is shared engine; it knows one path and is told the rest.
DOC = (Path(__file__).resolve().parents[2]
       / "showoff-render" / "examples" / "assembly" / "script" / "narration-assembly-v2.md")
ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*[\d.]+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$")

# The Multilingual voices are a later generation than the plain Neural ones and the difference
# is not subtle -- they phrase and breathe where the older models recite. Microsoft's own
# personality tags are quoted, because they describe the models accurately.
VOICES = {
    "en-US-AndrewMultilingualNeural": "warm, confident, authentic, honest -- the default",
    "en-US-BrianMultilingualNeural": "approachable, casual, sincere; lighter than Andrew",
    "en-AU-WilliamMultilingualNeural": "Australian, friendly, a little drier",
    "en-US-SteffanNeural": "older model: darker and slower, more obviously read",
    "en-GB-RyanNeural": "older model: British, formal, the most 'announcer'",
}

# Per-line rate, as a deterministic wobble around the base. A narrator does not hold one tempo
# for 84 seconds; holding one is a large part of why text-to-speech sounds like text-to-speech.
RATE_WOBBLE = (-3, +2, -1, +3, -2, 0, +2, -3, +1, -2, +3)

FFMPEG_HINT = (
    r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)


def find_ffmpeg() -> str:
    """winget installs ffmpeg outside the shell's PATH on this machine, so `which` finds
    nothing and it looks absent. Check the known location before giving up."""
    return shutil.which("ffmpeg") or (FFMPEG_HINT if Path(FFMPEG_HINT).exists() else "")


def read_table(doc: Path):
    rows = []
    for line in doc.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m and not line.startswith("| frame"):
            rows.append((int(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    return sorted(rows)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", type=Path, default=DOC)
    ap.add_argument("--out", type=Path, default=Path("out/audio/vo"))
    ap.add_argument("--voice", default="en-US-AndrewMultilingualNeural")
    ap.add_argument("--rate", type=int, default=-9, help="base rate, per cent")
    # Pitch is left alone by default. Shifting a neural voice down is the fastest way to make
    # it sound processed; depth comes from the model and from the chest lift in voice_chain.
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--dry", action="store_true", help="skip the voice chain, for comparison")
    ap.add_argument("--wet", type=float, default=0.13, help="room level, 0-1")
    ap.add_argument("--list", action="store_true", help="print the candidate voices and exit")
    args = ap.parse_args()

    if args.list:
        for name, why in VOICES.items():
            print(f"  {name:32s} {why}")
        return 0

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        sys.exit("ffmpeg not found; it decodes what edge-tts returns")
    rows = read_table(args.doc)
    if not rows:
        sys.exit(f"no narration rows parsed out of {args.doc}")
    args.out.mkdir(parents=True, exist_ok=True)
    # Clear the directory first. The mixer takes every vo_*.wav it finds, so a line that moves
    # frame leaves its old file behind and the narrator says both -- which is exactly what
    # happened when the first pass at these timings was superseded: five stale lines, and a
    # mix with sixteen in it instead of eleven.
    stale = sorted(args.out.glob("vo_*.wav")) + sorted(args.out.glob("vo_*.mp3"))
    for f in stale:
        f.unlink()
    if stale:
        print(f"  cleared {len(stale)} file(s) from a previous run")

    print(f"{args.voice}  rate {args.rate:+d}% ±3  pitch {args.pitch}  "
          f"room {'off' if args.dry else f'{args.wet:.0%}'}   {len(rows)} lines")
    total_words = 0
    made = []
    raw = []
    for i, (frame, _screen, text) in enumerate(rows):
        mp3 = args.out / f"vo_{frame:04d}.mp3"
        wav = args.out / f"vo_{frame:04d}.wav"
        rate = f"{args.rate + RATE_WOBBLE[i % len(RATE_WOBBLE)]:+d}%"
        # The library, not the console script: `edge-tts` installs into a Scripts directory
        # that is not on this machine's PATH, and the API takes the text as a Python string,
        # so the em dashes and apostrophes in the document need no escaping of our own.
        async def speak(t=text, dest=mp3, r=rate):
            await edge_tts.Communicate(t, args.voice, rate=r,
                                       pitch=args.pitch).save(str(dest))
        try:
            asyncio.run(speak())
        except Exception as exc:                                   # noqa: BLE001
            sys.exit(f"edge-tts failed on frame {frame}: {exc}")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(mp3),
                        "-ar", str(SR), "-ac", "1", str(wav)], check=True)
        mp3.unlink()
        raw.append((frame, wav, read_wav(wav)[0]))

        dur = wav_seconds(wav)
        start = (frame - 1) / FPS
        nxt = (rows[i + 1][0] - 1) / FPS if i + 1 < len(rows) else 84.0
        slot = nxt - start
        total_words += len(text.split())
        flag = "" if dur <= slot else f"  OVERRUNS BY {dur - slot:.2f} s -- shorten the line"
        made.append((frame, start, dur, slot, text))
        print(f"  f{frame:4d}  {start:6.2f} s  {dur:5.2f} s spoken / {slot:5.2f} s slot"
              f"  {len(text.split()):2d} w  rate {rate}{flag}")

    # One gain for all of them, from the loudest line, so the quiet ones stay quiet. Each line
    # gets its own room seed: identical early reflections on every sentence would put the
    # narrator in a different room from himself each time he stopped talking.
    if not args.dry:
        processed = [(fr, w, humanise(x, wet=args.wet, seed=5 + 3 * k))
                     for k, (fr, w, x) in enumerate(raw)]
        peak = max(float(np.abs(p).max()) for _fr, _w, p in processed)
        for _fr, w, p in processed:
            write_wav24(w, p / peak * 0.89)
        print(f"  voice chain: de-ess, chest, presence, compress, saturate, drift, "
              f"{args.wet:.0%} room -- {len(processed)} lines, one gain across all")

    last = made[-1]
    print(f"  {total_words} words over 84.0 s = {total_words / 84.0 * 60:.0f} wpm; "
          f"last line ends at {last[1] + last[2]:.2f} s")
    over = [m for m in made if m[2] > m[3]]
    if over:
        print(f"  {len(over)} line(s) overrun their slot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
