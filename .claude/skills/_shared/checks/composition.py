#!/usr/bin/env python3
"""The rendered checks that every authored composition has to pass, in one place.

  1. nothing visible extends past the canvas
  2. no visible text renders below the font floor
  3. nothing is drawn on top of anything else — text on text, text on a picture,
     picture on a picture
  4. inside a drawing, no line, curve or block edge comes within the clearance of
     a word

All four are measured in a real browser on the computed style, because all four
failures are invisible in the source. A heading that fits at the author's zoom
overflows at 1920x1080; a font size that reads fine on a laptop is unreadable in a
projected room; a 1560px diagram dropped into a 1130px column lands on its
neighbour and the HTML looks blameless. Only the renderer knows.

    slide-deck/examples/presentation/tools/render_check.py   per slide, plus screenshots
    education-video/method/composition_check.py              per instant, plus determinism,
                                                             offline behaviour and a contact sheet

The caller owns the browser and the page; this module owns the question. `skip` exists
because a deck carries speaker notes in the DOM that are not part of the picture.

Where 3 and 4 come from
-----------------------
A deck that passed checks 1 and 2 went to its author with six layout defects on his
first look at a screen: a diagram sitting on a plot, lines through three labels,
words jammed against block edges. Neither check could see any of them, because every
defect was full-size text inside the canvas. Checks 3 and 4 are what those defects
taught. They are ported from the toolkit that came back from that deck, and their
constants are the tuned ones, not guesses: a symmetric 12px clearance reported 54
findings on 15 slides and nearly all were fine; the per-axis rule below reported 8,
and all 8 were real. A check that floods its report gets switched off, which is worse
than no check.

Two deliberate exemptions, because without them check 3 fires on every good design:

  `.no-collide`   opt out one element and its subtree. For a layer that is meant to
                  sit on another — a caption band, a callout, a highlight.
  a backdrop      a picture covering BACKDROP_FRAC or more of the canvas is a
                  background layer, so nothing is reported against it.

Neither is a way to silence a real finding. If you reach for `.no-collide` more than
once or twice on one composition, the layout is the problem.
"""

from __future__ import annotations

# GATE 0 of slide-deck sets the floor and education-video inherits it. Computed px, not
# authored: a 28px rule authored inside a transformed parent is not 28px on screen.
FONT_FLOOR = 28.0
BOX_TOL = 1.0     # px of slack on the canvas edge, for subpixel layout rounding

# Overlap, in rendered px. Two boxes that share less than this in either direction are
# touching, not overlapping — borders and subpixel rounding do that on clean layouts.
OVERLAP_TOL = 2.0
BACKDROP_FRAC = 0.85   # a picture this much of the canvas is a background, not a figure

# Clearance from a word, in the drawing's own user units. Horizontal and vertical are
# not the same problem: a two-line label in a short block is normal and reads fine, but
# a label almost touching a block's left or right edge is the defect the eye catches
# first. So clearance is per-axis, and these are the numbers that survived tuning.
CLEAR_X = 8.0     # from a stroke, sideways
CLEAR_Y = 4.0     # from a stroke, vertically
INSET_X = 12.0    # from the edge of the block the word sits in, sideways
INSET_Y = 3.0     # from the edge of the block the word sits in, vertically

