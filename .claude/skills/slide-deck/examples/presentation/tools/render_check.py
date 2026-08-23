#!/usr/bin/env python3
"""Rendered checks on the built master, plus slide screenshots for the export.

For every slide: (1) no visible element extends past the 1920x1080 canvas;
(2) no visible text renders below the GATE 0 floor (28px computed); (3) nothing is drawn
on top of anything else — words on words, words on a picture, a picture on a picture;
(4) inside a diagram, no line, curve or block edge crowds a word; and (5) a 1920x1080 PNG
is written for the pixel-faithful PowerPoint export.
Exits non-zero on any violation. Needs the default python (Playwright).

Checks (1) to (4) come from _shared/checks/composition.py, which education-video runs too.
Speaker notes are excluded by `skip=".notes"` as they always were. Elements that are not on
screen are skipped, ancestors included, because an invisible element overflowing is not a
defect anyone sees.

Checks (3) and (4) are the ones that find real defects: (1) and (2) are cheap and almost
never fire, because a layout defect is full-size text inside the canvas. **The PNGs are not
optional.** The checker and a pair of eyes catch different things — look at the pictures.
"""
import os, sys
from pathlib import Path

# The overflow, font-floor, overlap and clearance checks are shared with education-video, in
# _shared/checks/composition.py. This file owns the per-slide loop, the screenshots and the
# link map; it does not own a second opinion on what "too small" or "too close" means.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "_shared" / "checks"))
from composition import FONT_FLOOR, BOX_TOL  # noqa: E402
from composition import problems as composition_problems  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRES = os.path.dirname(HERE)
MASTER = os.path.join(PRES, "how-to-use-the-skills.html")
OUTDIR = os.path.join(PRES, "exports", "slides")
FLOOR = FONT_FLOOR
TOL = BOX_TOL

def main():
    import json
    from playwright.sync_api import sync_playwright
    os.makedirs(OUTDIR, exist_ok=True)
    fails, links = [], {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("file:///" + MASTER.replace(os.sep, "/"))
        page.wait_for_timeout(600)  # fonts
        n = page.evaluate("() => document.querySelectorAll('.slide').length")
        for i in range(n):
            page.evaluate("(i) => show(i)", i)
            page.wait_for_timeout(120)
            probs = composition_problems(page, ".slide.current", TOL, FLOOR,
                                         skip=".notes")
            for msg in probs:
                fails.append("slide %d: %s" % (i + 1, msg))
            page.screenshot(path=os.path.join(OUTDIR, "slide-%02d.png" % (i + 1)))
            rects = page.evaluate("""() =>
                [...document.querySelectorAll('.slide.current a[href]')].map(a => {
                  const r = a.getBoundingClientRect();
                  return {href: a.href, x: r.left, y: r.top, w: r.width, h: r.height};
                })""")
            if rects:
                links[str(i + 1)] = rects
        b.close()
    with open(os.path.join(os.path.dirname(OUTDIR), "links.json"), "w") as f:
        json.dump(links, f, indent=1)
    if fails:
        print("FAIL (%d):" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("OK: %d slides — nothing past the canvas, no computed text below %.0fpx, nothing drawn "
          "on top of anything else, every word clear of the geometry; PNGs in %s.\n"
          "Now look at them: the checks and a pair of eyes catch different things."
          % (n, FLOOR, OUTDIR))
    return 0

if __name__ == "__main__":
    sys.exit(main())
