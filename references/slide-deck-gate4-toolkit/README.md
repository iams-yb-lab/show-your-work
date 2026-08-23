# Reference implementation — the four GATE 4 mechanical checks

Supporting code for the GATE 4 proposal, which was **applied on 2026-08-23 and then deleted**, as an
applied proposal is. Its argument and its evidence now live in that pull request and in
`EXPORT-MANIFEST.md`; the part that generalizes lives in `_shared/checks/composition.py`, which both
`slide-deck` and `education-video` run. These files are **evidence and a starting point, not part of
the install payload** — nothing here is reached by a skill, and `install_skills.py` does not copy
this directory.

They came out of one 15-slide talk deck. Every rule they enforce exists because a human found the
defect first.

| file | what it is |
|---|---|
| `mechcheck.js` | the four checks, run inside a built HTML master, in the browser, where real geometry can be measured. Writes its verdict to `<div id="mechcheck">` and reddens `#mechbanner` on failure |
| `run_mechcheck.py` | loads the master in headless Chrome, reads that verdict, exits non-zero on any finding |
| `render_slides.py` | one PNG per slide, so the pictures can actually be looked at |
| `check_pptx_layout.py` | the same three ideas for a PowerPoint rebuild, read back out of the saved `.pptx` (bounds, collisions, font floor, wrapped-text height estimated pessimistically) |
| `render_pptx.ps1` | renders a `.pptx` to one PNG per slide through PowerPoint itself — the authentic renderer, and the only way to see font substitution |
| `deckcfg.py` | the shared config loader the Python tools use (`deck.json`: canvas, font floor, export names) |

## The numbers that matter for tuning

`mechcheck.js` check 4 is stated as **clearance, not contact**, per-axis:

```js
var CLEAR_X = 8;    // px from any stroke, sideways
var CLEAR_Y = 4;    // px from any stroke, vertically
var INSET_X = 12;   // px inside its own block, sideways
var INSET_Y = 3;    // px inside its own block, vertically
```

A **symmetric** 12 px rule reported **54 findings on 15 slides**, nearly all of them two-line
labels in perfectly readable blocks. The per-axis rule above reported **8**, and all eight were
real — six of them on slides the deck's author had not yet reached. A check that floods its report
gets switched off, which is worse than no check, so tune it against a deck a human has already
judged.

## Proving a check can fail

Never trust a check that has only ever passed:

```bash
python - <<'PY'
d = open('deck.html', encoding='utf-8').read()
d = d.replace('<section class="slide" id="s05">',
  '<section class="slide" id="s05"><div class="card blue" style="position:absolute;'
  ' left:120px; top:300px; width:600px; height:300px;">deliberate collision</div>', 1)
open('negtest.html','w',encoding='utf-8').write(d)
PY
# run the check against negtest.html — it MUST fail — then delete the file
```

Expected:

```
MECHCHECK FAIL
s05: blocks overlap — <div> over <img>
```

## What the master must provide

`mechcheck.js` expects the page conventions the deck it came from used: `#deck` as the scaled
canvas wrapper, one `.slide` per slide with `.current` on the rendered one, `aside.notes` for
speaker notes (never rendered, always excluded from every check), and `#mechcheck` / `#mechbanner`
for output. Configure with `window.MECHCHECK = { canvas:[1920,1080], fontFloorPx:20 }` before it
loads; the clearance values above are overridable by the same object.
