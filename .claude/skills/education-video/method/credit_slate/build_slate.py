"""Build the closing credit slate every film ends on.

    python build_slate.py --config slate.json --title "<video title>" --date 2026-10-01 [--png] [--out path]

`slate.json` describes the lab once (name, subline, website, logo files, supporters); each film
supplies only its title and release date. Output: <out>.html, self-contained (logos and QR code
inlined, nothing fetched at render time), and with --png a 1920x1080 preview via Playwright and the
system Chrome. Requires `pip install segno` for the QR code.

The slate is a static picture held for `seconds` (default 3) at the end of the film. The composition
shows it from (duration - seconds) to the end; the narration master must already carry that much
silence at its tail so the audio stays the timing authority.

Example config (paths relative to the config file):

    {
      "lab_name": "IAMS-Yb-Lab",
      "subline": "Institute of Atomic and Molecular Sciences · Academia Sinica · Taipei",
      "url": "https://iamsquantum.github.io/new/index.html",
      "lab_logo": {"file": "../Assets/happyNanofiber.png", "height": 250},
      "supporters_caption": "Supported by",
      "supporters": [
        {"name": "IAMS", "file": "../Assets/IAMS.jpg", "height": 96},
        {"name": "Academia Sinica", "file": "../Assets/AcademiaSinica.png", "height": 104}
      ],
      "seconds": 3
    }
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "credit_slate_template.html"


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def qr_data_uri(url: str) -> str:
    import io

    import segno

    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", xmldecl=False, svgns=True,
                                    dark="#1B1F2A", light=None, border=1, scale=8)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build(cfg: dict, base: Path, title: str, date: str, template: Path) -> str:
    html = template.read_text(encoding="utf-8")
    url = cfg["url"]
    strip = "\n".join(
        f'      <img class="support" alt="{s["name"]}" style="height:{s["height"]}px" src="{data_uri(base / s["file"])}">'
        for s in cfg.get("supporters", [])
    )
    repl = {
        "{{TITLE}}": title,
        "{{DATE}}": date,
        "{{URL}}": url,
        "{{URL_TEXT}}": url.replace("https://", "").replace("http://", "").removesuffix("/index.html").rstrip("/"),
        "{{QR}}": qr_data_uri(url),
        "{{SECONDS}}": f"{cfg.get('seconds', 3):g}",
        "{{LAB_NAME}}": cfg["lab_name"],
        "{{SUBLINE}}": cfg.get("subline", ""),
        "{{LAB_LOGO}}": data_uri(base / cfg["lab_logo"]["file"]),
        "{{LAB_LOGO_H}}": str(cfg["lab_logo"].get("height", 250)),
        "{{SUPPORTERS_CAPTION}}": cfg.get("supporters_caption", "Supported by"),
        "{{SUPPORT_LOGOS}}": strip,
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    return html


def render_png(html_path: Path, png_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(300)
        page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": 1920, "height": 1080})
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="slate.json describing the lab")
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True, help="release date, ISO YYYY-MM-DD")
    ap.add_argument("--template", default=str(TEMPLATE))
    ap.add_argument("--out", default="credit_slate", help="output path without extension")
    ap.add_argument("--png", action="store_true", help="also render a 1920x1080 PNG preview")
    a = ap.parse_args()

    cfg_path = Path(a.config).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    html_path = out.with_suffix(".html")
    html_path.write_text(build(cfg, cfg_path.parent, a.title, a.date, Path(a.template)),
                         encoding="utf-8", newline="\n")
    print(html_path)
    if a.png:
        png = out.with_suffix(".png")
        render_png(html_path, png)
        print(png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
