#!/usr/bin/env python3
"""Mux a silent picture, the approved mix and a subtitle track into the delivered film.

GATE 6 of the education-video skill. The picture arrives silent from
export_html_video.py, the audio is the combined mix the user approved at GATE 3,
and the captions go in as a soft mov_text track whose ENABLED bit is then cleared
in the container — so a player offers them and nobody sees them until they ask.
ffmpeg's own -disposition cannot do that for MP4; this can, in one byte.

    python deliver_film.py --picture silent.mp4 --audio mix.wav \
        --subtitles captions.srt --output film.mp4

Nothing here re-encodes the picture: the video stream is copied and its MD5 is
compared before and after, which is the only proof the mux was lossless. The
subtitle track is extracted back out of the finished file and diffed against the
sidecar, because a track that is present but empty looks identical from outside.

Exits non-zero on: a changed video stream, a missing or empty subtitle track, a
subtitle track flagged default, or a picture/audio duration gap wider than one
frame. Needs ffmpeg and ffprobe on PATH.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


def shown(cmd: list[str]) -> str:
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


def probe(path: Path) -> dict:
    out = run([FFPROBE, "-v", "error", "-show_streams", "-show_format",
               "-of", "json", str(path)])
    if out.returncode:
        raise SystemExit(f"ffprobe failed on {path}:\n{out.stderr.strip()}")
    return json.loads(out.stdout)


def stream(info: dict, kind: str) -> dict | None:
    for s in info.get("streams", []):
        if s.get("codec_type") == kind:
            return s
    return None


def duration(info: dict) -> float:
    d = info.get("format", {}).get("duration")
    if d is not None:
        return float(d)
    for s in info.get("streams", []):
        if s.get("duration"):
            return float(s["duration"])
    raise SystemExit("could not read a duration")


def video_md5(path: Path) -> str:
    """MD5 of the video stream's decoded packets, ignoring the container."""
    out = run([FFMPEG, "-v", "error", "-i", str(path), "-map", "0:v:0",
               "-c", "copy", "-f", "md5", "-"])
    if out.returncode:
        raise SystemExit(f"could not hash the video stream of {path}:\n{out.stderr.strip()}")
    return out.stdout.strip().split("=", 1)[-1]


CUE_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
                    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")


def srt_cues(text: str) -> list[tuple[float, float, str]]:
    """(start, end, collapsed text) per cue. Tolerant of CRLF, BOM and blank runs."""
    cues, lines = [], text.replace("\r\n", "\n").lstrip("\ufeff").split("\n")
    i = 0
    while i < len(lines):
        m = CUE_RE.search(lines[i])
        if not m:
            i += 1
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        i += 1
        body = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i].strip())
            i += 1
        cues.append((start, end, " ".join(body)))
    return cues


