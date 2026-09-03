#!/usr/bin/env python3
"""Render a checked end card to the form the film needs.

    python render_card.py card.html --png  card.png            # a still
    python render_card.py card.html --mp4  card.mp4            # for an HTML-rendered film
    python render_card.py card.html --frames out/ --start-number 1801   # for a 3D film

Three outputs, because the two video skills assemble a film in two different ways.

  --png     one screenshot of the export root. For a thumbnail, a slide, or a look at the
            card without rendering anything long.

  --mp4     hands the card to education-video/method/export_html_video.py and lets THAT do
            the encode. This is deliberate and it is the whole reason this path exists at
            all: that file holds the only copy of the H.264 profile, the pixel format, the
            colour range and the bt709 metadata the film's picture is encoded with, and the
            card is only useful if it will stream-copy onto the end of that picture without
            re-encoding. A second copy of those flags here would drift, and the failure when
            it drifted would be a concat that silently produced a broken file.

  --frames  numbered PNGs. showoff-render encodes a film from a PNG sequence, so a card
            written as more frames numbered past the last rendered one needs no video work
            at all -- the existing encoder globs and sorts and picks the sequence up.

The card is time-invariant, so every frame of it is the same frame. --mp4 still renders each
one through the exporter rather than looping a still, because the point is that the card comes
out of the same encoder as the picture. --frames copies one screenshot, which is exact and
costs nothing.

Rendering does not check anything. Run check_card.py first.
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
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent          # .../.claude/skills/
EXPORTER = SKILLS / "education-video" / "method" / "export_html_video.py"

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
        p = Path(explicit).expanduser()
        if p.is_file():
            return str(p.resolve())
        raise SystemExit(f"Chrome executable not found: {p}")
    candidates = [
        shutil.which("chrome"), shutil.which("chromium"), shutil.which("google-chrome"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome",
                     "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome",
                     "Application", "chrome.exe"),
        "/usr/bin/google-chrome", "/usr/bin/chromium",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise SystemExit("no Chrome found; pass --chrome")


def shoot(card: Path, width: int, height: int, chrome: str | None) -> tuple[bytes, float]:
    """One screenshot of the export root, and the duration the card declares."""
    with local_server(card.parent) as port:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=find_chrome(chrome),
                args=["--force-device-scale-factor=1", "--hide-scrollbars"])
            page = browser.new_context(viewport={"width": width, "height": height + 140},
                                       device_scale_factor=1).new_page()
            page.goto(f"http://127.0.0.1:{port}/{quote(card.name)}", wait_until="load")
            page.wait_for_function("document.fonts && document.fonts.status === 'loaded'",
                                   timeout=20000)
            page.wait_for_timeout(150)
            root = page.query_selector(EXPORT_SELECTOR)
            if root is None:
                browser.close()
                raise SystemExit(f"no element carries {EXPORT_SELECTOR} in {card.name}")
            duration = float(root.get_attribute(
                "data-om-exportable-video-with-duration-secs") or 0)
            png = root.screenshot(type="png")
            browser.close()
    return png, duration


def render_png(card: Path, out: Path, width: int, height: int, chrome: str | None) -> None:
    png, _ = shoot(card, width, height, chrome)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(png)
    print(f"still: {out}  ({width}x{height})")


def render_frames(card: Path, out_dir: Path, width: int, height: int, fps: int,
                  start: int, chrome: str | None) -> None:
    png, duration = shoot(card, width, height, chrome)
    count = round(duration * fps)
    if count < 1:
        raise SystemExit(f"card declares {duration}s at {fps} fps, which is no frames at all")
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (out_dir / f"card_{start + i:06d}.png").write_bytes(png)
    print(f"frames: {count} identical PNGs in {out_dir}, "
          f"numbered {start:06d}..{start + count - 1:06d} ({duration}s at {fps} fps)")
    print("  they sort after the film's own frames only if `start` is past its last one")


def render_mp4(card: Path, out: Path, width: int, height: int, fps: int,
               chrome: str | None, overwrite: bool) -> None:
    if not EXPORTER.is_file():
        raise SystemExit(
            f"the film exporter is not where it should be: {EXPORTER}\n"
            "  The card's MP4 must come out of the same encoder as the film's picture, so "
            "there is no fallback here on purpose.")
    cmd = [sys.executable, str(EXPORTER), str(card), str(out),
           "--width", str(width), "--height", str(height), "--fps", str(fps)]
    if chrome:
        cmd += ["--chrome", chrome]
    if overwrite:
        cmd.append("--overwrite")
    print(f"handing the card to {EXPORTER.name} so the encode matches the film's picture")
    raise SystemExit(subprocess.call(cmd))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card", type=Path)
    ap.add_argument("--png", type=Path)
    ap.add_argument("--mp4", type=Path)
    ap.add_argument("--frames", type=Path, metavar="DIR")
    ap.add_argument("--start-number", type=int, default=1,
                    help="first frame number for --frames; set it past the film's last frame")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--chrome")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    if not args.card.is_file():
        print(f"error: no such card: {args.card}", file=sys.stderr)
        return 1
    if not (args.png or args.mp4 or args.frames):
        print("error: choose an output: --png, --mp4 or --frames", file=sys.stderr)
        return 1

    card = args.card.resolve()
    if args.png:
        render_png(card, args.png, args.width, args.height, args.chrome)
    if args.frames:
        render_frames(card, args.frames, args.width, args.height, args.fps,
                      args.start_number, args.chrome)
    if args.mp4:
        render_mp4(card, args.mp4, args.width, args.height, args.fps,
                   args.chrome, args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
