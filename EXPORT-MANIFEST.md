# Export manifest

Extracted 2026-08-14 from the `temperature-controller` repository, at commit `2fea890`.

141 files, 2.6 MB. The method, the shared tooling and the evidence came; the films did not.

## The skills, byte-identical

Copied without a character changed, because they are read-only and because an adapted skill is a
different skill. Verified by `tools/check_links.py`, which reads `tools/skill-hashes.txt`.

| file | sha256 (first 16) |
|---|---|
| `.claude/skills/education-video/SKILL.md` | `99a16be0ad1e7866` — superseded, see below |
| `.claude/skills/education-video/interview.md` | `fa7a570e313f1d84` — superseded, see below |
| `.claude/skills/education-video/images.md` | `81b65b43ae00363c` — superseded, see below |
| `.claude/skills/natural-voice/SKILL.md` | `1b11e1ec4bbf2538` |
| `.claude/skills/showoff-render/SKILL.md` | `8805cef3fc262996` — superseded, see below |

## Edited after export

On 2026-08-17 the user authorized, with the exact phrase, a rewrite of
`.claude/skills/showoff-render/SKILL.md`: the run protocol from `education-video` (interview,
posted checklist, named gates, user-owned approvals) wrapped around the existing rules, which
carried word-for-word. The design and its rationale are in the commit that applied it, `5e7590e`,
and the proposal it was written from, `541b0f9`.
New hash `8abf7da6eed3dc44`, blessed into `tools/skill-hashes.txt`. **This copy now leads the
source repository** — the same edit still needs to land at the source, at which point the two are
byte-identical again.

On 2026-08-22 the user authorized, with the exact phrase, a change to all three
`education-video` files: **the Claude Design handoff is gone.** GATE 5 was one prompt the user pasted
into Claude Design, which returned an HTML bundle we rendered; it is now the picture itself — one
self-contained HTML composition we author and the user approves silent — and a new GATE 6 renders it,
muxes the approved mix, attaches the captions as a subtitle track the viewer switches on, and hands
over the film. Six gates where there were five. The order `document → script → audio → picture` and
GATE 0 through GATE 4 are untouched; `interview.md` loses two Claude Design references and gains one
settled question, and `images.md` loses one. New hashes `85d0e2f11842b63f` (SKILL.md),
`31fd7a97d918746e` (interview.md) and `9b30e8b1da0d596c` (images.md), blessed into
`tools/skill-hashes.txt`. **These copies now lead the source repository**, as `showoff-render` already
does. The rationale, the evidence it argues from and what it deliberately leaves alone are in the commit
that applied it and in its pull request; the proposal itself was deleted on 2026-08-23, once nothing
read-only named it any more.

On 2026-08-23 the user authorized, with the exact phrase, the removal of one machine's account name
from the skills. It stood 105 times across 33 files as `C:\Users\<the account>\...`, in a
repository that is now public, and `CLAUDE.md` calls a hardcoded path a bug in its own right.

Three of those files are live, and were fixed rather than redacted.
`_shared/audio/narrate.py` resolves ffmpeg by `$FFMPEG`, then `shutil.which`, then a glob under
`Path.home()` — so it also survives the ffmpeg upgrade that the pinned version directory would not.
`natural-voice/profiles/deep-onyx-slow/make_prompt.py` puts that same glob on `PATH`.
`education-video/method/README.md` stops telling a reader to prepend somebody else's home directory.

Everything else is a record of a run — logs, generated reports, take selections, and the scripts
`MAP.md` and `_shared/README.md` name as records to read and not to run. Rewriting one of those to
look tidy would make it false, so **only the account segment was replaced, with `<user>`**. Nothing
else in them moved: the versions, timings, measurements and warnings they are kept for read exactly
as they did.

**No hashed file changed**, so `tools/skill-hashes.txt` is untouched and the seven files it verifies
are still byte-identical to the source repository. The payload's other files now differ from the
source wherever they carried that account name. `tools/check_links.py` gained the rule that keeps it
that way: inside the payload, a literal home directory fails the independence check, and `<user>` is
the one account segment it accepts.

