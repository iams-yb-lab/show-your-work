# One folder per skill

**Status: PROPOSED 2026-08-22.** Authorised by the user typing `I insist on editing the skills` on
2026-08-22, after reading the layout in this document's *The layout* section.

## Why

The user's words, on being shown the repository: *"It looks messy, a human like me can't easily
understand the structure, like which thing belongs to which skill."* Three defects sit behind that,
all confirmed by reading the tree rather than by argument.

### 1. Nothing maps a file to the skill that owns it

There is no index. `README.md` lists directories and never connects them to skills. So:

- `presentation/` is `slide-deck`'s only evidence. **No skill names it, and no document says it is
  slide-deck's** — by design, because the `travel` check forbids the link. The connection exists
  only in a reader's head.
- `technical-report` owns no files at all. Nothing says so, so a reader looks for them.
- `video/engine/` is shared by three skills' films; `video/picture/` belongs to one. Both sit at the
  same depth under the same parent with no marker of the difference.
- `video/` itself is named for a medium, not a skill, and holds two skills' methods, three films'
  evidence and all the shared audio tooling.

### 2. The same job is implemented more than once

| what | where | note |
|---|---|---|
| canvas overflow + font-size floor, via headless Chrome | `video/picture/composition_check.py` and `presentation/tools/render_check.py` | the 28px floor is a literal in both files |
| integrated loudness / true peak | `video/engine/mix_audio.py:675-726` **plus seven other files** | `video/README.md` states "a second copy of a loudness meter is a second answer to the same question." The rule is written down and broken. |
| mux picture to audio, then verify by stream hash | `video/picture/deliver_film.py` and `video/education/how-to-make-an-explainer/tools/finish.py` | `finish.py` has run on a real film; `deliver_film.py` never has |
| contact sheet from sampled frames | `composition_check.py`, `showoff/.../tools/probe_sheet.py`, `crop_tile.py` | three variants |

The seven loudness copies are the serious one. A measurement that disagrees with itself is worse than
no measurement, and this repository's stated bench is a person's ears — so a wrong number is not
caught by listening.

### 3. Installing copies 108 MB, and 106 MB of it is never read

`tools/install_skills.py` copies `video/` whole. Of that:

- `video/education/` — 73 MB. Linked by **no** skill.
- `video/showoff/assembly/gallery/` — 33 MB, four stills. Linked by no skill; three of the four are
  named by no file in the repository at all.
- everything the skills actually reach — **under 2 MB**.

So every project installed into receives three finished jobs' footage that no session opens.

## What this costs, and the honest weakness in the case

`CLAUDE.md`: *"a `proposals/` document argues from entries — how often, at which gate, what it cost
— and then the user types the exact phrase. A proposal with no entries behind it is taste, which is
what the read-only rule exists to keep out."*

