#!/usr/bin/env python3
"""Build an authorship end card from a credits file.

    python build_card.py credits.json --out card.html
    python build_card.py credits.json --out card.html --image-manifest ../images/MANIFEST.md
    python build_card.py credits.json --out card.html --pages 2

One self-contained HTML file, nothing fetched at render time: the fonts are spliced in as
inlined woff2 and a logo is embedded as a data URI. Feed the result to check_card.py, then
to render_card.py.

Two things this script will not do, both on purpose:

  It will not silently lengthen the film. When the credits do not fit on one card it escalates
  from one column to two, which is only layout. When two columns still overflow it FAILS and
  tells you to pass --pages, because a second card adds seconds to the film, and the film's
  length is an audio decision taken at the gate where the mix is approved -- not a side effect
  of someone adding a name.

  It will not invent a credit. A role with no names is dropped, a section with no rows is not
  rendered, and there are no default values anywhere. A card can be wrong by omission, which
  someone will notice; a card that quietly credits "-" for Music is wrong in a way nobody can
  see.

A card may also carry a representative still from the film and a QR code to where the
viewer goes next. Both are optional and both are off unless the credits file asks; a card
with neither renders exactly as it did before they existed. The still takes the room the
credits do not want, so it is largest on the card that needs it most -- the one with two
names on it.

The composition font floor is 28px and this card obeys it, which is why it carries no fine
print. Fewer and larger credits, or another page. Never smaller type.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import mimetypes
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "card.template.html"
FONTS = HERE / "fonts.css"

# ---------------------------------------------------------------------------------------
# Geometry. Every constant here mirrors a rule in card.template.html; changing one there
# without changing it here makes the fit estimate lie, and the overflow then surfaces in
# check_card.py instead. That is the intended order: cheap arithmetic guesses, the browser
# decides.
# ---------------------------------------------------------------------------------------

PAD_TOP, PAD_BOTTOM = 76, 64
PAD_X = 120
FLOOR = 28                      # the shared composition font floor

KICKER_H = FLOOR * 1.2
TITLE_SIZE, TITLE_LH = 58, 1.08
TITLE_MT = 16
TITLE_ALT_H = 34 * 1.25 + 8
RULE_H = 24 + 8 + 30
BYLINE_MT = 18
BYLINE_SIZE = 36
BYLINE_LH = BYLINE_SIZE * 1.25
BYLINE_SEP = "  ·  "              # what joins two roles on one byline
BYLINE_MAX_LINES = 2                   # past this it is a credits block wearing a hat

BLOCK_LABEL_LH = FLOOR * 1.2
BLOCK_LABEL_CHROME = 10 + 1 + 14               # padding-bottom + border + margin-bottom
BLOCK_GAP = 26                                 # the grid's row-gap

ROLE_W = 340                                   # the role column, from .row's grid template
ROW_GAP_X = 28                                 # .row column-gap
COL_GAP = 96                                   # .credits column-gap
NAME_LH = 32 * 1.3
ROLE_LH = FLOOR * 1.35
ROW_MB = 8
ROW_ALT_H = FLOOR * 1.3                        # the optional second-language line

DISCLOSURE_LH = FLOOR * 1.42
DISCLOSURE_CHROME = 20 + 16 + 16               # margin-top + vertical padding

FOOTER_CHROME = 18 + 20 + 1                    # margin-top + padding-top + border
STAMP_LH = FLOOR * 1.38
WORDMARK_LH = FLOOR * 1.35
PLATE_PAD = 28

SHOWCASE_MT = 30                               # .showcase margin-top
SHOWCASE_GAP = 64                              # .showcase column-gap
LINKOUT_W = 420                                # the QR rail's width, from .linkout
LINKOUT_GAP = 14                               # .linkout and .still row-gap
LINK_LH = FLOOR * 1.35
STILL_MIN = 240                                # the least room a still is worth showing in

# The QR code. QR_TARGET is what is wanted, not what is used: the code is drawn at a whole
# number of pixels per module, so the real size is the nearest multiple of the module count.
# QR_BORDER is the quiet zone the spec requires and a scanner uses to find the code at all.
QR_TARGET = 260
QR_BORDER = 4
QR_ERROR = "m"                                 # ~15% recovery
QR_DARK, QR_LIGHT = "#0F0F11", "#FFFFFF"

# Rough advance width, as a fraction of the font size. Only used to guess how many lines a
# string wraps to; a wrong guess costs a re-run, not a bad card. The tracked variant is for
# the uppercase mono labels, which carry .14em of letter-spacing on top of the advance.
EM_SANS = 0.52
EM_MONO = 0.60
EM_MONO_TRACKED = EM_MONO + 0.14

SECTIONS = [
    ("film", "This film"),
    ("project", "The project"),
    ("sources", "Sources & data"),
    ("supervision", "Supervision"),
]


class CardError(Exception):
    """A credits file that cannot honestly produce a card."""


# ---------------------------------------------------------------------------------------
# Reading and validating
# ---------------------------------------------------------------------------------------

def _rows(raw, where: str) -> list[dict]:
    """Normalise a credit list, dropping rows nobody filled in."""
    out = []
    for i, row in enumerate(raw or []):
        if not isinstance(row, dict):
            raise CardError(f"{where}[{i}] is not an object with 'role' and 'names'")
        role = (row.get("role") or "").strip()
        names = [str(n).strip() for n in (row.get("names") or []) if str(n).strip()]
        alt = (row.get("alt") or "").strip()
        if not names:
            continue                      # an unfilled role is omitted, never defaulted
        if not role:
            raise CardError(f"{where}[{i}] has names but no role: {names}")
        out.append({"role": role, "names": names, "alt": alt})
    return out


def load_credits(path: Path, image_manifest: Path | None = None) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CardError(f"{path.name} is not valid JSON: {exc}") from exc

    mode = (data.get("mode") or "").strip().lower()
    if mode not in ("project", "standalone"):
        raise CardError("mode must be 'project' (the film is about a project, so the people "
                        "who built it get credited too) or 'standalone' (everything the film "
                        "needs is the film's own)")

    film = data.get("film") or {}
    if not (film.get("title") or "").strip():
        raise CardError("film.title is required")
    film_rows = _rows(film.get("credits"), "film.credits")
    if not film_rows:
        raise CardError("film.credits must name at least one person -- a card that credits "
                        "nobody for the film has no reason to exist")

    project = data.get("project") or {}
    project_rows = _rows(project.get("credits"), "project.credits")
    if mode == "project":
        if not (project.get("name") or "").strip():
            raise CardError("mode is 'project', so project.name is required")
        if not project_rows:
            raise CardError("mode is 'project', so project.credits must name at least one "
                            "person. A film about a project that credits only its film-makers "
                            "takes credit for someone else's work")
    elif project_rows or (project.get("name") or "").strip():
        raise CardError("mode is 'standalone' but a project block is filled in. Set mode to "
                        "'project', or remove the block")

    byline = bool(film.get("byline"))

    image = (film.get("image") or "").strip()
    image_credit = (film.get("image_credit") or "").strip()
    if image_credit and not image:
        raise CardError("film.image_credit carries an attribution for an image that is not "
                        "on the card. Set film.image, or drop the credit")

    link = data.get("link") or {}
    link_url = (link.get("url") or "").strip()
    link_label = (link.get("label") or "").strip()
    if link and not link_url:
        raise CardError("link is present but link.url is empty. A QR code that goes nowhere "
                        "is worse than none: a viewer scanning it cannot tell it failed")
    if link_url and not link_label:
        raise CardError("link.label is required: say what a viewer gets for scanning it. "
                        "The code itself says nothing, and nobody scans an unlabelled square")

    sources = _rows(data.get("sources"), "sources")
    if image_manifest is not None:
        row = images_row(image_manifest)
        if row and not any(r["role"].lower().startswith("image") for r in sources):
            sources.append(row)

    disclosure = (data.get("disclosure") or "").strip()
    if not disclosure:
        raise CardError("disclosure is required. Say what in this film was generated -- the "
                        "narration, the picture, the script -- and what made it. A film that "
                        "carries a synthetic voice without saying so is the thing this card "
                        "exists to prevent")

    acc = data.get("accountability") or {}
    if not (acc.get("responsible") or "").strip():
        raise CardError("accountability.responsible is required: who stands behind the claims")
    if not (acc.get("contact") or "").strip():
        raise CardError("accountability.contact is required: where a viewer takes a correction")

    return {
        "mode": mode,
        "film": {"title": film["title"].strip(),
                 "title_alt": (film.get("title_alt") or "").strip(),
                 "kind": (film.get("kind") or "").strip(),
                 "year": str(film.get("year") or "").strip(),
                 "image": image,
                 "image_credit": image_credit,
                 "byline": byline,
                 "rows": film_rows},
        "project": {"name": (project.get("name") or "").strip(), "rows": project_rows},
        "sources": sources,
        "supervision": _rows(data.get("supervision"), "supervision"),
        "disclosure": disclosure,
        "funding": (data.get("funding") or "").strip(),
        "accountability": {"responsible": acc["responsible"].strip(),
                           "contact": acc["contact"].strip()},
        "link": {"label": link_label, "url": link_url},
        "identity": dict(data.get("identity") or {}),
        "duration_s": float(data.get("duration_s") or 6.0),
    }


def images_row(manifest: Path) -> dict | None:
    """Lift licence and attribution out of a GATE 4 image manifest.

    The attribution strings are recorded there and, until now, never reached the screen. For a
    CC-BY image that is not a nicety: the licence requires the credit to appear where the work
    appears. An empty manifest produces no row, which is the correct answer for a film that
    photographs nothing.
    """
    if not manifest.exists():
        raise CardError(f"image manifest not found: {manifest}")
    lines = [ln.strip() for ln in manifest.read_text(encoding="utf-8").splitlines()
             if ln.strip().startswith("|")]
    if len(lines) < 3:
        return None
    header = [c.strip().lower() for c in lines[0].strip("|").split("|")]
    lic = next((i for i, c in enumerate(header) if "licen" in c), None)
    if lic is None:
        return None
    att = next((i for i, c in enumerate(header) if "attribut" in c), None)

    seen, names = set(), []
    for line in lines[2:]:                       # skip the |---| separator
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) <= lic:
            continue
        licence = cells[lic]
        who = cells[att] if att is not None and len(cells) > att else ""
        if not licence or licence in {"-", "—"}:
            continue
        text = f"{licence} — {who}" if who and who not in {"-", "—"} else licence
        if text not in seen:
            seen.add(text)
            names.append(text)
    return {"role": "Images", "names": names, "alt": ""} if names else None


# ---------------------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------------------

def wrapped(text: str, size: float, width: float, em: float = EM_SANS) -> int:
    per_line = max(1, int(width / (size * em)))
    return max(1, math.ceil(len(text) / per_line))


def sections_of(c: dict) -> list[dict]:
    out = []
    for key, label in SECTIONS:
        if key == "film":
            # Moved to the header, not copied: a byline that also left a block behind
            # would credit the same person twice on one card.
            rows = [] if c["film"]["byline"] else c["film"]["rows"]
        elif key == "project":
            rows = c["project"]["rows"]
        else:
            rows = c[key]
        if not rows:
            continue
        title = label
        if key == "project" and c["project"]["name"]:
            title = f"{label} — {c['project']['name']}"
        out.append({"label": title, "rows": rows})
    return out


def byline_pairs(c: dict) -> list[tuple[str, str]]:
    """The film's credits as (role, names), ready to set on one line."""
    return [(r["role"], ", ".join(r["names"])) for r in c["film"]["rows"]]


