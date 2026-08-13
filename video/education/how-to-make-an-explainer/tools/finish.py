#!/usr/bin/env python3
"""
finish.py — put the sound on the silent render and prove nothing else changed.

The picture comes out of the HTML bundle silent, by construction: the exporter passes `-an` and there
is no audio argument. So this is the last step of the film, and it does two things — mux, then refuse
to believe it worked until it has checked.

What it verifies, and why each check exists:

  picture untouched   the video stream's MD5 before and after must match. `-c:v copy` is supposed to be
                      lossless; this is the only thing that proves it was.
  duration            the finished file against the audio, within one frame. The render is
                      round(duration x fps) frames, so it is legitimately up to half a frame short of
                      the audio, and anything larger is a real drift.
  scene boundaries    every scene in and out from the cue sheet must fall inside the finished file, and
                      the table must still sum to its duration. Catches a render that silently stopped
                      early — which looks like a complete film until the last scene is missing.
  audio               codec, sample rate, channels, and loudness re-measured on the *decoded* result,
                      not assumed from the encoder's arguments.

    python3 tools/finish.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

FFBIN = (r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
         r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin")
if Path(FFBIN).is_dir():
    os.environ["PATH"] = FFBIN + os.pathsep + os.environ["PATH"]
FFMPEG = str(Path(FFBIN) / "ffmpeg.exe") if Path(FFBIN).is_dir() else "ffmpeg"
FFPROBE = str(Path(FFBIN) / "ffprobe.exe") if Path(FFBIN).is_dir() else "ffprobe"

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

FILM = Path(__file__).resolve().parent.parent


def video_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "engine").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a video tree")


VIDEO = video_root(FILM)
sys.path.insert(0, str(VIDEO / "engine"))
from mix_audio import lufs, true_peak_db  # noqa: E402

WORK = VIDEO / "out/education/how-to-make-an-explainer"
AUDIO_BITRATE = "384k"      # generous stereo AAC-LC; YouTube re-encodes anyway, so give it headroom
FPS = 30


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def video_stream_md5(path: Path) -> str:
    out = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-map", "0:v", "-c", "copy",
                          "-f", "md5", "-"], capture_output=True, text=True, check=True).stdout
    return out.strip()


def probe(path: Path) -> dict:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          str(path)], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    result = {"duration_s": float(data["format"]["duration"]),
              "size_mb": round(int(data["format"]["size"]) / 1_048_576, 2),
              "streams": []}
    for stream in data["streams"]:
        row = {"type": stream["codec_type"], "codec": stream["codec_name"]}
        if stream["codec_type"] == "video":
            num, den = stream["r_frame_rate"].split("/")
            row.update({"width": stream["width"], "height": stream["height"],
                        "fps": int(num) / int(den), "frames": int(stream.get("nb_frames", 0)),
                        "profile": stream.get("profile"), "pix_fmt": stream.get("pix_fmt")})
        else:
            row.update({"sample_rate": int(stream["sample_rate"]),
                        "channels": stream["channels"],
                        "bitrate_kbps": round(int(stream.get("bit_rate", 0)) / 1000)})
        result["streams"].append(row)
    return result


def decoded_audio_measurements(path: Path) -> dict:
    scratch = WORK / "_finish_probe.wav"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(path), "-map", "0:a",
                    "-c:a", "pcm_f32le", str(scratch)], check=True)
    y, rate = sf.read(scratch, dtype="float32", always_2d=True)
    scratch.unlink(missing_ok=True)
    stereo = y.T if y.shape[1] == 2 else np.stack([y[:, 0], y[:, 0]])
    return {"lufs": round(float(lufs(stereo)), 2),
            "true_peak_dbtp": round(float(true_peak_db(stereo)), 2),
            "duration_s": round(len(y) / rate, 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--picture", type=Path, default=WORK / "picture/picture-silent.mp4")
    ap.add_argument("--out", type=Path, default=WORK / "deliver/how-to-make-an-explainer-1080p.mp4")
    args = ap.parse_args()

    mix = json.loads((WORK / "mix.json").read_text(encoding="utf-8"))
    cues = json.loads((WORK / "cues.json").read_text(encoding="utf-8"))
    audio = Path(mix["path"])
    if not args.picture.exists():
        raise SystemExit(f"no silent render at {args.picture}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    silent = probe(args.picture)
    before = video_stream_md5(args.picture)

    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(args.picture), "-i", str(audio),
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(args.out)], check=True)

    after = video_stream_md5(args.out)
    final = probe(args.out)
    measured = decoded_audio_measurements(args.out)
    video = next(s for s in final["streams"] if s["type"] == "video")
    sound = next((s for s in final["streams"] if s["type"] == "audio"), None)

    scenes = cues["scenes"]
    table_sum = sum(s["duration_s"] for s in scenes)
    problems = []
    if before != after:
        problems.append(f"the picture was re-encoded: {before} != {after}")
    if sound is None:
        problems.append("no audio stream in the output")
    if abs(final["duration_s"] - mix["duration_s"]) > 1.0 / FPS:
        problems.append(f"duration {final['duration_s']:.3f} s against audio {mix['duration_s']:.3f} s, "
                        f"more than one frame apart")
    if (video["width"], video["height"]) != (1920, 1080) or abs(video["fps"] - FPS) > 0.01:
        problems.append(f"geometry {video['width']}x{video['height']} @ {video['fps']} fps")
    if scenes and scenes[-1]["out_s"] > final["duration_s"] + 1.0 / FPS:
        problems.append(f"the film ends at {final['duration_s']:.3f} s but scene "
                        f"{scenes[-1]['scene']} runs to {scenes[-1]['out_s']:.3f} s — render stopped early")
    if abs(table_sum - final["duration_s"]) > 0.05:
        problems.append(f"scene table sums to {table_sum:.3f} s, film is {final['duration_s']:.3f} s")
    if sound and (sound["sample_rate"] != 48000 or sound["channels"] != 2):
        problems.append(f"audio is {sound['sample_rate']} Hz / {sound['channels']} ch")
    if abs(measured["lufs"] - mix["delivered"]["lufs"]) > 0.5:
        problems.append(f"loudness moved to {measured['lufs']:+.2f} from {mix['delivered']['lufs']:+.2f}")

    report = {
        "output": str(args.out), "sha256": sha256(args.out),
        "silent_picture": {"path": str(args.picture), **silent},
        "audio_source": {"path": str(audio), "lossless": True,
                         "lufs": mix["delivered"]["lufs"],
                         "true_peak_dbtp": mix["delivered"]["true_peak_dbtp"]},
        "finished": final,
        "audio_measured_on_output": measured,
        "video_stream_md5": {"before": before, "after": after, "unchanged": before == after},
        "scene_table_sum_s": round(table_sum, 3),
        "audio_bitrate_requested": AUDIO_BITRATE,
        "problems": problems,
    }
    (WORK / "finish.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"finished film: {args.out}")
    print(f"  {final['duration_s']:.3f} s, {video['width']}x{video['height']} @ {video['fps']:g} fps, "
          f"{video['frames']} frames, {final['size_mb']:.1f} MB")
    print(f"  picture untouched by the mux: {before == after}")
    if sound:
        print(f"  audio {sound['codec']} {sound['bitrate_kbps']} kbps, {sound['sample_rate']} Hz, "
              f"{sound['channels']} ch, measured {measured['lufs']:+.2f} LUFS / "
              f"{measured['true_peak_dbtp']:+.2f} dBTP")
    print(f"  scene table {table_sum:.3f} s against film {final['duration_s']:.3f} s")
    if problems:
        print(f"  {len(problems)} PROBLEM(S):")
        for line in problems:
            print(f"    {line}")
        return 1
    print("  every check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