def plain(s: str) -> str:
    """Strip the markup mov_text round-trips into, and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>|\{\\[^}]*\}", "", s)).strip()


MP4_CONTAINERS = (b"moov", b"trak", b"mdia")
TKHD_ENABLED = 0x000001
SUBTITLE_HANDLERS = (b"sbtl", b"text", b"subp")


def mp4_children(buf: bytes | bytearray, start: int, end: int):
    """(type, offset, size, header length) for every box directly inside [start, end)."""
    i = start
    while i + 8 <= end:
        size, typ = struct.unpack(">I4s", buf[i:i + 8])
        header = 8
        if size == 1:
            size = struct.unpack(">Q", buf[i + 8:i + 16])[0]
            header = 16
        elif size == 0:
            size = end - i
        if size < header:
            return
        yield typ, i, size, header
        i += size


def mp4_find(buf, start: int, end: int, want: bytes):
    for typ, off, size, header in mp4_children(buf, start, end):
        if typ == want:
            return off, size, header
    return None


def find_subtitle_tkhd(buf) -> int | None:
    """Offset of the tkhd box of the first subtitle track, or None."""
    moov = mp4_find(buf, 0, len(buf), b"moov")
    if not moov:
        return None
    mo, ms, mh = moov
    for typ, off, size, header in mp4_children(buf, mo + mh, mo + ms):
        if typ != b"trak":
            continue
        mdia = mp4_find(buf, off + header, off + size, b"mdia")
        if not mdia:
            continue
        do, ds, dh = mdia
        hdlr = mp4_find(buf, do + dh, do + ds, b"hdlr")
        if not hdlr:
            continue
        ho, _hs, hh = hdlr
        if buf[ho + hh + 8:ho + hh + 12] in SUBTITLE_HANDLERS:
            tkhd = mp4_find(buf, off + header, off + size, b"tkhd")
            if tkhd:
                return tkhd[0]
    return None


def switch_subtitles_off(path: Path) -> str:
    """Clear the subtitle track's ENABLED bit, so a player offers it rather than showing it.

    One byte, inside a fixed-size box: no offset moves and the media data is not touched.
    This is what makes the track switchable; ffmpeg cannot express it for MP4.
    """
    buf = bytearray(path.read_bytes())
    off = find_subtitle_tkhd(buf)
    if off is None:
        return "no subtitle track found in the container"
    flags = int.from_bytes(buf[off + 9:off + 12], "big")
    if not flags & TKHD_ENABLED:
        return ""
    buf[off + 9:off + 12] = (flags & ~TKHD_ENABLED).to_bytes(3, "big")
    path.write_bytes(buf)
    return ""


def loudness(path: Path) -> tuple[float | None, float | None]:
    out = run([FFMPEG, "-v", "info", "-i", str(path), "-map", "0:a:0",
               "-af", "ebur128=peak=true", "-f", "null", "-"])
    integrated = peak = None
    tail = out.stderr[-4000:]
    m = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", tail)
    if m:
        integrated = float(m[-1])
    m = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", tail)
    if m:
        peak = float(m[-1])
    return integrated, peak


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--picture", required=True, help="silent MP4 from export_html_video.py")
    ap.add_argument("--audio", required=True, help="the combined mix approved at GATE 3")
    ap.add_argument("--subtitles", help="sidecar .srt; omit only for a film with no captions")
    ap.add_argument("--output", required=True, help="the delivered MP4")
    ap.add_argument("--language", default="eng", help="ISO 639-2 code for the subtitle track")
    ap.add_argument("--track-title", default="Subtitles", help="name a player shows in its menu")
    ap.add_argument("--audio-bitrate", default="256k")
    ap.add_argument("--fps", type=float, default=30.0, help="only used to price the duration gap")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the ffmpeg command, change nothing")
    args = ap.parse_args()

    if not FFMPEG or not FFPROBE:
        raise SystemExit("ffmpeg and ffprobe must be on PATH")

    picture, audio = Path(args.picture).expanduser(), Path(args.audio).expanduser()
    output = Path(args.output).expanduser()
    subs = Path(args.subtitles).expanduser() if args.subtitles else None
    for p in [picture, audio] + ([subs] if subs else []):
        if not p.is_file():
            raise SystemExit(f"not a file: {p}")
    if output.exists() and not args.overwrite:
        raise SystemExit(f"output exists; pass --overwrite: {output}")

    cmd = [FFMPEG, "-y" if args.overwrite else "-n", "-hide_banner", "-loglevel", "warning",
           "-i", str(picture), "-i", str(audio)]
    if subs:
        cmd += ["-i", str(subs)]
    cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    if subs:
        cmd += ["-map", "2:0"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", args.audio_bitrate]
    if subs:
        # No -disposition here on purpose: ffmpeg's MP4 muxer writes the track's ENABLED bit
        # whatever you pass it, so -disposition:s:0 0 looks like it worked and does nothing.
        # switch_subtitles_off() clears the bit in the container afterwards, which does work.
        cmd += ["-c:s", "mov_text",
                "-metadata:s:s:0", f"language={args.language}",
                "-metadata:s:s:0", f"title={args.track_title}"]
    cmd += ["-movflags", "+faststart", str(output)]

    if args.dry_run:
        print(shown(cmd))
        return 0

    before = video_md5(picture)
    pic_info, aud_info = probe(picture), probe(audio)
    pic_dur, aud_dur = duration(pic_info), duration(aud_info)

    mux = run(cmd)
    if mux.returncode:
        print(mux.stderr.strip(), file=sys.stderr)
        raise SystemExit("the mux failed")

    problems: list[str] = []
    if subs:
        why = switch_subtitles_off(output)
        if why:
            problems.append(f"could not switch the subtitle track off: {why}")
    after = video_md5(output)
    if after != before:
        problems.append(f"the video stream changed: {before} -> {after}; it was not copied")

    out_info = probe(output)
    sub = stream(out_info, "subtitle")
    if subs:
        if sub is None:
            problems.append("no subtitle stream in the delivered file")
        else:
            if sub.get("disposition", {}).get("default"):
                problems.append("the subtitle track is still flagged default; it would come up "
                                "on by itself")
            back = run([FFMPEG, "-v", "error", "-i", str(output), "-map", "0:s:0",
                        "-c:s", "srt", "-f", "srt", "-"])
            if back.returncode:
                problems.append(f"could not read the track back: {back.stderr.strip()[:200]}")
            else:
                want = [(round(a, 2), round(b, 2), plain(t))
                        for a, b, t in srt_cues(subs.read_text(encoding="utf-8", errors="replace"))]
                got = [(round(a, 2), round(b, 2), plain(t)) for a, b, t in srt_cues(back.stdout)]
                if not got:
                    problems.append("the subtitle track is present but carries no cues")
                elif len(want) != len(got):
                    problems.append(f"cue count changed in the mux: {len(want)} in, {len(got)} out")
                else:
                    bad = [i for i, (w, g) in enumerate(zip(want, got), 1)
                           if w[2] != g[2] or abs(w[0] - g[0]) > 0.05 or abs(w[1] - g[1]) > 0.05]
                    if bad:
                        problems.append(f"{len(bad)} cue(s) differ from the sidecar, first at #{bad[0]}")

    gap = aud_dur - pic_dur
    frame = 1.0 / args.fps if args.fps else 0.0
    if abs(gap) > frame:
        problems.append(f"picture and audio differ by {gap * 1000:.0f} ms, wider than one frame "
                        f"({frame * 1000:.0f} ms) — the composition's duration and the master disagree")

    out_dur = duration(out_info)
    integrated, peak = loudness(output)
    v, a = stream(out_info, "video"), stream(out_info, "audio")

    print(f"\ndelivered   {output}")
    if v:
        print(f"picture     {v.get('width')}x{v.get('height')} {v.get('codec_name')} "
              f"{v.get('profile')} {v.get('r_frame_rate')} fps")
    print(f"video md5   {after}  (unchanged by the mux)" if after == before
          else f"video md5   {after}  CHANGED from {before}")
    if a:
        print(f"sound       {a.get('codec_name')} {a.get('sample_rate')} Hz "
              f"{a.get('channels')} ch {int(a.get('bit_rate', 0) or 0) // 1000} kbps")
    if integrated is not None:
        print(f"loudness    {integrated:.2f} LUFS integrated, peak {peak:.2f} dBFS"
              if peak is not None else f"loudness    {integrated:.2f} LUFS integrated")
    if sub:
        d = "off by default" if not sub.get("disposition", {}).get("default") else "DEFAULT ON"
        lang = sub.get("tags", {}).get("language", "?")
        print(f"subtitles   {sub.get('codec_name')} track, {lang}, {d}; sidecar {subs.name}")
    elif subs:
        print("subtitles   MISSING")
    else:
        print("subtitles   none requested")
    print(f"duration    {out_dur:.3f} s delivered; picture {pic_dur:.3f} s, audio {aud_dur:.3f} s, "
          f"gap {gap * 1000:+.0f} ms")

    if problems:
        print("\nFAILED")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nOK — stream copied, durations agree"
          + (", subtitle track present and switchable" if subs else ", no subtitle track asked for"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
