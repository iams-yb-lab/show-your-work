#!/usr/bin/env python3
"""Shared config loader for the slide-deck toolkit.

Every tool takes an optional --deck DIR (default: the current directory) and
reads deck.json from it. One place to change the canvas, the font floor, the
export names or the theme.
"""
import argparse, json, os, sys

DEFAULTS = {
    "title": "Deck",
    "master": "deck.html",
    "storyline": "STORYLINE.md",
    "src_glob": "src/part*.html",
    "exports_dir": "exports",
    "canvas": [1920, 1080],
    "font_floor_px": 20,
    "font_family": "Manrope",
    "fonts_dir": "src/fonts",
    "font_weights": [400, 500, 600, 700, 800],
    "font_css_url": "",
    "pdf_name": "deck-with-notes.pdf",
    "pdf_notes_pages": True,
    "pptx_name": "deck.pptx",
    "pptx_template": "",
    "chrome": "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "theme": {
        "accent": "156082", "body": "3B3B3B", "secondary": "6E6E6E", "rule": "C9C9C9",
        "card_blue": "EFF5F8", "card_warn": "FDECE7", "warn_text": "B53B1E",
        "card_good": "E9F6EC", "good_text": "196B24", "tile_bg": "FAFAFA",
    },
}


class Cfg(dict):
    """dict with attribute access and deck-relative path helpers."""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def path(self, *parts):
        return os.path.normpath(os.path.join(self.deck, *parts))

    def export(self, name):
        d = self.path(self["exports_dir"])
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, name)

    @property
    def master_path(self):
        return self.path(self["master"])

    @property
    def toolkit(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(argv=None, extra=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default=os.getcwd(), help="deck folder (default: cwd)")
    for a in (extra or []):
        ap.add_argument(*a[0], **a[1])
    args = ap.parse_args(argv)
    deck = os.path.abspath(args.deck)
    cfg = Cfg(DEFAULTS)
    cfg["theme"] = dict(DEFAULTS["theme"])
    jf = os.path.join(deck, "deck.json")
    if os.path.exists(jf):
        user = json.load(open(jf, encoding="utf-8"))
        for k, v in user.items():
            if k.startswith("_"):
                continue
            if k == "theme" and isinstance(v, dict):
                cfg["theme"].update(v)
            else:
                cfg[k] = v
    else:
        print("note: no deck.json in %s — using defaults" % deck, file=sys.stderr)
    cfg["deck"] = deck
    cfg["args"] = args
    return cfg
