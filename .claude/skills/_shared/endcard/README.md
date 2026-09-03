# The authorship end card

The standard closing slide for a film. It says who made the film, who built the thing the film
is about, what in it was generated, who is answerable for the claims, and where a viewer takes
a correction. One template, filled from a small data file, appended to every film.

It exists because a film made with these skills otherwise ends on its last narrated line and
carries no attribution at all — no author, no builders, no statement that the narration is
synthetic. The films carry real numbers to people who will believe them, and a viewer who
believes them is owed the name of whoever stands behind them.

```bash
python build_card.py credits.json --out card.html   # data  -> one self-contained page
python check_card.py card.html                      # the browser decides whether it fits
python render_card.py card.html --mp4 card.mp4      # -> the film's own encoder
python append_card.py --picture picture.mp4 --card card.mp4 --out picture+card.mp4
```

**Keep the credits file with the film, never here.** `_shared/` is replaced wholesale when the
skills update, so a credits file left in this folder is gone the first time somebody runs the
updater. `credits.example.json` is a worked example to copy out, not a place to edit.

## The two modes, which is the decision that matters

**`"mode": "project"` — the film is about something somebody built.** Then the card credits
the project's people as well as the film's, and refuses to build without them. A film about a
project that credits only its film-makers takes credit for someone else's work, so this is a
hard failure and not a warning.

**`"mode": "standalone"` — everything the film needs is the film's own.** An explainer about a
published standard, a method, an idea. The project block is not rendered, and filling one in
while claiming this mode is refused rather than silently ignored.

Getting the mode wrong is the one mistake with a victim, which is why the two are named
choices rather than something inferred from whether a field happens to be filled in.

## The fields

| field | | what it is |
|---|---|---|
| `mode` | **required** | `project` or `standalone` |
| `film.title` | **required** | the film's title, as it should be read |
| `film.title_alt` | | a second-language title, set under the first |
| `film.kind`, `film.year` | | the kicker line, e.g. `Explainer · 2026` |
| `film.credits` | **required** | who made the film. At least one row |
| `film.byline` | | set the film's credits above the rule instead of in a block |
| `film.image` | | a representative still, beside the credits file |
| `film.image_credit` | | one attribution line under that still |
| `project.name` | project mode | what the film is about |
| `project.credits` | project mode | who built it. At least one row |
| `sources` | | the source document, standards, datasets, images |
| `supervision` | | principal investigators, advisors |
| `disclosure` | **required** | what was generated, and what generated it |
| `funding` | | a grant or programme, if there is one |
| `accountability.responsible` | **required** | who stands behind the claims |
| `accountability.contact` | **required** | where a viewer takes a correction |
| `identity.name`, `.name_alt` | | the institution, in one or two languages |
| `identity.logo`, `.logo_height` | | a logo file beside the credits file |
| `link.url`, `link.label` | | where the viewer goes next: a QR code, and its address |
| `duration_s` | | how long the card holds. 6 seconds by default |

A credit row is `{"role": …, "names": [ … ], "alt": …}`. `alt` is the second-language line under
the names — a Chinese name under a Latin one.

**A role with nobody in it is dropped, not defaulted.** Keep every role you might use in the
file; the unfilled ones vanish. There is no `"—"` anywhere and there never should be: a card
can be wrong by omission, which someone will notice, but a card that quietly credits a dash for
Music is wrong in a way nobody can see.

### The disclosure is required, and it is the point

Say what was generated and what generated it — the narration, the picture, the script. A film
that carries a synthetic voice without saying so is the thing this card exists to prevent, and
the lab's acceptable-use statement asks for exactly this. It is a required field so that it
cannot be dropped by someone in a hurry.

### The closing-frame card: a byline, a still, and a QR code

A film whose credits are one name does not want a credits block. `"byline": true` on the
`film` block sets those roles on one line under the title, above the rule, where a byline
belongs — and the space they were using goes to the still:

```json
"film": {
  "title": "How to Make an Explainer",
  "credits": [{"role": "Created by", "names": ["A. Researcher"]}],
  "byline": true,
  "image": "still.png",
  "image_credit": "Frame from the film"
},
"link": {"label": "The lab's page for this project", "url": "https://example.org/project"}
```

**The roles are moved, not copied.** A byline that also left a block behind would credit the
same person twice, so the `This film` block is not rendered at all when it is on. Everything
that made a credits block honest still holds: `check_card.py` reads the byline for a role with
nobody in it exactly as it reads a row, and a card with neither a row nor a byline still fails
as crediting nobody. Past two lines the build refuses — a byline with six roles on it is a
credits block wearing a hat, and the block is the better answer.

**The still is height-bound, not width-bound.** Its box is as tall as the credits leave, and a
16:9 frame cannot use the width that remains, so it sits on the card's left edge with the rail
at the right. `object-fit: contain`, never `cover`: cropping somebody's frame to fill a box is
a decision the card does not get to make on its own.

**The link is not the accountability contact**, even when they are the same address. One is
where a viewer goes next; the other is where a correction goes. When the two point at the same
place the rail keeps the code and drops the text, because printing one URL twice on one card
reads as a mistake — the same reasoning that suppresses a repeated wordmark.

`link.label` is required whenever there is a link. Nobody scans an unlabelled square, and the
code itself says nothing about where it goes.

### The QR code needs segno, and your phone