def byline_lines(c: dict, width: int) -> int:
    if not c["film"]["byline"]:
        return 0
    text = BYLINE_SEP.join(f"{role}  {names}" for role, names in byline_pairs(c))
    return wrapped(text, BYLINE_SIZE, width - 2 * PAD_X)


def byline_height(c: dict, width: int) -> float:
    if not c["film"]["byline"]:
        return 0.0
    return BYLINE_MT + byline_lines(c, width) * BYLINE_LH


def column_width(width: int, cols: int) -> float:
    return ((width - 2 * PAD_X) - COL_GAP * (cols - 1)) / cols


def block_height(block: dict, col_w: float) -> float:
    """How tall one credit block renders in a column of the given width.

    Wrapping is counted, not assumed away: a name long enough to take two lines -- a music
    track with its licence, an institution with its department -- makes the block taller,
    and a model that ignored that would underestimate, which is the direction that ships a
    card with the last credit cut off the bottom.
    """
    names_w = max(120.0, col_w - ROLE_W - ROW_GAP_X)
    h = BLOCK_LABEL_LH * wrapped(block["label"], FLOOR, col_w, EM_MONO_TRACKED) \
        + BLOCK_LABEL_CHROME
    for row in block["rows"]:
        name_lines = sum(wrapped(n, 32, names_w, EM_SANS) for n in row["names"])
        role_lines = wrapped(row["role"], FLOOR, ROLE_W, EM_MONO)
        h += max(name_lines * NAME_LH, role_lines * ROLE_LH) + ROW_MB
        if row["alt"]:
            h += ROW_ALT_H
    return h


