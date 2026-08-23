# Set aside, not deleted

Nothing here was thrown away, and nothing here is needed by any skill. It was moved out
on 2026-08-22 so the skills' own folders hold only what they use, and so an install stops
copying 92 MB nobody reads. **This directory does not travel** — `install_skills.py` does
not copy it, and `check_links.py` fails any link from a skill into it.

Decide on each of these at your leisure. Deleting anything here is safe in the sense that
git keeps every version, and `CLAUDE.md` forbids rewriting history to tidy it.

## explainer-picture/ — 53 MB

`Explainer Video as-delivered.html` and `Explainer Video captions-off.html`, the two
Claude Design bundles that **are** the how-to-make-an-explainer film. They play in a
browser; there is no MP4 of that film anywhere.

**Not re-makeable.** These are an input to the render, not an output of it. The two differ
by exactly one byte — `captions:true` becomes `false` — which is the claim
`examples/how-to-make-an-explainer/RENDER-LOG.md` makes, and keeping both is what makes it
checkable. `.gitattributes` here stops git normalising them, which would change their
bytes and break that.

Cheap to keep in git: the second bundle stores as a delta against the first, so the pair
costs about as much history as one of them.

## assembly-gallery/ — 33 MB

`purple_demo.png`, `purple_showcase.png`, `purple_slide.png`, `purple_cinematic.png` — four
hero stills from the assembly film, about 8 MB each.

**Not re-makeable.** The circuit board they were rendered from deliberately never came to
this repository. Purple was chosen for trace contrast and part separation; red and green
were never committed. Only `purple_showcase` is named by any document
(`examples/assembly/RENDER-LOG.md`, in a story about a render that could not be
reproduced); the other three are named by nothing.

## deck-unused-assets/ — 176 KB

`slide7-checklist-gate0.png` and `slide8-checklist-gate2.png`. The deck's
`master-template.html` has `__ASSET:…__` placeholders for five of its seven images; these
two have none, so they are not in the built deck. `build.py` fails on a *missing* asset and
never notices an unused one, which is why nothing caught this. `ASSETS.md` says they were
kept so a GATE 0 legibility call could be reversed in one edit.

## frozen-scripts/ — 36 KB

Six scripts from the assembly film's audio work that no other file in the repository names:
`audition_clone.py`, `generate_v8.py`, `make_deep_prompt.py`, `rebuild_compare.py`,
`editx_style.py`, `move_swell.py`.

They came from two directories that `_shared/README.md` describes as records to read and
not to run — their inputs were takes that never travelled. The other sixteen scripts in
those directories are cross-referenced from `VOICE-LOG.md`, `AUDIO-LOG.md` or each other,
so they stayed.

## slide-deck-gate4-toolkit/ — 40 KB

The reference implementations that came back with the GATE 4 proposal, on 2026-08-23, after that
proposal was applied and deleted: `mechcheck.js` (the four checks, written to run inside a built
master), `run_mechcheck.py`, `render_slides.py`, `check_pptx_layout.py`, `deckcfg.py`,
`render_pptx.ps1` and their README.

**The part that generalizes is already in the skills.** Checks 3 and 4 — element collision, and
clearance inside a diagram — were ported into `_shared/checks/composition.py`, with the tuned
constants and a negative test, so `slide-deck` and `education-video` both run them. What is kept
here is the original, unported form, because it is the evidence the tuning numbers came from.

`check_pptx_layout.py` is the one piece with **no counterpart in the skills**, deliberately. GATE 4
now asks for a mechanical check on any export that is a second implementation; the only deck in
this repository rebuilds its PowerPoint as one full-bleed image per slide, so there is no second
layout engine here to check and a ported copy would be code that had never been run. The next deck
that builds a hand-editable rebuild should start from this file. It carries the 960-pt canvas
constant that a 720-pt version got wrong.

Its own README states the tuning numbers and the negative test. Nothing links here from a skill,
and nothing may.

## SETUP-vendor-step-to-blender.md — 8 KB

A verified vendor-STEP to Blender route: Mayo 0.10.0, FreeCAD 0.21.2, Blender 4.2.2, with
the dead ends named, dated 2026-08-17.

**This one is not junk.** It has an entire commit of its own and **no file in the
repository points at it** — not `showoff-render/SKILL.md`, not the assembly film's picture
README, not `EXPORT-MANIFEST.md`. It is real, hard-won procedure that was one deletion away
from being lost silently. It is here so that it is at least visible; linking it from
`showoff-render`'s method would be the better answer, and needs someone to decide it
belongs there.

## The one file that was deleted rather than moved

`Temperature Controller Intro 1080p.mp4`, 18 MB, the intro film's silent 1080p master.
Deleted because unlike everything above it **is** re-makeable: it is a render of
`examples/intro/picture/Temperature Controller Intro.html` by
`education-video/method/export_html_video.py`.

That was checked rather than assumed. Re-rendering the first 90 frames and comparing them
against the original recovered from git history gave **SSIM 0.9978, PSNR 43.4 dB** — the
same picture, with the residual being re-encode noise at a different bitrate. Re-making it
needs Playwright, Chrome and ffmpeg, none of which are installed on this machine by
default; they were installed into a temporary environment for that check.

    python .claude/skills/education-video/method/export_html_video.py \
        ".claude/skills/education-video/examples/intro/picture/Temperature Controller Intro.html" \
        out/education/picture/intro-1080p.mp4 --width 1920 --height 1080 --fps 30
