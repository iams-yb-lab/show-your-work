#!/usr/bin/env python3
"""Build the self-contained master from the template.

Splices the embedded fonts and the assets/ images into master-template.html
and writes how-to-use-the-skills.html. The master is generated, never
hand-edited; an edit lands in the template and this runs again.

Images stay out of the template the same way the fonts do: the template
carries src="__ASSET:name.png__" and this inlines the file from assets/ as a
data: URI, so the master keeps its one rule — nothing is fetched at render
time — while the template stays readable in a diff.
"""
import base64, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRES = os.path.dirname(HERE)
TEMPLATE = os.path.join(PRES, "master-template.html")
FONTS = os.path.join(PRES, "fonts.css")
ASSETS = os.path.join(PRES, "assets")
OUT = os.path.join(PRES, "how-to-use-the-skills.html")

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}

def inline_assets(out):
    """Replace every __ASSET:name__ with the file's data: URI. Missing file = build failure."""
    missing = []
    def sub(m):
        name = m.group(1)
        path = os.path.join(ASSETS, name)
        ext = os.path.splitext(name)[1].lower()
        if not os.path.exists(path) or ext not in MIME:
            missing.append(name)
            return m.group(0)
        blob = base64.b64encode(io.open(path, "rb").read()).decode("ascii")
        return "data:%s;base64,%s" % (MIME[ext], blob)
    out = re.sub(r"__ASSET:([A-Za-z0-9._-]+)__", sub, out)
    return out, missing

def main():
    tpl = io.open(TEMPLATE, encoding="utf-8").read()
    fonts = io.open(FONTS, encoding="utf-8").read()
    if "/*__FONTS__*/" not in tpl:
        print("FAIL: template lost its /*__FONTS__*/ placeholder"); return 1
    out = tpl.replace("/*__FONTS__*/", fonts, 1)
    out, missing = inline_assets(out)
    if missing:
        print("FAIL: template asks for assets that are not in assets/: %s" % ", ".join(sorted(set(missing))))
        return 1
    if "__ASSET:" in out:
        print("FAIL: an __ASSET:…__ placeholder survived the splice (malformed name?)"); return 1
    # Self-containment: nothing may be FETCHED at render time. Allowed as
    # pure click-targets (user-initiated navigation, never loaded by the page):
    # the two film links. The lucide URL appears only in a comment (license).
    allowed = [
        "https://www.youtube.com/watch?v=mXi9sxOSgwc",
        "https://www.youtube.com/watch?v=5jy-V41uGpI",
        "https://github.com/lucide-icons/lucide",
    ]
    scan = out
    for a in allowed:
        scan = scan.replace('href="%s"' % a, "").replace(a, "")
    if "http://" in scan or "https://" in scan:
        print("FAIL: master references an external URL outside the allowed click-targets"); return 1
    io.open(OUT, "w", encoding="utf-8").write(out)
    print("wrote %s (%.1f MB)" % (OUT, len(out) / 1e6))
    return 0

if __name__ == "__main__":
    sys.exit(main())
