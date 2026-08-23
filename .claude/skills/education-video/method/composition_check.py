#!/usr/bin/env python3
"""Check an authored HTML composition before anything long is rendered.

GATE 5 of the education-video skill. The composition is a page that answers a
seek with the frame at that instant; export_html_video.py then steps it frame by
frame. This checks that the page keeps its side of that contract, and that it
looks right at every instant it is asked about — not just at t=0.

    python composition_check.py film.html --width 1920 --height 1080 \
        --expect-duration 270.349 --contact-sheet out/

Seven checks, in the order they hurt:

  contract     the export root exists, its box is exactly the authored size, and
               its duration attribute is present and matches the locked master
  offline      nothing is fetched at render time from anywhere but the local
               server: one missing asset is one blank region in the film
  determinism  seek away and back, and the same instant gives the same pixels.
               A composition that animates itself renders as a smear and looks
               perfect in a browser
  overflow     no visible element extends past the canvas, at any sampled instant
  font floor   no visible text renders below the floor the film agreed
  overlap      nothing is drawn on top of anything else — words on words, words
               on a picture, a picture on a picture — and inside a drawing no
               line, curve or block edge crowds a word. This is the one that
               catches the defect a viewer sees first and the source hides
  errors       no page error or failed console assertion while seeking

A finding that holds at every sampled instant is reported once, at the first
instant it appears, with a count of the later ones. A composition caught
mid-transition can legitimately have two beats crossing; mark a layer that is
meant to sit on another with `class="no-collide"` rather than reaching for a
switch that turns the check off.

Then it writes a contact sheet — a grid, never a single frame, because a lone
frame can land between one beat clearing and the next building and read as a
broken scene.

Exits non-zero on any violation. Needs Playwright and a system Chrome; ffmpeg is
used only to tile the contact sheet, and the sheet degrades to loose PNGs
without it.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

# The two rendered checks live in _shared/checks/composition.py: they are the same two the
# slide deck's render_check.py runs, and a second copy of a font floor is a second answer.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared" / "checks"))
from composition import BOX_TOL, FONT_FLOOR  # noqa: E402
from composition import problems as composition_problems  # noqa: E402

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
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        "/usr/bin/google-chrome", "/usr/bin/chromium",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return str(Path(c).resolve())
    raise SystemExit("Google Chrome/Chromium was not found; pass --chrome PATH")


SEEK = """
([selector, time]) => {
  const el = document.querySelector(selector);
  el.dispatchEvent(new CustomEvent('data-om-seek-to-time-frame', {detail: {time}}));
}
"""


def tile(pngs: list[Path], out: Path, columns: int) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not pngs:
        return False
    rows = (len(pngs) + columns - 1) // columns
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.name}'\n" for p in pngs), encoding="utf-8")
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", str(listing),
           "-vf", f"scale=480:-1,tile={columns}x{rows}:padding=6:color=0x202020",
           "-frames:v", "1", str(out)]
    ok = subprocess.run(cmd, capture_output=True, text=True, cwd=str(out.parent)).returncode == 0
    listing.unlink(missing_ok=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--expect-duration", type=float,
                    help="the locked master's duration; the page must agree with it")
    ap.add_argument("--duration-tolerance", type=float, default=0.01)
    ap.add_argument("--font-floor", type=float, default=FONT_FLOOR,
                    help="smallest text the film allows, in px on the authored canvas")
    ap.add_argument("--samples", type=int, default=24,
                    help="instants to check the DOM and the pixels at")
    ap.add_argument("--scene-table", help="JSON list of {title,start,duration}; must sum to the page")
    ap.add_argument("--contact-sheet", help="directory to write the sheet and its frames into")
    ap.add_argument("--sheet-columns", type=int, default=4)
    ap.add_argument("--chrome")
    args = ap.parse_args()

    html = Path(args.html).expanduser().resolve()
    if not html.is_file():
        raise SystemExit(f"not a file: {html}")
    chrome = find_chrome(args.chrome)

    problems: list[str] = []
    offsite: list[str] = []
    missing: list[str] = []
    page_errors: list[str] = []
    duration = 0.0

    with local_server(html.parent) as port, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
                                     args=["--force-device-scale-factor=1", "--hide-scrollbars"])
        context = browser.new_context(viewport={"width": args.width, "height": args.height + 140},
                                      device_scale_factor=1)
        page = context.new_page()
        # A browser asks for /favicon.ico whether or not the page mentions one; that 404 is
        # the browser's, not the composition's, and reporting it trains people to ignore this.
        def interesting(url: str) -> bool:
            return not url.endswith("/favicon.ico")

        page.on("pageerror", lambda e: page_errors.append(str(e)))
        # "Failed to load resource" is the console's copy of a bad response, without the URL.
        # The response handler below has the URL, so drop the copy and keep the useful one.
        page.on("console", lambda m: page_errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
        page.on("response", lambda r: missing.append(f"{r.url} -> HTTP {r.status}")
                if r.status >= 400 and interesting(r.url) else None)
        page.on("request", lambda r: offsite.append(r.url)
                if interesting(r.url) and not r.url.startswith(
                    (f"http://127.0.0.1:{port}", "data:", "blob:", "about:")) else None)

        page.goto(f"http://127.0.0.1:{port}/{quote(html.name)}", wait_until="load", timeout=60_000)
        root = page.locator(EXPORT_SELECTOR).first
        try:
            root.wait_for(state="attached", timeout=15_000)
        except Exception:
            print(f"FAILED\n  - no element carries {EXPORT_SELECTOR}; the exporter cannot start")
            browser.close()
            return 1
        page.evaluate("async () => { if (document.fonts?.ready) await document.fonts.ready; }")

        box = root.bounding_box()
        if not box:
            problems.append("the export root has no visible bounding box")
        else:
            actual = (round(box["width"]), round(box["height"]))
            if abs(box["width"] - args.width) > BOX_TOL or abs(box["height"] - args.height) > BOX_TOL:
                problems.append(f"the composition renders at {actual[0]}x{actual[1]}, authored as "
                                f"{args.width}x{args.height}; the render aborts on this")

        raw = root.get_attribute("data-om-exportable-video-with-duration-secs")
        try:
            duration = float(raw or "0")
        except ValueError:
            duration = 0.0
        if duration <= 0:
            problems.append(f"the duration attribute is missing or unreadable ({raw!r})")
        elif args.expect_duration and abs(duration - args.expect_duration) > args.duration_tolerance:
            problems.append(f"the page says {duration:.3f} s, the master is "
                            f"{args.expect_duration:.3f} s — the picture would be cut to a guess")

        if args.scene_table:
            scenes = json.loads(Path(args.scene_table).expanduser().read_text(encoding="utf-8"))
            total = sum(float(s["duration"]) for s in scenes)
            if duration and abs(total - duration) > 0.05:
                problems.append(f"the scene table sums to {total:.3f} s, the page says "
                                f"{duration:.3f} s")

        # Sample instants across the film, plus the two edges.
        end = max(duration - 1.0 / args.fps, 0.0) if duration else 0.0
        n = max(args.samples, 2)
        times = [round(i * end / (n - 1), 3) for i in range(n)]

        sheet_dir = Path(args.contact_sheet).expanduser() if args.contact_sheet else None
        if sheet_dir:
            sheet_dir.mkdir(parents=True, exist_ok=True)
        clip = {"x": box["x"], "y": box["y"], "width": args.width, "height": args.height} if box else None
        frames: list[Path] = []
        shots: dict[float, str] = {}

        # A defect that is on screen for a whole scene is found at every instant that
        # scene covers. Reporting it once, where it starts, keeps one bad label from
        # filling the report and hiding the other nine.
        first_seen: dict[str, list[float]] = {}

        for t in times:
            page.evaluate(SEEK, [EXPORT_SELECTOR, t])
            for f in composition_problems(page, EXPORT_SELECTOR, BOX_TOL, args.font_floor):
                first_seen.setdefault(f, []).append(t)
            png = page.screenshot(type="png", clip=clip)
            shots[t] = hashlib.md5(png).hexdigest()
            if sheet_dir:
                out = sheet_dir / f"t{t:09.3f}.png"
                out.write_bytes(png)
                frames.append(out)

        for f, seen_at in first_seen.items():
            more = f" and {len(seen_at) - 1} later instant(s)" if len(seen_at) > 1 else ""
            problems.append(f"t={seen_at[0]:.3f}s{more}  {f}")

        # Determinism: return to each instant out of order and demand the same pixels.
        for t in reversed(times):
            page.evaluate(SEEK, [EXPORT_SELECTOR, t])
            again = hashlib.md5(page.screenshot(type="png", clip=clip)).hexdigest()
            if again != shots[t]:
                problems.append(f"t={t:.3f}s is not deterministic — seeking back gives different "
                                f"pixels; the composition is animating itself, and it will smear")

        browser.close()

    if offsite:
        for url in sorted(set(offsite))[:6]:
            problems.append(f"fetched at render time: {url}")
    for m in sorted(set(missing))[:6]:
        problems.append(f"the page asked for something that is not there: {m}")
    for e in page_errors[:6]:
        problems.append(f"page error: {e[:160]}")

    sheet = None
    if args.contact_sheet:
        sheet_dir = Path(args.contact_sheet).expanduser()
        candidate = sheet_dir / "contact-sheet.png"
        if tile(sorted(sheet_dir.glob("t*.png")), candidate, args.sheet_columns):
            sheet = candidate

    print(f"\ncomposition  {html}")
    print(f"canvas       {args.width}x{args.height}, font floor {args.font_floor:.0f}px")
    print(f"duration     {duration:.3f} s on the page"
          + (f", master {args.expect_duration:.3f} s" if args.expect_duration else ""))
    print(f"sampled      {len(shots)} instants, each checked twice for determinism")
    if args.contact_sheet:
        print(f"contact      {sheet if sheet else Path(args.contact_sheet).expanduser()}"
              + ("" if sheet else "  (loose frames; ffmpeg not on PATH to tile them)"))

    if problems:
        print("\nFAILED")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return 1
    print("\nOK — contract kept, self-contained, deterministic, nothing overflowing, too small "
          "or drawn on top of anything else")
    return 0


if __name__ == "__main__":
    sys.exit(main())
