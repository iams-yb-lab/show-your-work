#!/usr/bin/env python3
"""Check a built authorship end card before it goes anywhere near a film.

    python check_card.py card.html
    python check_card.py card.html --width 1920 --height 1080 --expect-duration 6

Five checks, in the order they hurt:

  contract     the export root exists, its box is exactly the authored size, and its duration
               attribute is present and positive. Wrong here and the exporter aborts before
               frame 1 -- or worse, renders a card that will not stream-copy onto the film
  offline      nothing is fetched at render time. A card whose logo silently 404s is a card
               with a hole where an institution used to be, and it looks fine in a browser
               that still has the file cached
  composition  overflow, the 28px font floor, overlap and clearance -- the shared check, the
               same one the film and the deck run. This is the authority on whether the
               credits fit; build_card.py only guesses
  structure    the card actually says the things a card exists to say: a disclosure, someone
               answerable, a contact, and no dangling role with nobody in it
  static       two different instants give identical pixels. The card is meant to be
               time-invariant, and a card that animates renders as a smear

This is the third caller of _shared/checks/composition.py, beside the film's
composition_check.py and the deck's render_check.py. The floor is defined once, there, and a
second copy of it would be a second answer to the same question.

Exits non-zero on any finding. Needs Playwright and a system Chrome.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import os
import shutil
import sys
import threading
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "checks"))
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


# The structural rules, asked of the rendered card rather than of the JSON that produced it.
# Checking the artifact is the point: a build that silently dropped the disclosure would pass
# a re-run of its own validation and fail this.
JS_STRUCTURE = r"""
() => {
  const bad = [];
  const text = el => (el ? (el.textContent || '').trim() : '');

  const disc = document.querySelector('.disclosure');
  if (!disc) bad.push('no .disclosure element: every card must say what was generated');
  else if (!text(disc)) bad.push('.disclosure is present but empty');

  if (!text(document.querySelector('.stamp .label')))
    bad.push('the accountability stamp has no label, so it reads as one more credit');
  if (!text(document.querySelector('.stamp .contact')))
    bad.push('no contact route in the footer');

  const plate = document.querySelector('.plate img');
  const wordmark = document.querySelector('.wordmark');
  if (plate && wordmark) bad.push('both a logo and a wordmark: the lockup already carries ' +
                                  'the name, so printing it twice reads as an error');
  if (!plate && !wordmark) bad.push('no identity: neither a logo nor a wordmark');

  // Someone must be named as answerable. The stamp carries the name unless the wordmark on
  // the left is already carrying it, so either one satisfies this -- but not neither.
  if (!text(document.querySelector('.stamp .who')) && !text(wordmark) && !plate)
    bad.push('nobody is named as responsible for this content');

  document.querySelectorAll('.block').forEach((b, i) => {
    if (!text(b.querySelector('.block-label'))) bad.push(`block ${i} has no label`);
    if (!b.querySelectorAll('.row').length) bad.push(`block ${i} has a heading and no rows`);
  });

  document.querySelectorAll('.row').forEach((r, i) => {
    if (!text(r.querySelector('.role'))) bad.push(`row ${i} has names but no role`);
    if (!text(r.querySelector('.names'))) bad.push(`row ${i} has a role but nobody in it`);
  });

  if (!document.querySelectorAll('.row').length) bad.push('the card credits nobody');
  return bad;
}
"""


def check(card: Path, width: int, height: int, expect_duration: float | None,
          chrome: str | None) -> list[str]:
    findings: list[str] = []
    with local_server(card.parent) as port:
        origin = f"http://127.0.0.1:{port}"
        url = f"{origin}/{quote(card.name)}"
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=find_chrome(chrome),
                args=["--force-device-scale-factor=1", "--hide-scrollbars"])
            # The extra height is slack, so the composition is never the thing being clipped.
            page = browser.new_context(viewport={"width": width, "height": height + 140},
                                       device_scale_factor=1).new_page()

            offsite, failed, errors = [], [], []

            # A browser asks for /favicon.ico whether or not the page mentions one; that 404
            # is the browser's, not the card's, and reporting it trains people to ignore this
            # check. The film's composition_check.py draws the same line, for the same reason.
            def interesting(url: str) -> bool:
                return not url.endswith("/favicon.ico")

            page.on("request", lambda r: (
                offsite.append(r.url) if interesting(r.url) and not r.url.startswith(
                    (origin, "data:", "blob:", "about:")) else None))
            page.on("response", lambda r: (
                failed.append(f"{r.url} -> HTTP {r.status}")
                if r.status >= 400 and interesting(r.url) else None))
            page.on("pageerror", lambda e: errors.append(str(e)))
            # "Failed to load resource" is the console's copy of a bad response, without the
            # URL. The response handler above has the URL, so keep that one and drop the copy.
            page.on("console", lambda m: (
                errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" and not m.text.startswith("Failed to load resource")
                else None))

            page.goto(url, wait_until="load")
            page.wait_for_function("document.fonts && document.fonts.status === 'loaded'",
                                   timeout=20000)
            page.wait_for_timeout(150)

            root = page.query_selector(EXPORT_SELECTOR)
            if root is None:
                browser.close()
                return [f"no element carries {EXPORT_SELECTOR}: the exporter cannot start"]

            box = root.bounding_box() or {}
            if abs(box.get("width", 0) - width) > BOX_TOL or \
               abs(box.get("height", 0) - height) > BOX_TOL:
                findings.append(f"card renders at {box.get('width')}x{box.get('height')}, "
                                f"authored {width}x{height}")

            raw = root.get_attribute("data-om-exportable-video-with-duration-secs")
            try:
                duration = float(raw)
            except (TypeError, ValueError):
                duration = -1.0
            if duration <= 0:
                findings.append(f"duration attribute is {raw!r}; it must be a positive number")
            elif expect_duration is not None and abs(duration - expect_duration) > 0.01:
                findings.append(f"card duration {duration}s, expected {expect_duration}s")

            findings += [f"structure: {b}" for b in page.evaluate(JS_STRUCTURE)]
            findings += [f"composition: {p}" for p in
                         composition_problems(page, EXPORT_SELECTOR, BOX_TOL, FONT_FLOOR)]

            # Time-invariance. The card is static by design, so any two instants must agree.
            shots = []
            for t in (0.0, max(duration, 0.1) / 2):
                page.evaluate(
                    "(t) => document.querySelector('%s').dispatchEvent("
                    "new CustomEvent('data-om-seek-to-time-frame', {detail:{time:t}}))"
                    % EXPORT_SELECTOR, t)
                page.wait_for_timeout(60)
                shots.append(root.screenshot(type="png"))
            if shots[0] != shots[1]:
                findings.append("static: two instants render differently. This card is meant "
                                "to be time-invariant; something in it is animating")

            browser.close()

    findings += [f"offline: fetched {u}" for u in dict.fromkeys(offsite)]
    findings += [f"offline: {f}" for f in dict.fromkeys(failed)]
    findings += [f"error: {e}" for e in dict.fromkeys(errors)]
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card", type=Path)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--expect-duration", type=float)
    ap.add_argument("--chrome")
    args = ap.parse_args()

    if not args.card.is_file():
        print(f"error: no such card: {args.card}", file=sys.stderr)
        return 1

    findings = check(args.card.resolve(), args.width, args.height,
                     args.expect_duration, args.chrome)
    if findings:
        print(f"{len(findings)} finding(s) in {args.card.name}:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"{args.card.name}: clean at {args.width}x{args.height} "
          f"(contract, offline, composition, structure, static)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