def pack(blocks: list[dict], cols: int, width: int) -> float:
    """Height of the credits grid when blocks are laid out in `cols` columns.

    CSS grid places items row-major and gives each implicit row the height of its tallest
    item, so the total is the sum of row maxima plus the gaps between rows -- not the height
    of the tallest column. Modelling it as columns overestimates a balanced layout and
    underestimates a lopsided one, and the second of those is the direction that hurts.
    """
    col_w = column_width(width, cols)
    total = 0.0
    rows = [blocks[i:i + cols] for i in range(0, len(blocks), cols)]
    for i, row in enumerate(rows):
        total += max(block_height(b, col_w) for b in row) + (BLOCK_GAP if i else 0)
    return total


def identity_already_named(c: dict) -> bool:
    """True when the wordmark on the left already carries the responsible party's name."""
    ident = c["identity"]
    return (not ident.get("logo")
            and (ident.get("name") or "").strip().casefold()
            == c["accountability"]["responsible"].strip().casefold())


def has_showcase(c: dict) -> bool:
    """Whether this card carries a still, a QR code, or both."""
    return bool(c["film"]["image"] or c["link"]["url"])


def showcase_height(c: dict, width: int) -> float:
    """The room the showcase takes, and therefore the room the credits do not get.

    Reserved rather than measured. Without it choose_layout would hand the whole card to
    the credits, the still would be flattened to nothing by its own max-height, and the
    only sign of it would be a card that looks wrong in the browser -- which is the check
    doing the build script's job.

    The still gets a floor, not a share: STILL_MIN is the smallest a frame can be and still
    be worth putting on screen. When the credits leave more than that, the flex layout gives
    it away for free and this estimate is simply conservative, which is the safe direction.
    """
    if not has_showcase(c):
        return 0.0

    rail = 0.0
    if c["link"]["url"]:
        rail = (c["link"]["_qr_px"] + LINKOUT_GAP
                + wrapped(c["link"]["label"], FLOOR, LINKOUT_W, EM_MONO_TRACKED) * LINK_LH)
        if c["link"].get("_show_url"):
            rail += LINKOUT_GAP + wrapped(c["link"]["url"], FLOOR, LINKOUT_W,
                                          EM_MONO) * LINK_LH

    still = 0.0
    if c["film"]["image"]:
        still = STILL_MIN
        if c["film"]["image_credit"]:
            room = width - 2 * PAD_X
            if c["link"]["url"]:
                room -= LINKOUT_W + SHOWCASE_GAP
            still += LINKOUT_GAP + wrapped(c["film"]["image_credit"], FLOOR,
                                           max(200.0, room)) * LINK_LH

    return SHOWCASE_MT + max(rail, still)


