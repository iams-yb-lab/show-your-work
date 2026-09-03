# What belongs to which skill

The answer to "I can't tell which thing belongs to what". One row per skill, then the
two directories that are nobody's skill in particular.

Everything a skill owns is inside that skill's own folder under
[`.claude/skills/`](.claude/skills/). That location is not a choice — Claude Code only
finds a skill if its `SKILL.md` is there.

| skill | instructions | method | worked examples | size |
|---|---|---|---|---|
| [`education-video`](.claude/skills/education-video/) | `SKILL.md`, `interview.md`, `images.md` | [`method/`](.claude/skills/education-video/method/) — the picture method, the composition check, the HTML-to-video exporter, the delivery mux | [`examples/`](.claude/skills/education-video/examples/) — two films: `intro/` and `how-to-make-an-explainer/` | 2.9 MB |
| [`natural-voice`](.claude/skills/natural-voice/) | `SKILL.md` — a pointer document; its body is the link into `method/` | [`method/`](.claude/skills/natural-voice/method/) — `README.md` is the method itself, `EXPERIMENTS.md` is what is ruled out, `audio_audit.py` measures | [`profiles/`](.claude/skills/natural-voice/profiles/) — `warm-natural/` (approved) and `deep-onyx-slow/` | 984 KB |
| [`showoff-render`](.claude/skills/showoff-render/) | `SKILL.md` — self-contained | none; the skill carries its own method | [`examples/assembly/`](.claude/skills/showoff-render/examples/assembly/) — one film: the Blender and KiCad pipeline, its render log, its audio record | 600 KB |
| [`slide-deck`](.claude/skills/slide-deck/) | `SKILL.md` — self-contained, contains no paths | none | [`examples/presentation/`](.claude/skills/slide-deck/examples/presentation/) — the how-to-use-the-skills deck, delivered, with every gate document | 12 MB |
| [`technical-report`](.claude/skills/technical-report/) | `SKILL.md` — self-contained, contains no paths | **none** | **none** | 20 KB |

**`technical-report` owns nothing else, and that is not an oversight.** It is the only
skill not distilled from a produced artifact, recorded in
[`EXPORT-MANIFEST.md`](EXPORT-MANIFEST.md). Nothing is missing; do not go looking.

**`slide-deck`'s 12 MB is the deck**, which used to sit in a top-level `presentation/`
that no document connected to it. It is that skill's only evidence.

## Shared: [`.claude/skills/_shared/`](.claude/skills/_shared/)

Only what more than one skill calls. It has no `SKILL.md`, so Claude Code does not load
it as a skill.

| | what | called by |
|---|---|---|
| [`audio/`](.claude/skills/_shared/audio/) | the BS.1770-4 loudness meter, the true-peak limiter, the van Herk sliding maximum, the voice chain, the pitch set | `natural-voice` links `voice_chain.py` by name; `education-video` and `showoff-render` films import it |
| [`checks/`](.claude/skills/_shared/checks/) | `composition.py` — overflow, the font floor, overlap (text on text, text on a picture, a picture on a picture) and the clearance a word keeps from lines and block edges, measured in a browser. One implementation, one 28-pixel constant | `education-video` (per instant), `slide-deck` (per slide, and again statically) |
| [`endcard/`](.claude/skills/_shared/endcard/) | the authorship card a film ends on: who made it, who built the project, what was generated, who is answerable — optionally with the film's credits as a byline above the rule, a representative still, and a QR code to where the viewer goes next. `build_card.py` from a per-film credits file, `check_card.py` through the shared composition check, `render_card.py` to an MP4, PNG frames or a still, `append_card.py` to join it to the picture as a stream copy | `education-video` (MP4, joined before the mux), `showoff-render` (frames numbered past the last rendered one) |

## The rest of the repository

| | what |
|---|---|
| [`tools/`](tools/) | this repository's own machinery, which no skill calls: `install_skills.py`, `update.py`, `check_links.py`, `friction.py`, `skill-hashes.txt` |
| [`references/`](references/) | set aside, not yet deleted — see [`references/README.md`](references/README.md) |
| [`feedback/`](feedback/) | `lessons/<skill>.md` is injected at the start of a run of that skill; `inbox/` is raw and stays on this machine |
| `proposals/` | absent, which is the rule working: it holds only skill text waiting for the user's exact phrase, and the change that applies one deletes it |
| [`MAINTENANCE.md`](MAINTENANCE.md) | open items on this repository's own machinery — the tooling, the checks, the hooks, the rules. One line each, deleted when done |

## What travels, and what does not

`python tools/install_skills.py <project>` copies **192 files, 16.5 MB**, and a target
project gains exactly one directory: `.claude/skills/`. The machinery is remapped inside
it, at `_shared/tools/` and `_shared/feedback/lessons/`.

- **Travels:** every skill folder whole — instructions, methods, profiles and examples —
  plus `_shared/`, the four tools, `feedback/lessons/` and `LICENSE`.
- **Does not travel:** `references/`, `proposals/`, `feedback/inbox/`, this file,
  `README.md`, `CLAUDE.md`, `EXPORT-MANIFEST.md`, `MAINTENANCE.md`.

`examples/` travels deliberately. It is small now that the media has gone, and
`natural-voice`'s method links a file inside `showoff-render/examples/` — the record of
narration that passed every measurement and was rejected twice by ear. Excluding
examples would leave that link dangling in every installed copy.

## Load-bearing paths

Five relative links, in three files, that `tools/check_links.py` fails on if they break.
A broken one leaves a skill loading, sounding authoritative, and empty.

```
natural-voice/SKILL.md          ──►  method/README.md
                                ──►  method/EXPERIMENTS.md
                                ──►  profiles/warm-natural/
natural-voice/method/README.md  ──►  ../../_shared/audio/voice_chain.py
                                ──►  ../../showoff-render/examples/assembly/audio/VOICE-LOG.md
education-video/SKILL.md        ──►  method/README.md, method/composition_check.py,
                                     method/deliver_film.py, interview.md, images.md
showoff-render/SKILL.md         ──►  examples/assembly/RENDER-LOG.md   (prose, not a link)
```

## Files that still hold their own copy of something

Named here rather than fixed, because each is a record of what ran on a particular
machine and rewriting one to look tidier would make it false.

- `_shared/endcard/fonts.css` — the same two inlined woff2 faces as
  `slide-deck/examples/presentation/fonts.css`, 403 KB of it. Copied rather than shared so the
  end card's folder is self-contained: it is called from two skills that assemble a film in
  different ways, and a font path reaching sideways into one skill's *examples* would break the
  moment that example moved. The faces are identical bytes; nothing computes anything from them.
- `showoff-render/examples/assembly/audio/natural-v8/` and `.../pipeline/` — five files
  measure loudness by running ffmpeg over a file. That is a different mechanism from the
  meter in `_shared/audio/`, which takes a numpy array, so it is not a second answer to
  the same question. What is repeated between them is the ffmpeg invocation.
- `.../assembly/picture/tools/probe_sheet.py` and `crop_tile.py` — two more contact-sheet
  generators, Blender-side, beside the HTML-side one in `education-video/method/`.
- `education-video/examples/how-to-make-an-explainer/tools/finish.py` — muxes and verifies,
  as `education-video/method/deliver_film.py` does. `finish.py` is the one that has run on
  a finished film; `deliver_film.py` has not.
