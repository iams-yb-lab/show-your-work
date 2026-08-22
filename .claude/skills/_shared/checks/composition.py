#!/usr/bin/env python3
"""The two rendered checks that every authored composition has to pass, in one place.

  1. nothing visible extends past the canvas
  2. no visible text renders below the font floor

Both are measured in a real browser on the computed style, because both failures are
invisible in the source. A heading that fits at the author's zoom overflows at 1920x1080;
a font size that reads fine on a laptop is unreadable in a projected room. Only the
renderer knows.

These were written twice — once for this repository's own slide deck, once for the
explainer films' HTML compositions — with the floor spelled 28.0 in both files. A
measurement with two implementations has two answers, and the bench here is a person's
eyes, which will not catch the disagreement. So: one copy, two callers.

    slide-deck/examples/presentation/tools/render_check.py   per slide, plus screenshots
    education-video/method/composition_check.py              per instant, plus determinism,
                                                             offline behaviour and a contact sheet

The caller owns the browser and the page; this module owns the question. `skip` exists
because a deck carries speaker notes in the DOM that are not part of the picture.
"""

from __future__ import annotations

# GATE 0 of slide-deck sets the floor and education-video inherits it. Computed px, not
# authored: a 28px rule authored inside a transformed parent is not 28px on screen.
FONT_FLOOR = 28.0
BOX_TOL = 1.0     # px of slack on the canvas edge, for subpixel layout rounding

JS_CHECK = """
([selector, tol, floor, skip]) => {
  const root = document.querySelector(selector);
  if (!root) return ['the canvas ' + selector + ' is not in the page'];
  const problems = [];
  const sr = root.getBoundingClientRect();
  for (const el of root.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (parseFloat(cs.opacity) === 0) continue;
    if (skip && el.closest(skip)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const tag = el.tagName.toLowerCase() +
      (el.className && typeof el.className === 'string' && el.className.trim()
        ? '.' + el.className.trim().split(/\\s+/)[0] : '');
    if (r.left < sr.left - tol || r.right > sr.right + tol ||
        r.top < sr.top - tol || r.bottom > sr.bottom + tol) {
      problems.push('overflow: <' + tag + '> ' + JSON.stringify({
        l: Math.round(r.left - sr.left), r: Math.round(r.right - sr.left),
        t: Math.round(r.top - sr.top), b: Math.round(r.bottom - sr.top)}));
    }
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText) {
      const fs = parseFloat(cs.fontSize);
      if (fs < floor - 0.01) {
        problems.push('font ' + fs.toFixed(1) + 'px in <' + tag + '> "' +
                      el.textContent.trim().slice(0, 40) + '"');
      }
    }
  }
  return problems;
}
"""


def problems(page, selector: str, tol: float = BOX_TOL,
             floor: float = FONT_FLOOR, skip: str | None = None) -> list[str]:
    """Every overflow and undersized-text problem inside `selector`, as readable strings.

    `page` is a Playwright page the caller has already navigated and settled. Returns an
    empty list when the composition is clean, so a caller can accumulate across slides or
    across instants and decide its own exit code.
    """
    return page.evaluate(JS_CHECK, [selector, tol, floor, skip])
