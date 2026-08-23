# The build chain, in order

GATE 4 asks for one named command chain, written down where the deck's files live, with every
derived artifact after the thing it derives from. This is that chain for this deck. Run **all** of
it: re-running the whole thing must be cheaper than remembering which parts to re-run, because the
one step you skip is the step that ships a stale figure while every check still passes.

```bash
cd .claude/skills/slide-deck/examples/presentation
T=tools
python $T/build.py        && \
python $T/crosscheck.py   && \
python $T/render_check.py && \
python $T/make_pptx.py
```

Every step exits non-zero on failure, so `&&` between them is a working gate.

| step | reads | writes | why it is here |
|---|---|---|---|
| `build.py` | `master-template.html`, `assets/`, `fonts.css` | `how-to-use-the-skills.html` | the master is generated, never hand-edited |
| `crosscheck.py` | the master, `STORYLINE.md` | — | headlines and slide count, written independently, must agree. Plus a static font-size sweep of the source |
| `render_check.py` | the master | `exports/slides/*.png`, `exports/links.json` | the four mechanical checks in a real browser, and one PNG per slide |
| `make_pptx.py` | `exports/slides/*.png`, the master's notes | `exports/how-to-use-the-skills.pptx` | full-bleed rebuild, so it **must** come after `render_check.py` |

## The order is load-bearing in one place

`make_pptx.py` inserts the PNGs that `render_check.py` writes. Change a slide, rebuild the master,
rebuild the PPTX — and without `render_check.py` in between the PowerPoint carries the **old**
picture. Nothing fails; it just ships a stale slide. That is a defect this exact chain exists to
prevent, and it is how a real deck shipped a redesigned diagram in its old form.

## Two things the chain does not do

**It does not look at the pictures.** `render_check.py` writes `exports/slides/*.png` and says so;
reading them is a person's job, every build. The checker and a pair of eyes catch different things —
a checker finds crossings and collisions a reader skims past, a reader finds what is legal and ugly.
A green check is not a reviewed slide.

**It does not check the PowerPoint's geometry**, and it does not need to: every slide of this
rebuild is one full-bleed image, so there is no second layout engine to disagree with the browser.
A deck whose PowerPoint is a *hand-editable* rebuild is a second implementation and does need its
own mechanical check — bounds, collisions and the font floor read back out of the saved file, with
wrapped-text height estimated pessimistically. There is a reference implementation in this
repository, set aside rather than installed, and `references/README.md` says where.