**`feedback/` holds zero entries.** The loop has never been exercised: `feedback/inbox/` contains only
its README, all five `feedback/lessons/*.md` are placeholders, and the one friction pull request ever
opened (#2, `friction/mac`) was closed unmerged. So there is no run history behind this document.

That is a real weakness and it is not papered over here. What stands in its place is narrower and
should be read as such: this proposal changes **where files sit**, not what any gate asks or how any
method works. Not one instruction about making a film changes. The skill-file edits are path
rewrites — eleven markdown links and one prose citation — and every one is listed below with its
exact before and after. Nothing about *taste* is being decided, which is what the read-only rule
exists to keep out.

## The layout

```
.claude/skills/
  _shared/            only things more than one skill calls
    audio/            loudness meter, limiter, sliding maximum, voice chain, pitch set
    checks/           the one composition check (replaces two)
    README.md
  education-video/
    SKILL.md  interview.md  images.md
    method/           the picture method and its tools
    examples/         the two films: documents, scripts, logs
  natural-voice/
    SKILL.md
    method/           README.md  EXPERIMENTS.md  audio_audit.py
    profiles/         warm-natural/  deep-onyx-slow/
  showoff-render/
    SKILL.md
    examples/assembly/   the film whole: render log, audio, picture pipeline, narration
  slide-deck/
    SKILL.md
    examples/presentation/   the how-to-use-the-skills deck
  technical-report/
    SKILL.md          owns nothing else, and MAP.md says so

tools/                this repository's machinery: install, update, link check, friction
references/           set aside, not deleted
proposals/  feedback/
MAP.md                skill -> method, shared tools, examples, what travels
```

### Two decisions inside that shape

**Shared tools sit at `.claude/skills/_shared/`, not at root `tools/`.** A skill's link must resolve
identically here and in a project installed into. Root `tools/` cannot do that: the installer must
not merge into a `tools/` the target project already owns, so it would have to land somewhere else,
the link depth would change, and the link would break on install — the exact failure the `travel`
check exists to catch. Inside `.claude/skills/` the link is `../_shared/audio/mix_audio.py` in both
places, with no remapping. Root `tools/` keeps its own job: the installer, updater, link checker and
friction ledger, none of which a skill calls. A directory without a `SKILL.md` is not discovered as a
skill, so `_shared/` is inert to Claude Code.

**`examples/` travels.** An earlier draft excluded it to shrink the payload. That was wrong for one
concrete reason: `natural-voice`'s method links
`showoff/assembly/audio/VOICE-LOG.md` — the record of narration that passed every measurement and
was rejected twice by ear — and that link is load-bearing enough to sit in `GEOMETRY`. Excluding
`examples/` would leave it dangling in every installed copy. The payload saving does not come from
excluding examples; it comes from the heavy media leaving for `references/`. Documents and scripts
are what a worked example is for, and they are small.

## The skill-file edits, in full

Eleven markdown links (`GEOMETRY`, `tools/check_links.py:73-85`) and one prose citation
(`CITED`, `:88-90`). Nothing else in any skill file changes.

### `.claude/skills/natural-voice/SKILL.md`

| line | before | after |
|---|---|---|
| 8 | `../../../video/natural-voice/README.md` | `method/README.md` |
| 8 | display text `` `video/natural-voice/README.md` `` | `` `natural-voice/method/README.md` `` |
| 14 | `../../../video/natural-voice/EXPERIMENTS.md` | `method/EXPERIMENTS.md` |
| 192 | `../../../video/natural-voice/profiles/warm-natural/` | `profiles/warm-natural/` |
| 192 | display text `` `video/natural-voice/profiles/warm-natural/` `` | `` `natural-voice/profiles/warm-natural/` `` |

The two display copies are not checked by `check_links.py`, which matches on the link target only. A
run that fixed the links and left the backticked text would pass every check while reading wrong.

### `.claude/skills/education-video/SKILL.md`

| line | before | after |
|---|---|---|
| 40 | `../../../video/picture/README.md` | `method/README.md` |
| 194 | `../../../video/picture/composition_check.py` | `method/composition_check.py` |
| 233 | `../../../video/picture/deliver_film.py` | `method/deliver_film.py` |

`interview.md` and `images.md` (lines 15, 91, 164) are in-skill and unchanged.

### `.claude/skills/showoff-render/SKILL.md`

| line | before | after |
|---|---|---|
| 12 | `video/showoff/assembly/RENDER-LOG.md` (prose) | `showoff-render/examples/assembly/RENDER-LOG.md` |

Line 8 names `assembly_purple_v2.mp4`, a film that is not in this repository and never was. No check
covers it. Out of scope here; recorded so it is not lost.

### `slide-deck` and `technical-report`

Unchanged. Neither contains a path. `slide-deck` gains `examples/presentation/` beneath it, which
makes its evidence visible for the first time without the skill file changing at all.

### Not a skill file, but load-bearing

`video/natural-voice/README.md` becomes `natural-voice/method/README.md`, and its three links move
with it: `../engine/voice_chain.py` → `../../_shared/audio/voice_chain.py`,
`../showoff/assembly/audio/VOICE-LOG.md` → `../../showoff-render/examples/assembly/audio/VOICE-LOG.md`,
`profiles/warm-natural/` → `../profiles/warm-natural/`.

## The media

| file | size | what happens | why |
|---|---|---|---|
| `Temperature Controller Intro 1080p.mp4` | 18 MB | **deleted** | derived from the `.html` beside it; `export_html_video.py` re-makes it. Recoverable from git history. |
| `Explainer Video as-delivered.html` + `captions-off.html` | 53 MB | → `references/` | the only copy of that film; not re-makeable |
| `gallery/purple_*.png` ×4 | 33 MB | → `references/` | not re-makeable; the board they were rendered from never came here |

Deleting the MP4 means `intro_env.py:24`, `intro_mux.py` and `intro_cues.py` lose their picture
source. Those are updated to say the picture is re-made from the `.html`, and that doing so needs
Playwright, Chrome and ffmpeg. **ffmpeg is not installed on the machine this was done on**, so the
re-render is untested, and the film's README says so rather than implying otherwise.

Nothing in `references/` is deleted in this pass. It exists so the user can decide later with the
files in front of them.

## What would reopen this

- A skill needing a file another skill owns, which `_shared/` did not anticipate.
- `examples/` growing large enough that the payload argument returns. The check is
  `python tools/install_skills.py --check <target>`.
- Any friction entry showing a session lost time to the new layout. There are none today, and that
  is the weakness named above; the first entries that arrive are the evidence this document lacks.