def credits_budget(c: dict, width: int, height: int) -> float:
    """The vertical room left for credits once the fixed furniture has taken its share."""
    inner = width - 2 * PAD_X
    head = (KICKER_H + TITLE_MT
            + wrapped(c["film"]["title"], TITLE_SIZE, inner) * TITLE_SIZE * TITLE_LH
            + RULE_H)
    if c["film"]["title_alt"]:
        head += TITLE_ALT_H
    head += byline_height(c, width)
    disc = DISCLOSURE_CHROME + wrapped(c["disclosure"], FLOOR, inner - 26) * DISCLOSURE_LH

    ident, half = c["identity"], inner / 2
    has_logo = bool(ident.get("logo"))
    stamp_lines = wrapped("Responsible for this content", FLOOR, half, EM_MONO_TRACKED)
    if not identity_already_named(c):
        stamp_lines += wrapped(c["accountability"]["responsible"], FLOOR, half)
    if c["funding"] and has_logo:
        stamp_lines += wrapped(c["funding"], FLOOR, half)
    stamp_lines += wrapped(c["accountability"]["contact"], FLOOR, half, EM_MONO)

    if has_logo:
        left = int(ident.get("logo_height") or 56) + PLATE_PAD
    else:
        left = WORDMARK_LH * (bool(ident.get("name")) + bool(ident.get("name_alt"))
                              + bool(c["funding"]))
    foot = FOOTER_CHROME + max(stamp_lines * STAMP_LH, left)
    return ((height - PAD_TOP - PAD_BOTTOM) - head - disc - foot
            - showcase_height(c, width))


