#!/usr/bin/env python3
"""Mechanical cross-check: the master vs the storyline. Never eyeballed.

1. Parses slide headlines out of the built HTML master and out of
   STORYLINE.md (written independently) and exits non-zero on any
   difference in count, order, or bytes (after whitespace collapse).
2. Static font-floor check: every font-size in the master, CSS or SVG
   or JS-generated, must be >= the GATE 0 floor (28px on the 1080p canvas).
"""
import html as htmllib
import io, os, re, sys
from pathlib import Path

# The floor is defined once, in _shared/checks/composition.py. This file checks it statically —
# every font-size written in the master, whether or not it ever renders — and render_check.py
# checks it as computed. Two methods answering one question is the point; two numbers is not.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "_shared" / "checks"))
from composition import FONT_FLOOR  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRES = os.path.dirname(HERE)
MASTER = os.path.join(PRES, "how-to-use-the-skills.html")
STORYLINE = os.path.join(PRES, "STORYLINE.md")
FLOOR = FONT_FLOOR

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def storyline_headlines():
    out, in_comment = [], False
    for line in io.open(STORYLINE, encoding="utf-8"):
        t = line.strip()
        if in_comment:
            if "-->" in t:
                in_comment = False
            continue
        if t.startswith("<!--") and "-->" not in t:
            in_comment = True
            continue
        if not t or t.startswith("ACT") or t.startswith("<") or t.startswith("#"):
            continue
        out.append(norm(t))
    return out

def master_headlines(doc):
    heads = re.findall(r'<h1 class="headline"[^>]*>(.*?)</h1>', doc, re.S)
    return [norm(htmllib.unescape(re.sub(r"<[^>]+>", "", h))) for h in heads]

def font_floor_violations(doc):
    bad = []
    for m in re.finditer(r'font-size\s*[:=]\s*"?\s*(\d+(?:\.\d+)?)(px)?"?', doc):
        v = float(m.group(1))
        if v < FLOOR:
            bad.append((v, doc[max(0, m.start()-40):m.end()+10]))
    return bad

def main():
    doc = io.open(MASTER, encoding="utf-8").read()
    a, b = storyline_headlines(), master_headlines(doc)
    fail = False
    if len(a) != len(b):
        print("FAIL: storyline has %d headlines, master has %d" % (len(a), len(b)))
        fail = True
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            print("FAIL: slide %d differs\n  storyline: %s\n  master:    %s" % (i, x, y))
            fail = True
    for v, ctx in font_floor_violations(doc):
        print("FAIL: font-size %.1f below the %dpx floor near: …%s…" % (v, FLOOR, ctx))
        fail = True
    if fail:
        return 1
    print("OK: %d slides, headlines byte-identical after whitespace collapse; no font below %dpx"
          % (len(a), FLOOR))
    return 0

if __name__ == "__main__":
    sys.exit(main())
