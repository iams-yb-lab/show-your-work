"""Put the finished audio into the finished picture without re-encoding a single frame.

    python education-video/examples/intro/audio/intro_mux.py --audio out/audio/score.wav \
        --out "Temperature Controller Intro 1080p scored.mp4"
    python education-video/examples/intro/audio/intro_mux.py --audio out/audio/score.wav \
        --clip 42.33 81.63 --out out/samples/loop.mp4

`-c:v copy` copies the video stream through, so the picture in the output is bit-for-bit the
picture that was rendered and the audio can be re-cut any number of times for free. That claim
is checked rather than asserted: the MD5 of the video stream is taken from both files and
compared, and a mismatch is an error.

`--clip` is the exception and says so -- an excerpt has to start on an exact second rather than
on the nearest keyframe, so its video *is* re-encoded, at a quality high enough that what is
being judged is the audio.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intro_env import OUT, VIDEO, find_ffmpeg  # noqa: E402


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def video_md5(ffmpeg: str, path: Path) -> str:
    """The hash of the decoded-then-copied video stream alone, so the audio track cannot
    change it."""
    out = run([ffmpeg, "-v", "error", "-i", str(path), "-map", "0:v", "-c", "copy",
               "-f", "md5", "-"]).stdout.strip()
    return out.split("=")[-1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, default=VIDEO)
    ap.add_argument("--audio", type=Path, default=OUT / "audio" / "score.wav")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--bitrate", default="256k", help="AAC bitrate")
    ap.add_argument("--clip", type=float, nargs=2, metavar=("FROM", "TO"),
                    help="seconds; cuts an excerpt and re-encodes the picture to do it")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        sys.exit("ffmpeg not found")
    for p in (args.video, args.audio):
        if not p.exists():
            sys.exit(f"missing {p}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.clip:
        a, b = args.clip
        run([ffmpeg, "-y", "-loglevel", "error",
             "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(args.video),
             "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(args.audio),
             "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20",
             "-preset", "veryfast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", args.bitrate, "-movflags", "+faststart", str(args.out)])
        mb = args.out.stat().st_size / 1e6
        print(f"  wrote {args.out}  {b - a:.2f} s excerpt, {mb:.1f} MB "
              f"(picture re-encoded, which an excerpt needs)")
        return 0

    before = video_md5(ffmpeg, args.video)
    run([ffmpeg, "-y", "-loglevel", "error", "-i", str(args.video), "-i", str(args.audio),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", args.bitrate,
         "-shortest", "-movflags", "+faststart", str(args.out)])
    after = video_md5(ffmpeg, args.out)
    mb = args.out.stat().st_size / 1e6
    print(f"  wrote {args.out}  {mb:.1f} MB, AAC {args.bitrate}")
    print(f"  video stream MD5 {before}")
    if before != after:
        sys.exit(f"  MD5 CHANGED to {after} -- the picture was re-encoded, which it must not be")
    print("  unchanged by the mux, so the picture is the one that was rendered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