def split_block(block: dict, col_w: float, budget: float) -> list[dict]:
    """Break one over-tall section into continuation sections that each fit a card.

    A section is the thing that usually overflows -- fourteen people who built the hardware
    is one section, not fourteen -- so pagination that could only split *between* sections
    would refuse exactly the list it exists to carry.
    """
    out: list[dict] = []
    cur: list[dict] = []

    def flush() -> None:
        if cur:
            label = block["label"] if not out else f"{block['label']} (cont.)"
            out.append({"label": label, "rows": list(cur)})

    for row in block["rows"]:
        if cur and block_height({"label": block["label"], "rows": cur + [row]},
                                col_w) > budget:
            flush()
            cur = [row]
        else:
            cur.append(row)
    flush()
    return out or [block]


def paginate(blocks: list[dict], cols: int, width: int, budget: float) -> list[list[dict]]:
    """Lay the sections onto as few cards as they will fit on."""
    col_w = column_width(width, cols)
    units: list[dict] = []
    for b in blocks:
        units += (split_block(b, col_w, budget) if block_height(b, col_w) > budget else [b])

    pages: list[list[dict]] = []
    cur: list[dict] = []
    for u in units:
        if cur and pack(cur + [u], cols, width) > budget:
            pages.append(cur)
            cur = [u]
        else:
            cur.append(u)
    if cur:
        pages.append(cur)
    return pages


def choose_layout(c: dict, width: int, height: int, pages: int) -> tuple[int, list[list[dict]]]:
    """Return (columns, one section list per card), or raise if it will not fit."""
    budget = credits_budget(c, width, height)
    blocks = sections_of(c)
    if not blocks and not c["film"]["byline"]:
        raise CardError("nothing to credit: every section is empty")
    if byline_lines(c, width) > BYLINE_MAX_LINES:
        raise CardError(
            f"film.byline runs to {byline_lines(c, width)} lines, and a byline past "
            f"{BYLINE_MAX_LINES} is a credits block wearing a hat. Drop film.byline and "
            f"let these roles be a block, or move all but the author into another section.")
    if budget <= 0:
        raise CardError(
            f"the fixed furniture already fills the card: no room is left for one credit.\n"
            f"  The showcase reserves about {showcase_height(c, width):.0f}px, and the\n"
            f"  disclosure and the footer take what is left. Drop film.image, drop the\n"
            f"  link, or shorten the disclosure -- do not shrink the type.")

    # One card is the ordinary answer, and one column is the better-looking one, so both are
    # tried in that order before anything is allowed to get longer or busier.
    for cols in (1, 2):
        if pack(blocks, cols, width) <= budget:
            return cols, [blocks]

    if pages <= 1:
        over = pack(blocks, 2, width) - budget
        needed = len(paginate(blocks, 2, width, budget))
        raise CardError(
            f"the credits overflow one card by about {over:.0f}px even in two columns.\n"
            f"  Pass --pages {needed} to split them across {needed}, or shorten the list.\n"
            f"  This is not done for you because another card adds seconds to the film, and\n"
            f"  the film's length is settled where the mix is approved, not here.")

    # Past one card, two columns is what keeps the card count down, so it goes first.
    for cols in (2, 1):
        split = paginate(blocks, cols, width, budget)
        if len(split) <= pages:
            return cols, split
    needed = len(paginate(blocks, 2, width, budget))
    raise CardError(f"these credits need {needed} cards and you allowed {pages}. "
                    f"Pass --pages {needed}, or shorten the list.")


