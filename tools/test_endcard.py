#!/usr/bin/env python3
"""Prove the end card's rules can fail, then prove they stay quiet on a good card.

A validator that has only ever said yes is not evidence. This takes one credits file that
is correct, confirms it builds, then breaks exactly one thing at a time and confirms the
right rule catches each -- a missing mode, a project film that credits nobody for the
project, a standalone film with a project block, a missing disclosure, nobody answerable,
no contact, a role with nobody in it -- and confirms the two rules that are meant to stay
silent do: an unfilled role is dropped rather than defaulted, and an empty image manifest
adds no row.

Then it checks the parts that are arithmetic rather than policy: the grid fit model, which
must count a CSS grid's row maxima rather than a column's total, and the wrap counting that
keeps a long credit from being underestimated off the bottom of the card.

Then the closing-frame card: a byline moves the film's roles out of the grid rather than
copying them, a still and a QR code take budget away from the credits, a link that points
where the accountability contact already points is not printed twice, and a byline long
enough to be a credits block is refused rather than set in three lines under the title.

    python tools/test_endcard.py

Pure Python. No browser, no ffmpeg -- check_card.py is what asks a browser, and this is
what proves the rules underneath it. Exits non-zero if any case reports the wrong thing.
"""

from __future__ import annotations

import base64
import copy
import json
import sys
import tempfile
from pathlib import Path

# Do not anchor on the checkout -- .claude/skills/_shared/README.md. Walk up to the tree
# that holds the skills.
REPO = next((p for p in Path(__file__).resolve().parents
             if (p / ".claude" / "skills" / "natural-voice").is_dir()), None)
if REPO is None:
    raise SystemExit("cannot find the tree holding .claude/skills/natural-voice/")
ENDCARD = REPO / ".claude" / "skills" / "_shared" / "endcard"
sys.path.insert(0, str(ENDCARD))
import build_card as B  # noqa: E402


GOOD = {
    "mode": "project",
    "film": {"title": "How the Cooling Loop Holds Temperature", "kind": "Explainer",
             "year": "2026",
             "credits": [{"role": "Written & produced", "names": ["A. Researcher"]},
                         {"role": "Narration", "names": ["Synthetic speech"]}]},
    "project": {"name": "Cooling loop rev C",
                "credits": [{"role": "Design", "names": ["B. Engineer"]}]},
    "sources": [{"role": "Source document", "names": ["Design report, rev C"]}],
    "supervision": [{"role": "Principal investigator", "names": ["E. Supervisor"]}],
    "disclosure": "Narration is synthetic speech. The picture was built with an AI assistant.",
    "accountability": {"responsible": "Example Research Group",
                       "contact": "example.org/cooling-loop"},
    "identity": {"name": "Example Research Group"},
    "duration_s": 6,
}


def write(tmp: Path, data: dict, name: str = "credits.json") -> Path:
    p = tmp / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def broken(**changes) -> dict:
    """A copy of GOOD with one thing wrong. A key set to None is deleted."""
    d = copy.deepcopy(GOOD)
    for dotted, value in changes.items():
        keys = dotted.split("__")
        target = d
        for k in keys[:-1]:
            target = target[k]
        if value is None:
            target.pop(keys[-1], None)
        else:
            target[keys[-1]] = value
    return d


# Each case: a name, the credits data, and a phrase the refusal must contain.
REFUSALS = [
    ("mode missing", broken(mode=None), "mode must be"),
    ("mode nonsense", broken(mode="whatever"), "mode must be"),
    ("no film title", broken(film__title=""), "film.title is required"),
    ("film credits empty", broken(film__credits=[]), "at least one person"),
    ("project mode, no project name", broken(project__name=""), "project.name is required"),
    ("project mode, nobody built it", broken(project__credits=[]),
     "takes credit for someone else's work"),
    ("standalone with a project", broken(mode="standalone"), "but a project block is filled"),
    ("no disclosure", broken(disclosure=""), "disclosure is required"),
    ("nobody responsible", broken(accountability__responsible=""),
     "accountability.responsible is required"),
    ("no contact", broken(accountability__contact=""), "accountability.contact is required"),
    ("a role with nobody in it",
     broken(film__credits=[{"role": "", "names": ["A. Researcher"]}]), "has names but no role"),
    ("credits that are not objects", broken(sources=["just a string"]), "is not an object"),
    ("an image credit with no image", broken(film__image_credit="Frame from the film"),
     "image that is not on the card"),
    ("a link that goes nowhere", broken(link={"label": "The project"}), "goes nowhere"),
    ("a link with no label", broken(link={"url": "https://example.org/p"}),
     "link.label is required"),
]