```bash
python -m pip install segno
```

Only needed when a card has a link. It is generated at build time and inlined as an SVG data
URI, because nothing may be fetched at render time — and because a code pulled from a chart
service would hand that service the URL of every film anybody renders.

The code is drawn at a whole number of pixels per module rather than a round 260px, so the
browser never resamples it. That matters more than it sounds: a resampled code looks perfect
in a still and fails to scan off a compressed frame.

**Scan it off a rendered frame before the film ships.** Your phone is the bench here, the same
way your ears are the bench for the mix — a code that survives the PNG and dies in H.264 is
invisible to every check in this folder. At 259px with error correction M it has been decoded
out of the exporter's own H.264 output, which is evidence and not a guarantee: a smaller card,
a longer URL or a lower bitrate all change the answer.

### The image manifest closes a loop

```bash
python build_card.py credits.json --out card.html --image-manifest ../images/MANIFEST.md
```

The image gate already records a licence and an attribution string per image, and until now
neither ever reached the screen. For a CC-BY image that is not a nicety — the licence requires
the credit to appear where the work appears. This reads the manifest, de-duplicates, and adds
one `Images` row. An empty manifest adds nothing, which is the right answer for a film that
photographs nothing.

## Why the card cannot carry fine print

Every visible line obeys the shared 28px composition floor, the same one the films and the deck
obey. On a 1920×1080 card that leaves room for roughly seven credit rows in one column.

So the layout escalates, and `build_card.py` says which it chose:

1. **one column** while the credits fit — the calmer look, and what a standalone film usually gets;
2. **two columns** when they do not — still the same type at the same size, just twice the room;
3. **more cards**, but only when you ask with `--pages N`.

**It will not add a card on its own.** Another card adds seconds to the film, and the film's
length is settled where the mix is approved — not as a side effect of somebody adding a name.
When two columns overflow it refuses, and tells you how many cards the list actually needs.

`build_card.py` estimates the fit with arithmetic; `check_card.py` measures it in a browser.
The browser is the authority. The constants in the build script mirror the rules in
`card.template.html`, so changing one without the other makes the estimate lie — and the
overflow then surfaces in the check instead, which is the safe direction but a slower one.

## Fonts, and languages the bundled ones do not cover

`fonts.css` carries Instrument Sans and JetBrains Mono as inlined woff2. **Both are
Latin-only.** A card with Chinese, Japanese or Korean text falls back to whatever the machine
doing the render happens to have installed, which means it can render differently on the next
machine and is not reproducible.

```bash
python build_card.py credits.json --out card.html --extra-fonts cjk.css
```

Pass a CSS file of extra `@font-face` rules with the faces inlined. Nothing may be fetched at
render time, so a `<link>` to a font service will not do — `check_card.py` fails it.

## Getting it into a film

The card is a separate render that joins the film's picture without either being re-encoded.
That only works because `render_card.py --mp4` hands the card to the film's own exporter rather
than encoding it here: that exporter holds the only copy of the H.264 profile, pixel format,
colour range and bt709 metadata, and a second copy of those would drift. When it drifted, the
join would still produce a file that plays and is wrong somewhere in the middle.

`append_card.py` compares resolution, frame rate, codec, profile, pixel format and every colour
field before it joins anything, and refuses on a mismatch. Afterwards it hashes the picture's
first *n* frames out of the joined file and checks them against the original — the only proof
that a copy was actually a copy.

### The audio has to grow too, and this is the part that surprises people

The delivery step refuses a picture and an audio track that differ by more than one frame. A
six-second card therefore needs six more seconds of audio. There are two honest ways to get it:

- **Plan it at the audio gate.** The mix is rendered that much longer, and the music tail runs
  out underneath the card. This is the good one, and it means the card's length has to be known
  when the mix is made — which is why it belongs in the opening interview, not at the end.
- **Pad the locked mix.** `append_card.py --mix … --mix-out …` appends digital silence. The
  film simply goes quiet under the card. Use it when reopening the mix costs more than the
  silence does. It is not the same thing, and the script says so every time.

### For a film rendered from 3D

A film encoded from a PNG sequence needs no video work at all:

```bash
python render_card.py card.html --frames out/ --start-number 1801 --fps 30 \
    --width 2560 --height 1440
```

Numbered PNGs that sort after the film's own frames, which the existing frame encoder picks up
because it globs and sorts. Set `--start-number` past the last rendered frame, and match the
render's width and height. The card is static, so all of its frames are one screenshot copied.

## What check_card.py actually checks

| | |
|---|---|
| contract | the export root exists, its box is exactly the authored size, the duration is positive |
| offline | nothing fetched at render time; a logo that silently 404s leaves a hole |
| composition | overflow, the 28px floor, overlap, clearance — the shared check, one implementation |
| structure | a disclosure, somebody answerable, a contact, and no heading with nothing under it |
| static | two different instants give identical pixels |

It is the third caller of the shared composition module, beside the film's own check and the
deck's. The floor is defined once, there.

## Honesty rules, which are not style

- **No name goes on this card that did not do the thing.** It is a credit, not a courtesy.
- **No role is defaulted.** An empty role is omitted, so the card can be incomplete but never
  false.
- **The disclosure is not optional and not negotiable.**
- **The template ships with no logo.** A default that carried one institution's mark would
  stamp it on other people's films.