# ---------------------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------------------

def e(s) -> str:
    return html.escape(str(s), quote=True)


def render_rows(rows: list[dict]) -> str:
    out = []
    for row in rows:
        names = "<br>".join(e(n) for n in row["names"])
        alt = f'<span class="alt">{e(row["alt"])}</span>' if row["alt"] else ""
        out.append(f'      <div class="row"><div class="role">{e(row["role"])}</div>'
                   f'<div class="names">{names}{alt}</div></div>')
    return "\n".join(out)


def render_content(c: dict, page_blocks: list[dict], cols: int, page: int, pages: int) -> str:
    f = c["film"]
    kicker = " · ".join(x for x in (f["kind"], f["year"]) if x)
    parts = ["  <header>"]
    if kicker:
        parts.append(f'    <div class="kicker">{e(kicker)}</div>')
    parts.append(f'    <h1 class="title">{e(f["title"])}</h1>')
    if f["title_alt"]:
        parts.append(f'    <div class="title-alt">{e(f["title_alt"])}</div>')
    if f["byline"]:
        bits = []
        for i, (role, names) in enumerate(byline_pairs(c)):
            if i:
                bits.append('<span class="sep">·</span>')
            bits.append(f'<span class="pair"><span class="role">{e(role)}</span>'
                        f'<span class="who">{e(names)}</span></span>')
        parts.append('    <div class="byline">' + "".join(bits) + "</div>")
    parts.append('    <div class="rule"></div>')
    parts.append("  </header>")

    if pages > 1:
        parts.append(f'  <div class="page-of">{page} / {pages}</div>')

    parts.append(f'  <div class="credits" data-cols="{cols}">')
    for b in page_blocks:
        parts.append('    <section class="block">')
        parts.append(f'      <div class="block-label">{e(b["label"])}</div>')
        parts.append(render_rows(b["rows"]))
        parts.append("    </section>")
    parts.append("  </div>")

    # The showcase repeats on every page for the same reason the disclosure does, and for
    # one more: credits_budget subtracts its room from every page's budget, so a showcase
    # that appeared on only one of them would make the estimate wrong about the others.
    if has_showcase(c):
        link = c["link"]
        parts.append('  <div class="showcase">')
        if f.get("_image_data"):
            parts.append('    <div class="still">')
            parts.append(f'      <div class="frame"><img src="{f["_image_data"]}" '
                         f'alt="{e(f["title"])}"></div>')
            if f["image_credit"]:
                parts.append(f'      <div class="credit">{e(f["image_credit"])}</div>')
            parts.append("    </div>")
        if link["url"]:
            parts.append('    <div class="linkout">')
            parts.append(f'      <div class="label">{e(link["label"])}</div>')
            parts.append(f'      <div class="qr"><img src="{link["_qr_data"]}" '
                         f'alt="{e(link["url"])}"></div>')
            if link.get("_show_url"):
                parts.append(f'      <div class="url">{e(link["url"])}</div>')
            parts.append("    </div>")
        parts.append("  </div>")

    # The disclosure and the identity repeat on every page. They are the two things a viewer
    # must not be able to miss by looking away for four seconds.
    parts.append(f'  <div class="disclosure">{e(c["disclosure"])}</div>')

    ident = c["identity"]
    responsible = c["accountability"]["responsible"]
    parts.append("  <footer>")
    if ident.get("_logo_data"):
        parts.append(f'    <div class="plate"><img src="{ident["_logo_data"]}" '
                     f'alt="{e(ident.get("name", ""))}"></div>')
    elif ident.get("name"):
        bits = [e(ident["name"])]
        if ident.get("name_alt"):
            bits.append(f'<span class="alt">{e(ident["name_alt"])}</span>')
        if c["funding"]:
            bits.append(f'<span class="funding">{e(c["funding"])}</span>')
        parts.append(f'    <div class="wordmark">{"".join(bits)}</div>')

    # Naming the institution on the left and again on the right reads as a mistake, not as
    # a second fact. When a wordmark is already carrying the name, the stamp drops to its
    # label and its contact; a logo is a mark rather than a sentence, so the name stays.
    already_named = (not ident.get("_logo_data")
                     and (ident.get("name") or "").strip().casefold()
                     == responsible.strip().casefold())
    stamp = ['<span class="label">Responsible for this content</span>']
    if not already_named:
        stamp.append(f'<span class="who">{e(responsible)}</span>')
    if c["funding"] and ident.get("_logo_data"):
        stamp.append(f'<span class="who">{e(c["funding"])}</span>')
    stamp.append(f'<span class="contact">{e(c["accountability"]["contact"])}</span>')
    parts.append('    <div class="stamp">' + "".join(stamp) + "</div>")
    parts.append("  </footer>")
    return "\n".join(parts)


