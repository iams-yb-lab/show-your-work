#!/usr/bin/env python3
"""Render every slide of the HTML master to a PNG, so they can be looked at.

The mechanical checks and a pair of eyes catch different things. On the deck this
toolkit came from, the checker found two defects the eyes had passed over, and the
eyes found one the checker had passed over. Run both, every build.

    python render_slides.py --deck . [--slides 3,7,12]
"""
import os, subprocess, sys
from deckcfg import load


def main():
    cfg = load(extra=[(["--slides"], {"default": "", "help": "comma list, e.g. 3,7,12 (default: all)"}),
                      (["--count"], {"type": int, "default": 0, "help": "how many slides (default: read the master)"})])
    n = cfg.args.count
    if not n:
        doc = open(cfg.master_path, encoding="utf-8").read()
        n = doc.count('<section class="slide"')
    want = [int(x) for x in cfg.args.slides.split(",") if x.strip()] or list(range(1, n + 1))
    outdir = cfg.export("slidepng")
    os.makedirs(outdir, exist_ok=True)
    url = "file:///" + cfg.master_path.replace("\\", "/")
    for i in want:
        png = os.path.join(outdir, "s%02d.png" % i)
        subprocess.run([cfg.chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=%d,%d" % (cfg.canvas[0], cfg.canvas[1]),
                        "--virtual-time-budget=6000", "--screenshot=" + png,
                        url + "#s%02d" % i],
                       capture_output=True, timeout=180)
        print(("ok   " if os.path.exists(png) else "FAIL ") + png)
    print("\nNow LOOK at them. A green mechcheck is not a reviewed slide.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
