#!/usr/bin/env python3
"""Prove the composition checks can fail, then prove they stay quiet on clean work.

A mechanical check that has only ever passed is not evidence. This builds one clean
1920x1080 composition, confirms every check is silent on it, then injects exactly one
deliberate defect at a time and confirms the right check catches each — text on text,
text on a picture, a picture on a picture, a word crossed by a line, a word flush to
the edge of its own block, a word crowded by a mark, something past the canvas,
text below the font floor, and a word that is only too small once its diagram is
scaled.

    python tools/test_composition_check.py            # all cases
    python tools/test_composition_check.py --keep     # leave the fixtures to look at

Needs a system Chrome; it does not need Playwright, so it runs anywhere the skills do.
Exits non-zero if any case reports the wrong thing.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Do not anchor on the checkout — .claude/skills/_shared/README.md. Walk up to the tree
# that holds the skills.
REPO = next((p for p in Path(__file__).resolve().parents
             if (p / ".claude" / "skills" / "natural-voice").is_dir()), None)
if REPO is None:
    raise SystemExit("cannot find the tree holding .claude/skills/natural-voice/")
sys.path.insert(0, str(REPO / ".claude" / "skills" / "_shared" / "checks"))
import composition as C  # noqa: E402


def find_chrome() -> str:
    candidates = [
        shutil.which("chrome"), shutil.which("chromium"), shutil.which("google-chrome"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome", "/usr/bin/chromium",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return str(Path(c).resolve())
    raise SystemExit("Google Chrome/Chromium was not found; this test needs a browser")


# A small drawing, as a data: URI, so the fixture fetches nothing.
PIC = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
    b'<rect width="400" height="300" fill="#cfd8e3"/></svg>').decode())

CLEAN = """
<div id="canvas">
  <h1 id="head">A headline that stays in its lane</h1>
  <p id="lead">A paragraph of body text, well clear of everything else on the canvas.</p>
  <img id="pic" src="%s">
  <svg id="draw" width="1200" height="360" viewBox="0 0 1200 360">
    <rect id="block" x="40" y="40" width="400" height="140" fill="#eeeeee" stroke="#333333"/>
    <text id="inblock" x="60" y="120" font-size="32">inside its block</text>
    <line id="rule" x1="40" y1="260" x2="1160" y2="260" stroke="#333333" stroke-width="3"/>
    <text id="underline" x="60" y="330" font-size="32">below the line</text>
  </svg>
</div>
""" % PIC

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>fixture</title><style>
  html, body { margin: 0; padding: 0; background: #ffffff; }
  #canvas { position: relative; width: 1920px; height: 1080px; background: #ffffff;
            font-family: Helvetica, Arial, sans-serif; color: #111111; }
  #head { position: absolute; left: 100px; top: 80px; width: 1200px; margin: 0;
          font-size: 64px; line-height: 1.2; }
  #lead { position: absolute; left: 100px; top: 260px; width: 800px; margin: 0;
          font-size: 32px; line-height: 1.4; }
  #pic  { position: absolute; left: 1000px; top: 260px; width: 400px; height: 300px; }
  #draw { position: absolute; left: 100px; top: 640px; }
  .extra { position: absolute; margin: 0; font-size: 32px; line-height: 1.4; }
</style></head><body>
%(body)s
<script>
(function () {
  const CHECK = %(check)s;
  const OVER  = %(over)s;
  function run() {
    let p = [];
    try { p = p.concat(CHECK(['#canvas', %(tol)s, %(floor)s, null])); }
    catch (e) { p.push('CHECK threw: ' + e); }
    try { p = p.concat(OVER(['#canvas', %(cfg)s, null])); }
    catch (e) { p.push('OVER threw: ' + e); }
    const d = document.createElement('div');
    d.id = '__result';
    d.textContent = btoa(unescape(encodeURIComponent(JSON.stringify(p))));
    document.body.appendChild(d);
  }
  window.addEventListener('load', () => setTimeout(run, 250));
})();
</script>
</body></html>
"""