def data_uri(src: str, base: Path, what: str) -> str:
    """One file beside the credits file, inlined. Nothing is fetched at render time, so
    every image on the card has to arrive this way."""
    p = Path(src) if Path(src).is_absolute() else (base / src)
    if not p.exists():
        raise CardError(f"{what} not found: {p}")
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def embed_logo(c: dict, base: Path) -> None:
    """Inline the logo, and suppress the wordmark when one is present.

    An institutional lockup already carries the institution's name, usually in two languages.
    Printing the name again beside it reads as a mistake, so the logo replaces the wordmark
    rather than joining it.
    """
    if c["identity"].get("logo"):
        c["identity"]["_logo_data"] = data_uri(c["identity"]["logo"], base, "identity.logo")


def embed_still(c: dict, base: Path) -> None:
    """Inline the representative frame, if the film named one."""
    if c["film"]["image"]:
        c["film"]["_image_data"] = data_uri(c["film"]["image"], base, "film.image")


def qr_svg(url: str) -> tuple[str, int]:
    """The link as a QR code: a data URI, and the exact pixel size to draw it at.

    Built here and inlined, for the same reason the fonts are: nothing may be fetched at
    render time. A code pulled from a chart service would also hand that service the URL
    of every film anyone ever renders, which is not its business.

    The size is a whole number of modules times a whole number of pixels, never a round
    260. A code whose modules land on fractional pixels gets resampled by the browser,
    and the result looks right in a still and fails to scan off a compressed frame --
    which is the failure mode nobody catches by looking at the card.
    """
    try:
        import segno
    except ModuleNotFoundError as exc:
        raise CardError("this card has a link, so it needs a QR code, and segno is not "
                        "installed: python -m pip install segno") from exc
    code = segno.make(url, error=QR_ERROR, mode="byte")
    modules = code.symbol_size(scale=1, border=QR_BORDER)[0]
    scale = max(1, round(QR_TARGET / modules))
    buf = io.BytesIO()
    code.save(buf, kind="svg", scale=scale, border=QR_BORDER,
              dark=QR_DARK, light=QR_LIGHT, xmldecl=False, svgns=True, nl=False)
    return (f"data:image/svg+xml;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}",
            modules * scale)


def same_target(a: str, b: str) -> bool:
    """True when two written-out addresses point at the same place.

    The link-out and the accountability contact do different jobs -- one is where a viewer
    goes next, the other is where a correction goes -- but on a small project they are
    usually the same address, written once with a scheme and once without. Printing it
    twice on one card reads as a mistake, exactly as naming the institution twice does,
    so the rail keeps the code and the footer keeps the text.
    """
    def norm(s: str) -> str:
        s = s.strip().casefold()
        for scheme in ("https://", "http://"):
            if s.startswith(scheme):
                s = s[len(scheme):]
                break
        return s.removeprefix("www.").rstrip("/")
    return bool(a and b) and norm(a) == norm(b)