Two tools were added to `video/picture/` for the new gates: `composition_check.py` (the GATE 5 check —
export contract, canvas size, offline, determinism, overflow, font floor, contact sheet) and
`deliver_film.py` (the GATE 6 mux, the switchable subtitle track and its verification). Both travel
with the payload; neither has been run on a real film. `tools/check_links.py` now treats the skill's
links to all three as load-bearing, so moving one breaks the check rather than the film.

## Added after export

On 2026-08-18 the user authorized, with the exact phrase, the creation of a fourth skill:
`.claude/skills/technical-report/SKILL.md` — plain-English technical reports for readers with
background but no project context, distilled from the source project's design report
(`docs/design-report-v2.md` there, cited as history, never as a live path). It originates in this
repository and has no source-repository counterpart to be byte-identical to. The analysis behind
it, the pipeline rationale and the two-reviewer verification record are in the commit that created
it, `5e7590e`, and the proposal it was written from, `541b0f9`. It links to
nothing — the first skill with no `video/` dependency. Hash `e751dcf302480871`, blessed into
`tools/skill-hashes.txt`.

On 2026-08-18 the user authorized, with the exact phrase, the creation of a fifth skill:
`.claude/skills/slide-deck/SKILL.md` — slide decks, spoken over or read alone, built as one
self-contained HTML master. Like `technical-report` it originates here, and it is the **second
skill that links to nothing**, so it travels alone. Unlike every other skill in this repository
it was **not distilled from a produced artifact** — there is no reference deck; it carries the
three gate-run siblings' protocol and states its slide craft as method rather than measurement,
and it says so about itself. The proposal, the pipeline rationale and the two-reviewer
verification record are in the commit that created it, `5e7590e`, and the proposal it was written
from, `541b0f9`;
the first deck it produces is its first evidence, and that evidence stays with the deck. Hash
`1ecd48bc86bef336`, blessed into `tools/skill-hashes.txt`.

On 2026-08-23 the user authorized, with the exact phrase, a change to
`.claude/skills/slide-deck/SKILL.md`: **GATE 4's mechanical check is four checks, not two**, and the
geometry rule is stated as *clearance, not contact*. The two the skill named — font floor, slide
overflow — find almost nothing, because a real layout defect is full-size text inside the canvas.
The two added are **element collision** and **clearance inside every diagram**, per-axis, with the
straddling-versus-contained distinction that makes the second usable. GATE 4 also now requires that
each check be proven able to fail before it is trusted, that every slide be rendered and *looked at*,
that an export which is a second implementation get a check of its own, that the build be one named
command chain, and that reusable tooling be run against the finished deck. GATE 3 gains one
paragraph: diagrams are the default, and the asset list is a named output. Four hunks, +59/-6 lines;
everything else is byte-identical by construction, because the text was produced by applying the
edits programmatically rather than retyping the file.

The evidence is a 15-slide talk built with this skill elsewhere, which passed both stated checks and
still reached its author with six layout defects on his first look at a screen. Tuning mattered more
than the idea: a symmetric 12px clearance reported 54 findings on those 15 slides and nearly all were
fine, while the per-axis rule reported 8, every one real. Old hash `1ecd48bc86bef336`, new hash
`6b0c277b92fcd76b`, blessed into `tools/skill-hashes.txt`. **This copy now leads the source
repository**, as `showoff-render` and `education-video` already do.

The machinery behind it is in `_shared/checks/composition.py`, which both `slide-deck` and
`education-video` call, and `tools/test_composition_check.py` is the negative test that proves each
check can fail. The proposal this was applied from was deleted by the same pull request; its
reference implementations were set aside in `references/slide-deck-gate4-toolkit/`.

## What came with them, and why it had to

