/* ============================================================================
 * mechcheck.js — the four mechanical checks for an HTML slide master.
 *
 * Drop this into any deck master built on the toolkit skeleton. It runs in the
 * browser, where real measured geometry is available, writes its verdict into
 * <div id="mechcheck">, and turns #mechbanner red on failure so a human cannot
 * miss it either. tools/run_mechcheck.py reads that node and exits non-zero.
 *
 * The checks, in order of how many real defects they find (least first):
 *   1. font floor       — text below the agreed floor for the room's back row
 *   2. slide overflow   — anything outside the fixed canvas
 *   3. element collision— two figures/cards/tiles drawn over each other
 *   4. text vs geometry — a line, curve or shape edge crossing a word, inside
 *                         one diagram
 *
 * Checks 1 and 2 are the cheap ones and catch almost nothing. Checks 3 and 4
 * are the ones that catch what a reviewer actually sees. Keep all four.
 *
 * Requires on the page:
 *   - #deck            the scaled 1:1 canvas wrapper
 *   - .slide           one per slide; .current is the rendered one
 *   - aside.notes      speaker notes, never rendered, always excluded
 * Configure via window.MECHCHECK = { canvas:[1920,1080], fontFloorPx:20 }.
 * ========================================================================= */
(function () {
  var CFG = window.MECHCHECK || {};
  var CANVAS = CFG.canvas || [1920, 1080];
  var FLOOR = CFG.fontFloorPx || 20;
  // Clearance, in SVG user units: a word must not merely avoid touching a line or a
  // block edge, it must stand clear of it. "Not touching" still reads as cramped.
  // Horizontal and vertical are not the same problem: a two-line label in a short
  // block is normal and reads fine, but a label almost touching a block's left or
  // right edge reads as cramped. So clearance is per-axis.
  var CLEAR_X = CFG.clearanceX == null ? 8 : CFG.clearanceX;   // strokes, sideways
  var CLEAR_Y = CFG.clearanceY == null ? 4 : CFG.clearanceY;   // strokes, vertically
  var INSET_X = CFG.insetX == null ? 12 : CFG.insetX;          // inside its own block
  var INSET_Y = CFG.insetY == null ? 3 : CFG.insetY;

  function run() {
    var fails = [];
    var deck = document.getElementById("deck");
    var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));

    slides.forEach(function (slide) {
      var id = slide.id || "slide";
      var wasCurrent = slide.classList.contains("current");
      slide.classList.add("current");               // must be laid out to measure

      var deckScale = deck.getBoundingClientRect().width / CANVAS[0];
      var sr = slide.getBoundingClientRect();
      var notNotes = function (el) { return !el.closest("aside.notes"); };

      /* ---- 1. font floor -------------------------------------------------- */
      Array.prototype.forEach.call(slide.querySelectorAll("*"), function (el) {
        if (!notNotes(el)) return;
        var hasText = Array.prototype.some.call(el.childNodes, function (n) {
          return n.nodeType === 3 && n.textContent.trim();
        });
        if (!hasText) return;
        var sz = parseFloat(getComputedStyle(el).fontSize);
        if (el.namespaceURI === "http://www.w3.org/2000/svg") {
          // an SVG scales with its container: measure the text at its real rendered size
          var svg = el.ownerSVGElement;
          if (svg) {
            var vb = svg.viewBox.baseVal;
            var w = svg.getBoundingClientRect().width;
            if (vb && vb.width) sz = sz * ((w / deckScale) / vb.width);
          }
        }
        if (sz < FLOOR - 0.5) {
          fails.push(id + ": font " + sz.toFixed(1) + "px < " + FLOOR + "px — \"" +
                     el.textContent.trim().slice(0, 40) + "\"");
        }
      });

      /* ---- 4. text vs geometry, inside each diagram ----------------------- */
      Array.prototype.forEach.call(slide.querySelectorAll("svg"), function (svg) {
        var texts = [];
        Array.prototype.forEach.call(svg.querySelectorAll("text"), function (t) {
          try { texts.push({ el: t, b: t.getBBox() }); } catch (e) {}
        });
        if (!texts.length) return;

        // grow the text box by the clearance: anything in the halo is too close
        var box = function (b) {
          return { x1: b.x - CLEAR_X, y1: b.y - CLEAR_Y,
                   x2: b.x + b.width + CLEAR_X, y2: b.y + b.height + CLEAR_Y };
        };
        var hit = function (t, x, y) { return x > t.x1 && x < t.x2 && y > t.y1 && y < t.y2; };
        var seen = {};
        var flag = function (el, what) {
          var k = id + "|" + el.textContent.trim().slice(0, 32) + "|" + what;
          if (seen[k]) return;
          seen[k] = 1;
          fails.push(id + ": \"" + el.textContent.trim().slice(0, 32) + "\" crossed by " + what);
        };

        // filled shapes: a label fully inside its own block is correct;
        // a label straddling the block's edge is not.
        Array.prototype.forEach.call(svg.querySelectorAll("rect, circle, ellipse"), function (sh) {
          var s;
          try { s = sh.getBBox(); } catch (e) { return; }
          texts.forEach(function (o) {
            var t = box(o.b);
            var ix = Math.min(t.x2, s.x + s.width) - Math.max(t.x1, s.x);
            var iy = Math.min(t.y2, s.y + s.height) - Math.max(t.y1, s.y);
            if (ix <= 0 || iy <= 0) return;
            // a label inside its own block is correct only if it keeps INSET
            // clear of every edge; flush against the edge reads as cramped
            var clear = o.b.x >= s.x + INSET_X && o.b.y >= s.y + INSET_Y &&
                        o.b.x + o.b.width <= s.x + s.width - INSET_X &&
                        o.b.y + o.b.height <= s.y + s.height - INSET_Y;
            if (!clear) flag(o.el, "a " + sh.tagName + " edge (needs " + INSET_X + "px sideways)");
          });
        });

        // strokes: walk the geometry. A bounding box is useless here — a diagonal
        // line's box covers half the diagram.
        var sample = function (el, ptAt, len, what) {
          for (var s = 0; s <= len; s += 3) {
            var p = ptAt(s);
            for (var i = 0; i < texts.length; i++) {
              if (hit(box(texts[i].b), p.x, p.y)) flag(texts[i].el, what + " (needs " + CLEAR_X + "px clearance)");
            }
          }
        };
        Array.prototype.forEach.call(svg.querySelectorAll("line"), function (ln) {
          if (ln.closest("defs")) return;
          var x1 = +ln.getAttribute("x1"), y1 = +ln.getAttribute("y1");
          var x2 = +ln.getAttribute("x2"), y2 = +ln.getAttribute("y2");
          var len = Math.hypot(x2 - x1, y2 - y1);
          if (!len) return;
          sample(ln, function (s) {
            return { x: x1 + (x2 - x1) * s / len, y: y1 + (y2 - y1) * s / len };
          }, len, "a line");
        });
        Array.prototype.forEach.call(svg.querySelectorAll("path"), function (pt) {
          if (pt.closest("defs")) return;
          var len;
          try { len = pt.getTotalLength(); } catch (e) { return; }
          if (!len) return;
          sample(pt, function (s) { return pt.getPointAtLength(s); }, len, "a curve");
        });
      });

      /* ---- 3. element collision ------------------------------------------ */
      var blocks = Array.prototype.slice
        .call(slide.querySelectorAll("svg, img, .card, .tile"))
        .filter(notNotes);
      for (var a = 0; a < blocks.length; a++) {
        for (var b = a + 1; b < blocks.length; b++) {
          var A = blocks[a], B = blocks[b];
          if (A.contains(B) || B.contains(A)) continue;
          if (A.closest(".no-collide") || B.closest(".no-collide")) continue;
          var ra = A.getBoundingClientRect(), rb = B.getBoundingClientRect();
          if (!ra.width || !rb.width) continue;
          var ov = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
          var oh = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
          if (ov > 2 && oh > 2) {
            fails.push(id + ": blocks overlap — <" + A.tagName.toLowerCase() +
                       "> over <" + B.tagName.toLowerCase() + ">");
          }
        }
      }

      /* ---- 2. slide overflow --------------------------------------------- */
      Array.prototype.forEach.call(slide.querySelectorAll("*"), function (el) {
        if (!notNotes(el)) return;
        var r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        var tol = 2 * deckScale;
        if (r.left < sr.left - tol || r.right > sr.right + tol ||
            r.top < sr.top - tol || r.bottom > sr.bottom + tol) {
          fails.push(id + ": overflow — <" + el.tagName.toLowerCase() + "> \"" +
                     (el.textContent || "").trim().slice(0, 40) + "\"");
        }
      });

      if (!wasCurrent) slide.classList.remove("current");
    });

    var out = document.getElementById("mechcheck");
    if (out) {
      out.textContent = fails.length
        ? "MECHCHECK FAIL\n" + fails.join("\n")
        : "MECHCHECK PASS (" + slides.length + " slides)";
    }
    if (fails.length) {
      var ban = document.getElementById("mechbanner");
      if (ban) {
        ban.style.display = "block";
        ban.textContent = "MECHANICAL CHECK FAILED — " + fails.length +
                          " finding(s); see #mechcheck in the DOM";
      }
    }
    return fails;
  }

  window.mechCheck = run;
  window.addEventListener("load", function () { setTimeout(run, 300); });
})();