# Each case: a name, how it damages the clean fixture, and what the report must say.
# "" means the report must be empty.
CASES = [
    ("clean", lambda b: b, ""),
    ("text over text",
     lambda b: b.replace("</svg>\n</div>", "</svg>\n"
                         '<p class="extra" style="left:120px;top:280px">overlapping words</p>\n</div>'),
     "overlap, text over text"),
    ("text over a picture",
     lambda b: b.replace("</svg>\n</div>", "</svg>\n"
                         '<p class="extra" style="left:1040px;top:300px">on the picture</p>\n</div>'),
     "overlap, text over a picture"),
    ("a picture over a picture",
     lambda b: b.replace("</svg>\n</div>", "</svg>\n"
                         '<img class="extra" style="left:1200px;top:400px;width:400px;height:300px" src="%s">\n</div>' % PIC),
     "overlap, a picture over a picture"),
    ("a word crossed by a line",
     lambda b: b.replace('id="rule" x1="40" y1="260" x2="1160" y2="260"',
                         'id="rule" x1="40" y1="320" x2="1160" y2="320"'),
     "crossed by a line"),
    ("a word crossed by a polygon edge",
     # An arrowhead or a callout outline is a polygon, and its edges are shape edges
     # like any other. The left edge of this one runs straight down through the word.
     lambda b: b.replace("</svg>",
                         '<polygon points="150,280 400,280 400,360 150,360" fill="none" '
                         'stroke="#333333" stroke-width="3"/></svg>'),
     "crossed by a shape edge"),
    ("a word flush to its block edge",
     lambda b: b.replace('id="inblock" x="60"', 'id="inblock" x="44"'),
     "against a rect edge"),
    ("a word crowded by a mark",
     # 2.3px clear of the word "below the line", whose box ends at x=255.7: not
     # touching, and still too close. That is the whole point of the rule.
     lambda b: b.replace("</svg>", '<rect x="258" y="305" width="8" height="30" fill="#333333"/></svg>'),
     "crowded by a rect"),
    ("something past the canvas",
     lambda b: b.replace("</svg>\n</div>", "</svg>\n"
                         '<p class="extra" style="left:1800px;top:1000px;width:400px">past the edge</p>\n</div>'),
     "overflow:"),
    ("a word small only once scaled",
     # 32px authored inside a viewBox squeezed to half its width is 16px on the wall,
     # and the computed style still says 32. The floor is about what the room sees.
     lambda b: b.replace('<svg id="draw" width="1200" height="360"',
                         '<svg id="draw" width="600" height="180"'),
     "font 16.0px"),
    ("text below the font floor",
     lambda b: b.replace("</svg>\n</div>", "</svg>\n"
                         '<p class="extra" style="left:100px;top:560px;font-size:20px">too small to read</p>\n</div>'),
     "font 20.0px"),
]


def render(chrome: str, body: str, where: Path) -> list[str]:
    where.write_text(PAGE % {
        "body": body, "check": C.JS_CHECK.strip(), "over": C.JS_OVERLAP.strip(),
        "tol": json.dumps(C.BOX_TOL), "floor": json.dumps(C.FONT_FLOOR),
        "cfg": json.dumps(C.overlap_config()),
    }, encoding="utf-8")
    r = subprocess.run([chrome, "--headless=new", "--disable-gpu",
                        "--window-size=1920,1200", "--virtual-time-budget=8000",
                        "--dump-dom", "file://" + str(where.resolve())],
                       capture_output=True, text=True, timeout=180)
    m = re.search(r'<div id="__result">([A-Za-z0-9+/=]*)</div>', r.stdout)
    if not m:
        raise SystemExit("the fixture did not report; Chrome said:\n" + (r.stderr or "")[-1500:])
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="leave the fixtures on disk")
    args = ap.parse_args()

    chrome = find_chrome()
    tmp = Path(tempfile.mkdtemp(prefix="composition-check-"))
    bad = 0
    try:
        for name, damage, expect in CASES:
            found = render(chrome, damage(CLEAN), tmp / (name.replace(" ", "-") + ".html"))
            if not expect:
                ok = not found
                why = "clean, and the checks say so" if ok else f"{len(found)} finding(s) on clean work"
            else:
                ok = any(expect in f for f in found)
                why = ("caught: " + next(f for f in found if expect in f)) if ok \
                    else ("NOT caught; the report said " + (json.dumps(found) if found else "nothing"))
            print(f"{'PASS' if ok else 'FAIL'}  {name:<32} {why}")
            if not ok:
                bad += 1
                for f in found:
                    print(f"        - {f}")
        print()
        print("ALL PASS" if not bad else f"{bad} CASE(S) FAILED")
        if args.keep:
            print(f"fixtures: {tmp}")
        return 1 if bad else 0
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