| what | why it is not optional |
|---|---|
| `video/natural-voice/` | `natural-voice/SKILL.md` links to `README.md` here for the method itself, to `EXPERIMENTS.md` for what is ruled out, and to `profiles/warm-natural/` for the approved voice identity. Without this directory the skill is a broken link |
| `video/engine/` | the shared audio: BS.1770-4 loudness, true-peak limiting, the voice chain. `voice_chain.py` is linked by name from the method as a failed approach not to repeat |
| `video/picture/` | the picture tooling: the HTML-to-video exporter, the composition check and the film mux. `education-video` builds the composition at GATE 5 and delivers the film at GATE 6 — these three are what do it |
| `video/showoff/assembly/RENDER-LOG.md` | showoff-render says "the full arc, with numbers and citations, is in" this file |
| `video/showoff/assembly/audio/VOICE-LOG.md` | the method links to it for the rejected room-tone experiment and its verdict |
| `video/showoff/assembly/{picture,script,audio}/` | the Blender + KiCad pipeline and the audio R&D: showoff-render's reference implementation and the record behind natural-voice's fourteen rejected attempts |
| `video/education/` | both explainers' documents, scripts, logs and tools — including `how-to-make-an-explainer/tools/`, the cross-check tooling `education-video` tells you to build |
| `.claude/hooks/git-autosync.sh` | pushes commits already made; exits silently with no remote |

## What did not come

`video/out/` — 5.1 GB of frames, takes, mixes and masters, gitignored at both ends and
regenerable. Plus two documents about the source repository rather than about the method:
`video/MOVE-LOG.md`, which instructs its own retirement once the old layout is gone, and
`video/RELEASES.md`, an index of cuts that live under `out/`.

**Everything else tracked under `video/` came, including 107 MB of film media** — the two 26 MB
Claude Design bundles, the intro film's MP4 and HTML, and the four committed stills.

That reverses the first pass, which left them on the grounds that films must not accumulate in a
directory packaged for reuse. That rule assumes the film still has a home. Once the source `video/`
is deleted this repository is the only home, and the explainer's own render log says **the picture
cannot be re-rendered without those bundles** — they are an input, not an output. Losing something
irreplaceable to keep a repository tidy is the wrong trade.

The rule still holds going forward: **new** films belong to the project using the skill, not here.

## What was changed on the way in

Nothing in `.claude/skills/`. Outside it, every path that named another checkout as a **live** path
was removed, because the source `video/` tree is being deleted and this repository has to stand on
its own. `tools/check_links.py` now fails on any that come back.

| what | was | now |
|---|---|---|
| 10 Python files | a repository root hardcoded to one checkout | walk up to the directory holding `video/natural-voice/` |
| 2 Python files | `sys.path` into a pre-move `PCB/render/tools` | the same walk-up, to `video/engine/` |
| `render.ps1`, `animate.ps1`, `animate_v2.ps1` | `-Board` defaulted to one project's `.kicad_pcb` | no default; `throw "pass -Board <path to your .kicad_pcb>"` |
| `pipeline/mix_final.py` | the picture to mux hardcoded to one render | `SHOWOFF_PICTURE` from the environment |
| `warm-natural-v2/README.md` | run commands naming one machine's venv in one checkout | `$env:EDITX_PYTHON` and a repo-relative script path |
| 2 narration scripts | traces linked to the board's review and spec | the same traces, named as text, like the rows beside them |

**Records were left verbatim** and are declared in `check_links.py`'s `RECORDS` — six files: the
generation settings, the prompt-selection audition record, the delivered Design prompt, and the
three v2 pipeline reports. They describe what happened on a particular machine on a particular day,
and nothing reads them. Rewriting a record to look tidy in a new repository falsifies it. The
allowlist is exactly those six; nothing is listed that does not need to be, because an unnecessary
entry is a hole.

