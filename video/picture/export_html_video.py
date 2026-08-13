#!/usr/bin/env python3
"""Render an Omelette-style bundled HTML animation to a 4K MP4.

Requirements: Python Playwright, Google Chrome/Chromium, and ffmpeg.
The HTML is served only on 127.0.0.1. Frames are sought deterministically
through the bundle's data-om-seek-to-time-frame protocol and streamed directly
to ffmpeg, so no frame directory is required.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


EXPORT_SELECTOR = "[data-om-exportable-video-with-duration-secs]"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


@contextlib.contextmanager
def local_server(directory: Path):
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def find_chrome(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"Chrome executable not found: {path}")

    candidates = [
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("google-chrome"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise FileNotFoundError("Google Chrome/Chromium was not found; pass --chrome PATH")


def ffmpeg_encoder_args(codec: str, quality: int) -> list[str]:
    if codec == "h264_nvenc":
        return [
            "-c:v", "h264_nvenc",
            "-preset", "p6",
            "-tune", "hq",
            "-rc", "vbr",
            "-cq", str(quality),
            "-b:v", "0",
            "-spatial-aq", "1",
            "-temporal-aq", "1",
            "-profile:v", "high",
        ]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", str(quality), "-profile:v", "high"]


def nvenc_works(ffmpeg: str) -> bool:
    probe = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=size=16x16:duration=0.04",
            "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return probe.returncode == 0


def render(args: argparse.Namespace) -> None:
    html = Path(args.html).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not html.is_file():
        raise FileNotFoundError(html)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists; pass --overwrite: {output}")

    chrome = find_chrome(args.chrome)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg was not found on PATH")
    codec = args.codec
    if codec == "auto":
        codec = "h264_nvenc" if nvenc_works(ffmpeg) else "libx264"
        print(f"Encoder: {codec}", flush=True)
    elif codec == "h264_nvenc" and not nvenc_works(ffmpeg):
        raise RuntimeError("h264_nvenc is unavailable with this ffmpeg build and NVIDIA driver")
    output.parent.mkdir(parents=True, exist_ok=True)

    with local_server(html.parent) as port, sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=chrome,
            headless=True,
            args=[
                "--enable-gpu",
                "--disable-software-rasterizer",
                "--force-device-scale-factor=1",
                "--hide-scrollbars",
            ],
        )
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height + 140},
            device_scale_factor=1,
        )
        page = context.new_page()
        url = f"http://127.0.0.1:{port}/{quote(html.name)}"
        page.goto(url, wait_until="load", timeout=60_000)
        root = page.locator(EXPORT_SELECTOR).first
        root.wait_for(state="attached", timeout=60_000)
        page.evaluate(
            """async () => {
                if (document.fonts?.ready) await document.fonts.ready;
                await Promise.all([...document.images].map(img => img.complete
                    ? Promise.resolve()
                    : new Promise(resolve => {
                        img.addEventListener('load', resolve, {once:true});
                        img.addEventListener('error', resolve, {once:true});
                    })));
            }"""
        )

        box = root.bounding_box()
        if not box:
            raise RuntimeError("Exportable composition has no visible bounding box")
        actual = (round(box["width"]), round(box["height"]))
        requested = (args.width, args.height)
        if actual != requested:
            raise RuntimeError(f"Composition rendered at {actual}, expected {requested}")

        duration = float(root.get_attribute("data-om-exportable-video-with-duration-secs") or "0")
        if duration <= 0:
            raise RuntimeError("Animation duration is missing or invalid")
        total_frames = round(duration * args.fps)
        if args.frames is not None:
            total_frames = min(total_frames, args.frames)

        command = [
            ffmpeg,
            "-y" if args.overwrite else "-n",
            "-hide_banner",
            "-loglevel", "warning",
            "-f", "image2pipe",
            "-framerate", str(args.fps),
            "-vcodec", "mjpeg",
            "-i", "-",
            "-an",
            "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p",
            *ffmpeg_encoder_args(codec, args.quality),
            "-pix_fmt", "yuv420p",
            "-color_range", "tv",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-movflags", "+faststart",
            str(output),
        ]
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        if encoder.stdin is None:
            raise RuntimeError("Could not open ffmpeg input pipe")

        started = time.monotonic()
        try:
            for frame in range(total_frames):
                timestamp = frame / args.fps
                page.evaluate(
                    """([selector, time]) => {
                        const el = document.querySelector(selector);
                        el.dispatchEvent(new CustomEvent('data-om-seek-to-time-frame', {
                            detail: {time}
                        }));
                    }""",
                    [EXPORT_SELECTOR, timestamp],
                )
                jpeg = page.screenshot(
                    type="jpeg",
                    quality=args.jpeg_quality,
                    clip={
                        "x": box["x"],
                        "y": box["y"],
                        "width": args.width,
                        "height": args.height,
                    },
                )
                encoder.stdin.write(jpeg)
                if frame == 0 or (frame + 1) % args.progress_every == 0 or frame + 1 == total_frames:
                    elapsed = time.monotonic() - started
                    rate = (frame + 1) / elapsed
                    remaining = (total_frames - frame - 1) / rate if rate else 0
                    print(
                        f"{frame + 1}/{total_frames} ({(frame + 1) / total_frames:6.2%})  "
                        f"{rate:4.2f} fps  ETA {remaining / 60:5.1f} min",
                        flush=True,
                    )
        finally:
            with contextlib.suppress(BrokenPipeError, OSError):
                encoder.stdin.close()
            return_code = encoder.wait()
            context.close()
            browser.close()

        if return_code:
            raise RuntimeError(f"ffmpeg exited with status {return_code}")

        elapsed = time.monotonic() - started
        print(f"Wrote {output} ({args.width}x{args.height}, {args.fps} fps) in {elapsed / 60:.1f} min")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", help="Bundled HTML animation")
    parser.add_argument("output", help="Output MP4")
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--codec", choices=("auto", "h264_nvenc", "libx264"), default="auto")
    parser.add_argument("--quality", type=int, default=18, help="NVENC CQ or x264 CRF")
    parser.add_argument("--jpeg-quality", type=int, default=95, choices=range(1, 101))
    parser.add_argument("--frames", type=int, help="Render only the first N frames (for testing)")
    parser.add_argument("--progress-every", type=int, default=300)
    parser.add_argument("--chrome", help="Path to Chrome/Chromium")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        render(parse_args())
    except (FileNotFoundError, FileExistsError, RuntimeError, PlaywrightError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