JS_CHECK = """
([selector, tol, floor, skip]) => {
  const root = document.querySelector(selector);
  if (!root) return ['the canvas ' + selector + ' is not in the page'];
  const problems = [];
  const sr = root.getBoundingClientRect();
  // checkVisibility walks the ancestors. getComputedStyle(el).opacity is the element's
  // OWN opacity, so a whole beat faded out by its parent measured as if it were on
  // screen — which is how a film's every scene appeared to be stacked on every other.
  const onScreen = (el) => el.checkVisibility
    ? el.checkVisibility({opacityProperty: true, visibilityProperty: true,
                          contentVisibilityAuto: true})
    : (() => { const c = getComputedStyle(el);
               return c.display !== 'none' && c.visibility !== 'hidden' &&
                      parseFloat(c.opacity) !== 0; })();
  for (const el of root.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (!onScreen(el)) continue;
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

JS_OVERLAP = """
([selector, cfg, skip]) => {
  const root = document.querySelector(selector);
  if (!root) return [];
  const out = [];
  const seen = {};
  const rr = root.getBoundingClientRect();
  const rootArea = Math.max(rr.width * rr.height, 1);

  // checkVisibility walks the ancestors, which is the whole point: an element's own
  // opacity says nothing about the beat that faded it out.
  const shown = (el) => {
    const vis = el.checkVisibility
      ? el.checkVisibility({opacityProperty: true, visibilityProperty: true,
                            contentVisibilityAuto: true})
      : (() => { const c = getComputedStyle(el);
                 return c.display !== 'none' && c.visibility !== 'hidden' &&
                        parseFloat(c.opacity) !== 0; })();
    if (!vis) return false;
    if (skip && el.closest(skip)) return false;
    if (el.closest('.no-collide')) return false;
    return true;
  };
  const tag = (el) => el.tagName.toLowerCase() +
    (el.className && typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\\s+/)[0] : '');
  const words = (el) => (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 32);

  /* ---- 3. nothing drawn on top of anything else ------------------------- */
  // Measure the words, not the boxes that hold them. An element's box carries its
  // padding and its line-height leading, and two boxes can share 12px while the
  // glyphs are nowhere near each other — which is the false positive that would
  // make this check useless on any tightly set layout. A Range over the element's
  // own text nodes gives one box per rendered line; taking the leading back off
  // leaves roughly the band the ink actually occupies.
  const ink = (el) => {
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    let lh = parseFloat(cs.lineHeight);
    if (!isFinite(lh)) lh = fs * 1.2;
    const pad = Math.max(0, (lh - fs) / 2);
    const rects = [];
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      const rg = document.createRange();
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) {
        if (r.width <= 0 || r.height <= 0) continue;
        const top = r.top + pad, bottom = r.bottom - pad;
        if (bottom - top < 1) continue;
        rects.push({left: r.left, right: r.right, top: top, bottom: bottom});
      }
    }
    return rects;
  };
  const asRects = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0
      ? [{left: r.left, right: r.right, top: r.top, bottom: r.bottom}] : [];
  };

  // A picture is something drawn; a word is an element carrying its own text.
  // Text inside a drawing belongs to check 4, which measures it in the drawing's
  // own units.
  const pics = [...root.querySelectorAll('svg, img, picture, video, canvas, .card, .tile, .figure')]
    .filter(el => shown(el) && !(el.parentElement && el.parentElement.closest('svg')));
  const txts = [...root.querySelectorAll('*')].filter(el =>
    !el.closest('svg') && shown(el) &&
    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));

  // A picture the size of the canvas is a background layer. Everything is "on" it by
  // design, so reporting it would bury every real finding.
  const figures = pics.filter(el => {
    const r = el.getBoundingClientRect();
    return r.width * r.height < cfg.backdrop * rootArea;
  }).map(el => ({el: el, rs: asRects(el)})).filter(o => o.rs.length);
  const written = txts.map(el => ({el: el, rs: ink(el)})).filter(o => o.rs.length);

  const over = (A, B) => {
    if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) return null;
    let best = null;
    for (const a of A.rs) for (const b of B.rs) {
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w <= cfg.tol || h <= cfg.tol) continue;
      if (!best || w * h > best[0] * best[1]) best = [w, h];
    }
    return best ? Math.round(best[0]) + 'x' + Math.round(best[1]) : null;
  };
  const report = (kind, A, B, size) => {
    const k = kind + '|' + tag(A.el) + '|' + tag(B.el) + '|' + size;
    if (seen[k]) return;
    seen[k] = 1;
    let said = '';
    if (kind === 'text over text') said = ' "' + words(A.el) + '" / "' + words(B.el) + '"';
    else if (kind === 'text over a picture') said = ' "' + words(A.el) + '"';
    out.push('overlap, ' + kind + ': <' + tag(A.el) + '> over <' + tag(B.el) + '>' + said +
             ' — ' + size + 'px shared');
  };

  for (let i = 0; i < figures.length; i++)
    for (let j = i + 1; j < figures.length; j++) {
      const s = over(figures[i], figures[j]);
      if (s) report('a picture over a picture', figures[i], figures[j], s);
    }
  for (const t of written)
    for (const p of figures) {
      const s = over(t, p);
      if (s) report('text over a picture', t, p, s);
    }
  for (let i = 0; i < written.length; i++)
    for (let j = i + 1; j < written.length; j++) {
      const s = over(written[i], written[j]);
      if (s) report('text over text', written[i], written[j], s);
    }

  /* ---- 4. inside a drawing, a word must stand clear --------------------- */
  // Clearance, not contact. "Not touching" still reads as cramped, and the author of
  // the deck this came from rejected the same slide twice in those words.
  for (const svg of root.querySelectorAll('svg')) {
    if (!shown(svg)) continue;

    // Every box in the drawing's own coordinates. getBBox() is in the element's own
    // user space, so a shape inside a <g transform> is reported somewhere it is not
    // drawn; getCTM() is the matrix back to the drawing, and without it the check
    // compares a label against a shape that has already been moved out from under it.
    const mapped = (el) => {
      let b;
      try { b = el.getBBox(); } catch (e) { return null; }
      if (!b || (!b.width && !b.height)) return null;
      let m;
      try { m = el.getCTM(); } catch (e) { m = null; }
      if (!m) return {x: b.x, y: b.y, width: b.width, height: b.height};
      const xs = [], ys = [];
      for (const [x, y] of [[b.x, b.y], [b.x + b.width, b.y],
                            [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]) {
        xs.push(m.a * x + m.c * y + m.e);
        ys.push(m.b * x + m.d * y + m.f);
      }
      const x0 = Math.min(...xs), y0 = Math.min(...ys);
      return {x: x0, y: y0, width: Math.max(...xs) - x0, height: Math.max(...ys) - y0};
    };

    const texts = [];
    for (const t of svg.querySelectorAll('text')) {
      if (!shown(t)) continue;
      const b = mapped(t);
      if (b) texts.push({el: t, b: b});
    }
    if (!texts.length) continue;

    // grow the word's box by the clearance: anything in the halo is too close
    const halo = (b) => ({x1: b.x - cfg.clearX, y1: b.y - cfg.clearY,
                          x2: b.x + b.width + cfg.clearX, y2: b.y + b.height + cfg.clearY});
    const inside = (h, x, y) => x > h.x1 && x < h.x2 && y > h.y1 && y < h.y2;
    const flag = (el, what) => {
      const k = 'clear|' + words(el) + '|' + what;
      if (seen[k]) return;
      seen[k] = 1;
      out.push('too close: "' + words(el) + '" ' + what);
    };

    for (const sh of svg.querySelectorAll('rect, circle, ellipse')) {
      if (sh.closest('defs') || !shown(sh)) continue;
      const s = mapped(sh);
      if (!s) continue;
      for (const o of texts) {
        const h = halo(o.b);
        if (Math.min(h.x2, s.x + s.width) - Math.max(h.x1, s.x) <= 0) continue;
        if (Math.min(h.y2, s.y + s.height) - Math.max(h.y1, s.y) <= 0) continue;
        // A shape big enough to hold the word is the block the word sits in, and a
        // word inside its own block is correct — as long as it keeps the inset clear
        // of every edge. A shape smaller than that is a mark, not a container: a
        // waveform bar or a tick can never contain its label, so the containment
        // rule would report it forever. A mark is judged like a stroke instead.
        const holds = s.width >= o.b.width && s.height >= o.b.height;
        if (holds) {
          const okX = o.b.x >= s.x + cfg.insetX &&
                      o.b.x + o.b.width <= s.x + s.width - cfg.insetX;
          const okY = o.b.y >= s.y + cfg.insetY &&
                      o.b.y + o.b.height <= s.y + s.height - cfg.insetY;
          if (okX && okY) continue;
          const axis = !okX ? cfg.insetX + 'px sideways' : cfg.insetY + 'px vertically';
          flag(o.el, 'against a ' + sh.tagName + ' edge (needs ' + axis + ')');
        } else {
          flag(o.el, 'crowded by a ' + sh.tagName + ' (needs ' + cfg.clearX + 'px sideways, ' +
                     cfg.clearY + 'px vertically)');
        }
      }
    }

    // Strokes. Walk the geometry: a bounding box is useless here, because a diagonal
    // line's box covers half the drawing.
    const walk = (el, at, len, what) => {
      let m;
      try { m = el.getCTM(); } catch (e) { m = null; }
      for (let s = 0; s <= len; s += 3) {
        const p = at(s);
        const x = m ? m.a * p.x + m.c * p.y + m.e : p.x;
        const y = m ? m.b * p.x + m.d * p.y + m.f : p.y;
        for (const o of texts) if (inside(halo(o.b), x, y)) flag(o.el, what);
      }
    };
    for (const ln of svg.querySelectorAll('line')) {
      if (ln.closest('defs') || !shown(ln)) continue;
      const x1 = +ln.getAttribute('x1'), y1 = +ln.getAttribute('y1');
      const x2 = +ln.getAttribute('x2'), y2 = +ln.getAttribute('y2');
      const len = Math.hypot(x2 - x1, y2 - y1);
      if (!len) continue;
      walk(ln, (s) => ({x: x1 + (x2 - x1) * s / len, y: y1 + (y2 - y1) * s / len}), len,
           'crossed by a line (needs ' + cfg.clearX + 'px clearance)');
    }
    for (const pt of svg.querySelectorAll('path')) {
      if (pt.closest('defs') || !shown(pt)) continue;
      let len;
      try { len = pt.getTotalLength(); } catch (e) { continue; }
      if (!len) continue;
      walk(pt, (s) => pt.getPointAtLength(s), len,
           'crossed by a curve (needs ' + cfg.clearX + 'px clearance)');
    }
  }
  return out;
}
"""


def overlap_config(tol: float = OVERLAP_TOL, backdrop: float = BACKDROP_FRAC,
                   clear_x: float = CLEAR_X, clear_y: float = CLEAR_Y,
                   inset_x: float = INSET_X, inset_y: float = INSET_Y) -> dict:
    """The tuned constants, in the shape `JS_OVERLAP` reads them."""
    return {"tol": tol, "backdrop": backdrop, "clearX": clear_x, "clearY": clear_y,
            "insetX": inset_x, "insetY": inset_y}


def problems(page, selector: str, tol: float = BOX_TOL,
             floor: float = FONT_FLOOR, skip: str | None = None,
             overlaps: bool = True, config: dict | None = None) -> list[str]:
    """Every problem inside `selector`, as readable strings.

    Overflow and undersized text first, then anything drawn on top of anything else and
    anything crowding a word inside a drawing. `page` is a Playwright page the caller has
    already navigated and settled. Returns an empty list when the composition is clean, so
    a caller can accumulate across slides or across instants and decide its own exit code.

    `overlaps=False` runs only the two cheap checks. It exists for a caller that measures
    a composition mid-transition, where things genuinely do pass over each other; it is
    not for quietening a finding on a finished picture.
    """
    found = page.evaluate(JS_CHECK, [selector, tol, floor, skip])
    if overlaps:
        found += page.evaluate(JS_OVERLAP, [selector, config or overlap_config(), skip])
    return found
