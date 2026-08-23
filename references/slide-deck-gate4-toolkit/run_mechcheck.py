#!/usr/bin/env python3
"""Run the master's built-in mechanical checks and exit non-zero on any finding.

Loads the master in headless Chrome, lets mechcheck.js run, reads the verdict
out of #mechcheck. This is the step that must never be replaced by eyeballing —
but it is also not a substitute for tools/render_slides.py. Both, every build.
"""
import html as htmlmod
import os, re, subprocess, sys
from deckcfg import load


def main():
    cfg = load()
    url = "file:///" + cfg.master_path.replace("\\", "/")
    r = subprocess.run([cfg.chrome, "--headless=new", "--disable-gpu",
                        "--window-size=%d,%d" % (cfg.canvas[0], cfg.canvas[1]),
                        "--virtual-time-budget=9000", "--dump-dom", url],
                       capture_output=True, text=True, timeout=300)
    m = re.search(r'<div id="mechcheck">(.*?)</div>', r.stdout, re.S)
    if not m:
        print("could not find #mechcheck in the rendered DOM — is mechcheck.js inlined?",
              file=sys.stderr)
        return 2
    verdict = htmlmod.unescape(m.group(1)).strip()
    print(verdict)
    return 1 if verdict.startswith("MECHCHECK FAIL") else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