MANIFEST_WITH_ROWS = """\
| file | shows | cue | source | licence | attribution | edited |
|---|---|---|---|---|---|---|
| a.jpg | a pump | 3 | http://x | CC BY 4.0 | J. Photographer | cropped |
| b.jpg | a valve | 5 | http://y | CC BY 4.0 | J. Photographer | none |
| c.jpg | a rack | 9 | http://z | Public domain | - | none |
"""

MANIFEST_EMPTY = """\
| file | shows | cue | source | licence | attribution | edited |
|---|---|---|---|---|---|---|
"""


# The smallest valid PNG. The still only has to exist and be embeddable; what it looks
# like is check_card.py's business, not this file's.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")


def main() -> int:
    bad = 0
    skipped: list[str] = []

    def report(name: str, ok: bool, why: str) -> None:
        nonlocal bad
        print(f"{'PASS' if ok else 'FAIL'}  {name:<34} {why}")
        if not ok:
            bad += 1

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # ---- the good card builds, and check_card.py is what judges the pixels ----------
        try:
            B.build(write(tmp, GOOD), tmp / "card.html", 1920, 1080, 1, None)
            html = (tmp / "card.html").read_text(encoding="utf-8")
            ok = ("data-om-exportable-video-with-duration-secs=\"6" in html
                  and "@font-face" in html and "Example Research Group" in html)
            report("a good card builds", ok,
                   "built, self-contained, duration on the root" if ok
                   else "built but is missing the export attribute, the fonts, or the identity")
        except B.CardError as exc:
            report("a good card builds", False, f"refused a valid card: {exc}")

        # ---- every rule refuses what it is meant to refuse -----------------------------
        for name, data, expect in REFUSALS:
            try:
                B.load_credits(write(tmp, data))
            except B.CardError as exc:
                got = str(exc)
                report(name, expect in got,
                       f"caught: {got.splitlines()[0][:70]}" if expect in got
                       else f"WRONG rule fired: {got.splitlines()[0][:70]}")
            else:
                report(name, False, "NOT caught; it was accepted")

        # ---- and stays quiet where silence is correct ----------------------------------
        c = B.load_credits(write(tmp, broken(
            film__credits=[{"role": "Written & produced", "names": ["A. Researcher"]},
                           {"role": "Music", "names": []},
                           {"role": "Sound", "names": ["", "  "]}])))
        roles = [r["role"] for r in c["film"]["rows"]]
        report("an unfilled role is dropped", roles == ["Written & produced"],
               f"kept {roles}")

        # ---- the image manifest, both ways --------------------------------------------
        (tmp / "EMPTY.md").write_text(MANIFEST_EMPTY, encoding="utf-8")
        (tmp / "FULL.md").write_text(MANIFEST_WITH_ROWS, encoding="utf-8")
        report("an empty manifest adds no row", B.images_row(tmp / "EMPTY.md") is None,
               "no row, which is right for a film that photographs nothing")

        row = B.images_row(tmp / "FULL.md")
        want = ["CC BY 4.0 — J. Photographer", "Public domain"]
        report("a manifest's licences reach the card", row is not None and row["names"] == want,
               f"got {row['names'] if row else None}")

        # ---- the fit model -------------------------------------------------------------
        # Two blocks of very different height. CSS grid gives the row the height of its
        # tallest item, so two columns cost the taller one, not the sum, and not the tallest
        # column's running total.
        tall = {"label": "TALL", "rows": [{"role": f"r{i}", "names": ["n"], "alt": ""}
                                          for i in range(6)]}
        short = {"label": "SHORT", "rows": [{"role": "r", "names": ["n"], "alt": ""}]}
        one, two = B.pack([tall, short], 1, 1920), B.pack([tall, short], 2, 1920)
        report("two columns cost the taller block", abs(two - B.block_height(tall, 792)) < 1.0,
               f"one column {one:.0f}px, two {two:.0f}px")

        # A name long enough to wrap must make its block taller. Underestimating here is what
        # would ship a card with the last credit cut off the bottom.
        shortn = {"label": "L", "rows": [{"role": "Music", "names": ["K. Salo"], "alt": ""}]}
        longn = {"label": "L", "rows": [{"role": "Music", "names": [
            "A Very Long Track Title Indeed, by K. Salo, licensed CC BY 4.0"], "alt": ""}]}
        report("a wrapping credit is counted",
               B.block_height(longn, 792) > B.block_height(shortn, 792) + 20,
               f"{B.block_height(shortn, 792):.0f}px -> {B.block_height(longn, 792):.0f}px")

        # ---- overflow refuses rather than quietly adding a card ------------------------
        crowded = broken(film__credits=[{"role": f"Role number {i}", "names": [f"Person {i}"]}
                                        for i in range(14)],
                         project__credits=[{"role": f"Build role {i}", "names": [f"Maker {i}"]}
                                           for i in range(14)])
        try:
            B.build(write(tmp, crowded), tmp / "over.html", 1920, 1080, 1, None)
        except B.CardError as exc:
            report("too many credits refuses", "--pages" in str(exc),
                   "refused and said to pass --pages" if "--pages" in str(exc)
                   else f"refused for the wrong reason: {exc}")
        else:
            report("too many credits refuses", False, "NOT caught; it built anyway")

        # ...and too few pages refuses too, naming the number that would actually do it,
        # rather than quietly dropping the credits that did not fit.
        try:
            B.build(write(tmp, crowded), tmp / "short.html", 1920, 1080, 2, None)
        except B.CardError as exc:
            report("too few pages refuses", "need 3 cards" in str(exc),
                   f"caught: {exc}" if "need 3 cards" in str(exc)
                   else f"refused without saying how many are needed: {exc}")
        else:
            report("too few pages refuses", False, "NOT caught; it built anyway")

        # ...and with enough of them, the sections split across cards -- including a section
        # too long for one card, which is the case pagination exists for.
        try:
            made = B.build(write(tmp, crowded), tmp / "split.html", 1920, 1080, 3, None)
            durations = [
                float(p.read_text(encoding="utf-8")
                      .split('data-om-exportable-video-with-duration-secs="')[1].split('"')[0])
                for p in made]
            cont = sum("(cont.)" in p.read_text(encoding="utf-8") for p in made)
            report("--pages splits a long section",
                   len(made) == 3 and abs(sum(durations) - 6.0) < 0.01 and cont >= 1,
                   f"{len(made)} cards, {durations}s total 6s, {cont} carry a continuation")
        except B.CardError as exc:
            report("--pages splits a long section", False, f"refused: {exc}")

        # ---- the byline moves the film's roles; it does not copy them ------------------
        # A byline that also left a "This film" block behind would credit the same person
        # twice on one card, which is the failure this is here to hold shut.
        bl = B.load_credits(write(tmp, broken(mode="standalone", project=None,
                                              film__byline=True)))
        labels = [b["label"] for b in B.sections_of(bl)]
        report("a byline empties the film block", not any("This film" in l for l in labels),
               f"sections are {labels}")
        report("a byline still keeps the rows", len(bl["film"]["rows"]) == 2,
               f"{len(bl['film']['rows'])} roles are available to set on the line")

        # ...and a card whose only credit is a byline builds. sections_of() returns nothing
        # for it, which without the byline would be "nothing to credit".
        try:
            B.build(write(tmp, broken(mode="standalone", project=None, sources=[],
                                      supervision=[], film__byline=True,
                                      film__credits=[{"role": "Created by",
                                                      "names": ["A. Researcher"]}])),
                    tmp / "byline.html", 1920, 1080, 1, None)
            html = (tmp / "byline.html").read_text(encoding="utf-8")
            ok = 'class="byline"' in html and 'class="block"' not in html
            report("a byline-only card builds", ok,
                   "the byline carries the credit and no block is rendered" if ok
                   else "built, but the byline or the empty grid is wrong")
        except B.CardError as exc:
            report("a byline-only card builds", False, f"refused: {exc}")

        # ...but not one long enough to be a credits block in disguise.
        try:
            B.build(write(tmp, broken(mode="standalone", project=None, film__byline=True,
                                      film__credits=[{"role": f"Long role name {i}",
                                                      "names": [f"Somebody Person {i}"]}
                                                     for i in range(6)])),
                    tmp / "longbyline.html", 1920, 1080, 1, None)
        except B.CardError as exc:
            report("an overlong byline refuses", "wearing a hat" in str(exc),
                   f"caught: {str(exc).splitlines()[0][:70]}" if "wearing a hat" in str(exc)
                   else f"refused for the wrong reason: {exc}")
        else:
            report("an overlong byline refuses", False, "NOT caught; it built anyway")

        # ---- a showcase takes its room out of the credits' budget ----------------------
        (tmp / "still.png").write_bytes(PNG_1PX)
        plain = B.load_credits(write(tmp, GOOD))
        withimg = B.load_credits(write(tmp, broken(film__image="still.png")))
        B.prepare_link(plain)
        B.prepare_link(withimg)
        b0 = B.credits_budget(plain, 1920, 1080)
        b1 = B.credits_budget(withimg, 1920, 1080)
        report("a still costs the credits their room", b1 < b0 - 200,
               f"{b0:.0f}px of credits room becomes {b1:.0f}px")

        # A missing still is a refusal, not a hole in the card. check_card.py would catch a
        # 404 at render time; catching it here says which field is wrong.
        try:
            B.build(write(tmp, broken(film__image="not-there.png")),
                    tmp / "missing.html", 1920, 1080, 1, None)
        except B.CardError as exc:
            report("a missing still refuses", "film.image not found" in str(exc),
                   f"caught: {str(exc)[:70]}")
        else:
            report("a missing still refuses", False, "NOT caught; it built anyway")

        # ---- one address, written twice, is printed once -------------------------------
        report("the same address is recognised",
               B.same_target("https://example.org/cooling-loop/", "example.org/cooling-loop"),
               "a scheme and a trailing slash do not make it a second place")
        report("a different address is not",
               not B.same_target("https://example.org/other", "example.org/cooling-loop"),
               "two real destinations stay two")

        # ---- the QR code, if segno is here ---------------------------------------------
        try:
            import segno  # noqa: F401
        except ModuleNotFoundError:
            skipped.append("QR code cases (segno is not installed)")
        else:
            linked = B.load_credits(write(tmp, broken(
                link={"label": "The project", "url": "https://example.org/other"})))
            B.prepare_link(linked)
            uri, px = linked["link"]["_qr_data"], linked["link"]["_qr_px"]
            svg = base64.b64decode(uri.split(",", 1)[1]).decode("ascii")
            report("the QR is inlined, not fetched",
                   uri.startswith("data:image/svg+xml;base64,") and "<svg" in svg,
                   "an SVG data URI, so nothing is fetched at render time")
            report("the QR is drawn on whole pixels", f'width="{px}"' in svg and px % 1 == 0,
                   f"{px}px, an exact multiple of its module count")
            report("a link elsewhere is printed as text", linked["link"]["_show_url"],
                   "the rail shows the address because the footer's is a different place")

            dupe = B.load_credits(write(tmp, broken(
                link={"label": "The project", "url": "https://example.org/cooling-loop"})))
            B.prepare_link(dupe)
            report("the contact's address is not printed twice", not dupe["link"]["_show_url"],
                   "the rail keeps the code, the footer keeps the text")

        # ---- the footer does not print the institution twice ---------------------------
        same = B.load_credits(write(tmp, GOOD))
        report("a wordmark suppresses the repeat", B.identity_already_named(same),
               "identity and responsible party are the same, so the stamp drops the name")
        diff = B.load_credits(write(tmp, broken(
            accountability__responsible="Somebody Else Entirely")))
        report("a different responsible party is shown",
               not B.identity_already_named(diff), "the stamp keeps the name")

    print()
    for why in skipped:
        print(f"SKIP  {why}")
    print("ALL PASS" if not bad else f"{bad} CASE(S) FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