Sixteen further files mention the source project's name **without depending on it**: fifteen frozen
scripts write to `%TEMP%\temperature-controller-media\`, a machine-local scratch directory that
merely borrowed the name, and the assembly film's brief describes its subject in prose. Neither is
a path into another checkout.

`video/README.md` was rewritten for this repository. Three film READMEs lost a link to the dropped
`RELEASES.md`.

**Records were left verbatim.** `DESIGN-PROMPT.md`'s absolute paths, `education-v2-generation-settings.json`'s
provenance, and `VOICE-LOG.md`'s pre-move `PCB/render/` references all describe what actually
happened on a particular machine on a particular day. Rewriting a record to look tidy in a new
repository falsifies it.

## What will not run here

Honest limits, so nobody discovers them mid-task:

- `video/showoff/assembly/audio/{pipeline,natural-v8}/` — their repository anchors were repaired,
  but their inputs were takes under `out/` and scratch directories in `%TEMP%` that did not travel.
  Read them as the experiment record they are.
- `video/natural-voice/profiles/deep-onyx-slow/make_prompt.py` — same: the profile document and its
  measurements are here, the prompt-generation inputs are not. `warm-natural/` is complete,
  including its prompt WAV.
- `video/showoff/assembly/picture/*.ps1` — the Blender pipeline renders a specific board from a
  KiCad file in the other repository. It is here as showoff-render's worked example.
- The two `narration-assembly*.md` scripts trace their claims to that board's review and spec.
  Those links dangle on purpose and are registered in `check_links.py`'s `EXTERNAL` list.
- Several scripts extend `PATH` with this machine's ffmpeg install. Left alone: changing a path
  that works on the machine the export was made on trades a real capability for a tidier file.

## The layout changed on 2026-08-22: one folder per skill

The `video/` tree described throughout the sections above **no longer exists**. Everything a skill
owns now sits inside that skill's own folder under `.claude/skills/`, and only what more than one
skill calls is shared, at `_shared/`. The argument, and every path rewritten, is in the pull request
that did it, `#8`; the current map is
[`MAP.md`](MAP.md). Read the tables above as history: they record what came out of
`temperature-controller` and where it landed *then*.

| then | now |
|---|---|
| `video/engine/` | `.claude/skills/_shared/audio/` |
| `video/natural-voice/{README,EXPERIMENTS,audio_audit}` | `.claude/skills/natural-voice/method/` |
| `video/natural-voice/profiles/` | `.claude/skills/natural-voice/profiles/` |
| `video/picture/` | `.claude/skills/education-video/method/` |
| `video/education/` | `.claude/skills/education-video/examples/` |
| `video/showoff/` | `.claude/skills/showoff-render/examples/` |
| `presentation/` | `.claude/skills/slide-deck/examples/presentation/` |
| `video/README.md` | `.claude/skills/_shared/README.md`, rewritten |

Three skill files were edited, authorised by the user typing the exact phrase. Seven paths in all:
five markdown links and two of the same paths repeated as display text, which `check_links.py`
matches on the target only and so cannot see. New hashes:

| file | sha256 |
|---|---|
| `.claude/skills/natural-voice/SKILL.md` | `f6b8b08fd2c9b83c702e226f91ddc3f0dac768821f9af32be1a8cca295c3f60d` |
| `.claude/skills/education-video/SKILL.md` | `615f8d021584040cae33c4eb006a27202e3fc1b4c347b139cb38394080273e65` |
| `.claude/skills/showoff-render/SKILL.md` | `ff6df3c1ca528e0c9fcad32031b3f65cb0c4b0b99f441be89731292a267499e5` |

`slide-deck` and `technical-report` contain no paths, were not touched, and their hashes are
unchanged from the entries above.

### What left the payload

Installing was 108 MB and is now 15.8 MB. The difference is media that no skill ever opened, moved
to `references/`, which does not install: the two 26 MB explainer bundles and the four 8 MB assembly
stills. Neither can be re-made — the explainer has no MP4 at all, and the board the stills came from
never travelled — so both are kept, out of the way. See
[`references/README.md`](references/README.md).

One file was deleted rather than moved: `Temperature Controller Intro 1080p.mp4`, 18 MB, the intro
film's silent master. Unlike the rest it is reproducible from the HTML bundle beside it. That was
checked, not assumed: re-rendering its first 90 frames with `export_html_video.py` and comparing
against the original recovered from git gave SSIM 0.9978 and PSNR 43.4 dB. Playwright, a chromium
and an ffmpeg were installed into a temporary environment to do it; none of the three is present on
this machine otherwise.

### Two checks that had to change with the layout

- `check_skills` hashed every `.md` under `.claude/skills/`. Left alone, the move would have put
  about fifty method and example documents under the read-only rule, so a correction to a worked
  example would have reported as tampering. It now hashes `SKILL.md` and any `.md` directly beside
  it: seven files, the same seven as before.
- `.gitattributes` marked `.claude/skills/**` as `-text -diff`. Left alone, every script and
  document in the repository would have become undiffable. Narrowed to `.claude/skills/*/*.md`.

### One thing this manifest claimed that was already wrong

The note above about the two `narration-assembly*.md` files being "registered in
`check_links.py`'s EXTERNAL list" is stale — `EXTERNAL` is empty and was empty before this change.
The files are fine; the claim about how was not.
