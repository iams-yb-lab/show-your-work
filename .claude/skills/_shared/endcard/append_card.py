#!/usr/bin/env python3
"""Put the end card on the end of the film's picture, without re-encoding either.

    python append_card.py --picture picture.mp4 --card card.mp4 --out picture+card.mp4
    python append_card.py --picture picture.mp4 --card card.mp4 --out picture+card.mp4 \
        --mix mix.wav --mix-out mix+tail.wav

This runs BEFORE the film's mux, not after. It produces a new silent picture, which then goes
to deliver_film.py as `--picture` exactly as the old one did. The video stream is copied, so
the picture the user approved is bit-identical inside the longer file -- and this script proves
that by hashing the original picture's stream before and after.

The compatibility check is the reason this exists rather than a one-line ffmpeg call. A
stream-copy concat of two clips that disagree about resolution, frame rate, pixel format or
colour metadata does not fail: it produces a file that plays, and then goes wrong somewhere in
the middle for some viewers. So every one of those is compared first and a mismatch stops here.

About the audio. deliver_film.py refuses a picture and an audio track that differ by more than
one frame, so a card that adds six seconds of picture needs six seconds of audio to go with it.
There are two honest ways to get them and this script only does the second:

  Preferred -- the mix is rendered that much longer at the gate where it is approved, so the
  music tail runs out underneath the card. The card's length has to be known then, which is
  why it belongs in the interview rather than at the end.

  Fallback -- `--mix` pads the approved mix with digital silence. Use it when the mix is
  already locked and reopening it costs more than the silence does. The film simply goes quiet
  under the card. It is not the same thing and this script will say so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# The stream properties that must agree for a concat to be safe. Frame rate is compared as an
# exact rational, because 30 and 30000/1001 both print as "30" once rounded.
MUST_MATCH = ["width", "height", "codec_name", "profile", "pix_fmt",
              "color_range", "color_primaries", "color_transfer", "color_space",
              "r_frame_rate", "sample_aspect_ratio"]


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise SystemExit(f"{tool} is not on PATH; it is needed to join the card to the picture")
    return path


def probe(path: Path) -> dict:
    out = subprocess.run(
        [need("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    if not data.get("streams"):
        raise SystemExit(f"no video stream in {path}")
    s = dict(data["streams"][0])
    s["_duration"] = float(data["format"]["duration"])
    return s


def video_md5(path: Path, frames: int | None = None) -> str:
    """MD5 of the decoded video stream, optionally of only its first `frames` frames.

    Counting frames is what makes this a real check. The obvious alternative -- copy the first
    N seconds back out of the joined file and hash that -- does not work: a stream copy can
    only cut on a keyframe, so the trimmed file holds a different set of frames and the hashes
    disagree on a join that was in fact perfect.
    """
    cmd = [need("ffmpeg"), "-v", "error", "-i", str(path), "-map", "0:v:0"]
    if frames is not None:
        cmd += ["-frames:v", str(frames)]
    out = subprocess.run(cmd + ["-f", "md5", "-"],
                         capture_output=True, text=True, check=True).stdout
    return out.strip().split("=")[-1]


def frame_count(path: Path) -> int:
    """How many frames the video stream holds, counting them only if the container lied."""
    for args in (["-show_entries", "stream=nb_frames"],
                 ["-count_frames", "-show_entries", "stream=nb_read_frames"]):
        out = subprocess.run(
            [need("ffprobe"), "-v", "error", "-select_streams", "v:0"] + args
            + ["-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True).stdout.strip()
        if out.isdigit() and int(out) > 0:
            return int(out)
    raise SystemExit(f"could not determine how many frames are in {path}")


def compare(picture: dict, card: dict) -> list[str]:
    bad = []
    for key in MUST_MATCH:
        a, b = picture.get(key), card.get(key)
        if a != b:
            bad.append(f"  {key:22} picture={a!r}  card={b!r}")
    return bad


def concat(picture: Path, card: Path, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        listing = Path(tmp) / "concat.txt"
        listing.write_text(
            "".join(f"file '{p.resolve().as_posix()}'\n" for p in (picture, card)),
            encoding="utf-8")
        subprocess.run(
            [need("ffmpeg"), "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)],
            check=True)


def pad_audio(mix: Path, out: Path, seconds: float) -> float:
    subprocess.run(
        [need("ffmpeg"), "-v", "error", "-y", "-i", str(mix),
         "-af", f"apad=pad_dur={seconds}", "-c:a", "pcm_s24le", str(out)], check=True)
    return float(subprocess.run(
        [need("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(out)],
        capture_output=True, text=True, check=True).stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--picture", type=Path, required=True, help="the film's silent picture")
    ap.add_argument("--card", type=Path, required=True, help="the rendered end card")
    ap.add_argument("--out", type=Path, required=True, help="picture + card, still silent")
    ap.add_argument("--mix", type=Path, help="the approved mix, to pad with silence")
    ap.add_argument("--mix-out", type=Path, help="where the padded mix goes")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    for p in (args.picture, args.card):
        if not p.is_file():
            print(f"error: no such file: {p}", file=sys.stderr)
            return 1
    if args.out.exists() and not args.overwrite:
        print(f"error: {args.out} exists; pass --overwrite", file=sys.stderr)
        return 1
    if bool(args.mix) != bool(args.mix_out):
        print("error: --mix and --mix-out go together", file=sys.stderr)
        return 1

    pic, card = probe(args.picture), probe(args.card)
    if bad := compare(pic, card):
        print("error: the card and the picture cannot be joined without re-encoding.\n"
              "  These differ, and a stream copy would produce a file that plays and is "
              "wrong:", file=sys.stderr)
        print("\n".join(bad), file=sys.stderr)
        print("\n  Render the card through render_card.py --mp4, which hands it to the same\n"
              "  exporter the picture came from, at the picture's width, height and fps.",
              file=sys.stderr)
        return 1

    pic_frames, card_frames = frame_count(args.picture), frame_count(args.card)
    before = video_md5(args.picture)
    concat(args.picture, args.card, args.out)
    joined = probe(args.out)
    joined_frames = frame_count(args.out)

    print(f"picture  {pic['_duration']:.3f}s  {pic_frames} frames")
    print(f"card    +{card['_duration']:.3f}s  {card_frames} frames")
    print(f"joined   {joined['_duration']:.3f}s  {joined_frames} frames  ->  {args.out}")
    if joined_frames != pic_frames + card_frames:
        print(f"WARNING: {pic_frames} + {card_frames} = {pic_frames + card_frames} frames "
              f"went in and {joined_frames} came out", file=sys.stderr)
        return 1

    # The joined file is longer, so its whole-stream hash cannot equal the original's. Hash
    # only as many frames as the picture had: if it survived the copy untouched, they agree.
    after = video_md5(args.out, frames=pic_frames)
    if before == after:
        print(f"video stream unchanged by the join (md5 {before}, first "
              f"{pic_frames} frames)")
    else:
        print(f"WARNING: the picture's video stream changed in the join\n"
              f"  before {before}\n  after  {after}\n"
              f"  Do not ship this. The picture was re-encoded, which is what the copy was "
              f"meant to prevent.", file=sys.stderr)
        return 1

    if args.mix:
        if not args.mix.is_file():
            print(f"error: no such mix: {args.mix}", file=sys.stderr)
            return 1
        new = pad_audio(args.mix, args.mix_out, card["_duration"])
        print(f"mix     +{card['_duration']:.3f}s of DIGITAL SILENCE  ->  {args.mix_out} "
              f"({new:.3f}s)")
        print("  the film goes quiet under the card. If the music was meant to run out under "
              "it,\n  that has to come from the mix, and this is not it.")
    else:
        print(f"\nthe mix still needs {card['_duration']:.3f}s more, or deliver_film.py will "
              f"refuse\n  the picture and the audio for differing by more than one frame.")

    print(f"\nnext: deliver_film.py --picture {args.out.name} --audio <the longer mix> "
          f"--subtitles <srt>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
