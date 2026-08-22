#!/usr/bin/env python3
"""Rendered checks on the built master, plus slide screenshots for the export.

For every slide: (1) no visible element extends past the 1920x1080 canvas;
(2) no visible text renders below the GATE 0 floor (28px computed);
(3) a 1920x1080 PNG is written for the pixel-faithful PowerPoint export.
Exits non-zero on any violation. Needs the default python (Playwright).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRES = os.path.dirname(HERE)
MASTER = os.path.join(PRES, "how-to-use-the-skills.html")
OUTDIR = os.path.join(PRES, "exports", "slides")
FLOOR = 28.0
TOL = 1.0  # px

JS_CHECK = """
() => {
  const slide = document.querySelector('.slide.current');
  const problems = [];
  const sr = slide.getBoundingClientRect();
  for (const el of slide.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (el.closest('.notes')) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.left < sr.left - %(tol)f || r.right > sr.right + %(tol)f ||
        r.top < sr.top - %(tol)f || r.bottom > sr.bottom + %(tol)f) {
      problems.push('overflow: <' + el.tagName.toLowerCase() +
        (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '') +
        '> ' + JSON.stringify({l: Math.round(r.left - sr.left), r: Math.round(r.right - sr.left),
                               t: Math.round(r.top - sr.top), b: Math.round(r.bottom - sr.top)}));
    }
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText) {
      const fs = parseFloat(cs.fontSize);
      if (fs < %(floor)f - 0.01) {
        problems.push('font ' + fs.toFixed(1) + 'px in <' + el.tagName.toLowerCase() + '> "' +
                      el.textContent.trim().slice(0, 40) + '"');
      }
    }
  }
  return problems;
}
""" % {"tol": TOL, "floor": FLOOR}

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
            probs = page.evaluate(JS_CHECK)
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
    print("OK: %d slides — no overflow past the canvas, no computed text below %.0fpx; PNGs in %s"
          % (n, FLOOR, OUTDIR))
    return 0

if __name__ == "__main__":
    sys.exit(main())
