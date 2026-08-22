"""Encode a PNG frame sequence to an H.264 MP4, using Blender's own bundled FFmpeg.

Frames are rendered as PNGs rather than straight to video because a 600-frame run that
dies at frame 500 should not lose the first 499. This turns them into the one file that
drops into PowerPoint.

    blender --background --factory-startup --python tools/encode_frames.py -- \
        --frames out/anim/purple --out out/anim/purple.mp4 --fps 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def strips_of(editor):
    """Blender 4.5 renamed Sequence -> Strip and `sequences` -> `strips`."""
    return getattr(editor, "strips", None) or editor.sequences


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=Path, required=True, help="directory of PNG frames")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", default="HIGH", help="PERC_LOSSLESS, HIGH, MEDIUM, ...")
    args = ap.parse_args(argv)

    frames = sorted(args.frames.glob("*.png"))
    if not frames:
        return print(f"no PNGs in {args.frames}") or 1

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = args.fps
    scene.frame_start = 1
    scene.frame_end = len(frames)

    img = bpy.data.images.load(str(frames[0].resolve()))
    scene.render.resolution_x, scene.render.resolution_y = img.size
    scene.render.resolution_percentage = 100
    bpy.data.images.remove(img)

    scene.sequence_editor_create()
    strip = strips_of(scene.sequence_editor).new_image(
        name="frames", filepath=str(frames[0].resolve()), channel=1, frame_start=1)
    for f in frames[1:]:
        strip.elements.append(f.name)

    scene.render.image_settings.file_format = "FFMPEG"
    ff = scene.render.ffmpeg
    ff.format = "MPEG4"
    ff.codec = "H264"
    ff.constant_rate_factor = args.crf
    ff.ffmpeg_preset = "GOOD"
    ff.gopsize = args.fps          # a keyframe every second: scrubbable in a slide deck
    ff.audio_codec = "NONE"
    # Rendering the sequencer means the frames are already display-referred; a second view
    # transform would double-apply the tone map and wash the whole video out.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.filepath = str(args.out.resolve())
    scene.render.use_file_extension = False

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(animation=True)
    size = args.out.stat().st_size / 1e6 if args.out.exists() else 0.0
    print(f"  {args.out.name}: {len(frames)} frames, {scene.render.resolution_x}x"
          f"{scene.render.resolution_y}, {args.fps} fps, {size:.1f} MB")
    return 0 if size else 1


if __name__ == "__main__":
    raise SystemExit(main())