def prepare_link(c: dict) -> None:
    """Draw the QR, and decide whether its URL is worth printing as text as well."""
    link = c["link"]
    link["_qr_px"] = QR_TARGET
    if not link["url"]:
        return
    link["_qr_data"], link["_qr_px"] = qr_svg(link["url"])
    link["_show_url"] = not same_target(link["url"], c["accountability"]["contact"])


def build(credits_path: Path, out: Path, width: int, height: int, pages: int,
          image_manifest: Path | None, extra_fonts: Path | None = None) -> list[Path]:
    c = load_credits(credits_path, image_manifest)
    embed_logo(c, credits_path.parent)
    embed_still(c, credits_path.parent)
    prepare_link(c)
    cols, split = choose_layout(c, width, height, pages)

    template = TEMPLATE.read_text(encoding="utf-8")
    fonts = FONTS.read_text(encoding="utf-8")
    if extra_fonts is not None:
        if not extra_fonts.exists():
            raise CardError(f"--extra-fonts not found: {extra_fonts}")
        fonts += "\n" + extra_fonts.read_text(encoding="utf-8")
    per_page = round(c["duration_s"] / len(split), 3)

    written = []
    for i, blocks in enumerate(split, start=1):
        content = render_content(c, blocks, cols, i, len(split))
        page = (template
                .replace("/*__FONTS__*/", fonts)
                .replace("__TITLE__", e(c["film"]["title"] + " — credits"))
                .replace("__WIDTH__", str(width))
                .replace("__HEIGHT__", str(height))
                .replace("__COLS__", str(cols))
                .replace("__CARDCLASS__", "has-showcase" if has_showcase(c) else "")
                .replace("__QRPX__", str(int(c["link"]["_qr_px"])))
                .replace("__LOGOH__", str(int(c["identity"].get("logo_height") or 56)))
                .replace("__DURATION__", str(per_page))
                .replace("__CONTENT__", content))
        target = out if len(split) == 1 else out.with_name(f"{out.stem}-{i}{out.suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        written.append(target)

    plural = "" if len(written) == 1 else "s"
    print(f"built {len(written)} card{plural}, {cols} column{'' if cols == 1 else 's'}, "
          f"{per_page:g}s each, {width}x{height}")
    for w in written:
        print(f"  {w}")
    if c["film"]["byline"]:
        print(f"  byline: the film's {len(c['film']['rows'])} role(s) are above the rule, "
              f"on {byline_lines(c, width)} line(s), not in a credits block")
    if c["film"]["image"]:
        print(f"  still: {c['film']['image']}, at most "
              f"{width - 2 * PAD_X - (LINKOUT_W + SHOWCASE_GAP if c['link']['url'] else 0)}px wide")
    if c["link"]["url"]:
        print(f"  QR: {c['link']['_qr_px']}px, error correction "
              f"{QR_ERROR.upper()}, pointing at {c['link']['url']}")
        print("  scan that code off a rendered frame before the film ships:")
        print("  a code that survives a still and dies in H.264 looks perfect here.")
    print("  next: check_card.py, which is what actually decides whether it fits")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("credits", type=Path, help="the credits JSON for this film")
    ap.add_argument("--out", type=Path, required=True, help="output HTML path")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--pages", type=int, default=1,
                    help="allow the credits to run onto up to this many cards. It uses as "
                         "few as they fit on, and the declared duration is divided between "
                         "them, so the film gains no time it was not already given")
    ap.add_argument("--image-manifest", type=Path,
                    help="a GATE 4 MANIFEST.md; its licences become the Images row")
    ap.add_argument("--extra-fonts", type=Path,
                    help="a CSS file of extra @font-face rules, appended to the bundled two. "
                         "The bundled faces are Latin-only, so a card with Chinese, Japanese "
                         "or Korean text needs this or it renders in whatever the render "
                         "machine happens to have installed")
    args = ap.parse_args()
    try:
        build(args.credits, args.out, args.width, args.height, args.pages,
              args.image_manifest, args.extra_fonts)
    except CardError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
