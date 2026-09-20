---
name: slide-deck
description: Use when the user wants a slide deck — a presentation, talk slides, a pitch deck, or a reading deck that presents a project, a design, or findings to an audience. Start here BEFORE writing any outline or opening any design tool. Triggers on "slide deck", "presentation", "slides for a talk", "pitch deck", "make slides", "deck about this project", "present this to an audience".
---

# Slide deck — process notes

The order that works is **source → storyline → slide scripts → build → cold pass**. Slides drawn
before the storyline is settled get redrawn after every change of story, and a deck built on an
unchecked source asserts things nothing supports, at projector size, to a room that will believe
them.

This file is a toolbox, not a procedure to recite. What the deck says, how its argument is shaped and
how it looks are the user's decisions and the project's style guide's; nothing here is an opinion on
them. The one deck this skill has produced is in `examples/presentation/`, with its records.

## Two kinds of deck

A deck is **spoken over** or **read alone**. A talk deck's slides are sparse and its words live in
the speaker notes; a reading deck's slides carry the full meaning. Settle which it is first and write
it down with the deck's files; the scripts, the build and the cold pass all depend on it. If both
are wanted, the second is a planned variant.

## What to settle first

Read the project first; ask what it leaves open, in plain prose, together.

- Where the deck's files go (storyline, scripts, master, exports, records), never beside this skill.
- Spoken over or read alone; if spoken, who speaks.
- The audience: what may be assumed known, what must be taught.
- The source material and its evidence status: measured, specified, intended.
- Length: minutes for a talk, reading minutes for a reading deck; from it, a slide budget.
- Where it will play: the screen fixes the aspect ratio and a font-size floor, agreed as a number.
- Which export: the master is one self-contained HTML file; PDF prints from it; PowerPoint is either
  pixel-faithful slide images with real notes text, or a hand-editable rebuild, which is a second
  implementation and priced as one.
- Brand or template constraints, with the real assets.

## The source

A deck is only as accurate as the document under it. Before a storyline: the source states its
evidence status; every number has one home; typicals, estimates and assumptions are labelled; namesake
quantities are disambiguated; the scope limits are explicit. If the source is not ready, help write it
first; the `technical-report` skill covers that.

## The storyline

One line per slide, each line the slide's headline, in a file written to be parsed: one headline per
line, section names on their own marked lines, no tick marks in the file. The headlines' bytes are what
the cross-check tool later reads, so a headline that needs a status word (estimated, specified) carries
it from the start. Keep to the slide budget here, where cutting costs a line. Group slides into
sections so scripts can be drafted and reviewed a section at a time. Show the file and ask whether the
order is right before scripting.

## The slide scripts

One section at a time. Each slide's script carries: the headline, byte-identical to the storyline;
what the slide shows (a chart and which comparison; a table and which columns at which operating
points; an image, its source and licence; a diagram and what it draws); what it says (notes for a talk
deck, on-slide prose for a reading deck); and a trace from every claim to the source.

Before showing a section, verify it: every number against the source (value, unit, status, home);
every slide's evidence supporting its own headline; every term the audience must be taught appearing
before it is used; every trace pointing where it says. Rounding is the only transform allowed on a
number, never beyond the source's precision. Comparisons use identical columns at identical operating
points. Every image is licensed and no watermark is ever removed; search the project's own files
before asking the user for one, and close a section with the asset list: found, with paths; missing,
with what each must show.

## The build

- **One self-contained HTML master**: every slide on one fixed canvas at the agreed aspect ratio,
  fonts and images embedded, no external requests, plays from a double-click. Headlines land
  byte-identical to the scripts. Charts are generated from the numbers they plot.
- **Four mechanical checks, on every build**: font floor (text inside a scaled diagram measured at its
  scaled size); slide overflow; element collision; clearance inside every diagram between strokes and
  words, per axis, walking stroke geometry point by point. The shared implementation is
  `_shared/checks/composition.py`.
- **Prove each check can fail** by injecting a defect into a scratch copy before trusting a pass.
- **Render every slide to an image and look at it**, every build. Checks and eyes catch different
  things.
- **Speaker notes live in the master**, marked, and the master renders without them; the notes-free
  rendering is what the room sees and what every export derives from.
- **A cross-check tool**, built early: it parses headlines and slide count from the master and from
  the storyline file and exits non-zero on any difference.
- **Exports derive from the master and are regenerated, never patched.** A hand-editable PowerPoint
  rebuild has its own layout engine and needs its own geometry check (bounds, collisions, font floor,
  wrapped-text height estimated pessimistically); it does not carry its fonts, and the user is told
  which renderer they are getting.
- **The build is one named command chain**, written down with the deck's files, ordered so every
  derived artefact follows the thing it derives from.
- Ask the user to open the master full screen on the machine it will play from, and the export the
  way its recipient will.

## The cold pass

The deck claims to work on its audience; the honest test is a viewer with no context: a fresh
subagent or a colleague. It gets exactly the audience description, the notes-free rendering (never
the scripts or the HTML source) and reporting instructions, and reads nothing else. It reports, per
slide: the main point it took, the argument as it understood it, every term met before it was taught,
every claim it took as measured, every question left open. The user judges whether the viewer's
playback matches what the deck meant.

For a talk deck, add a timing pass measured on the actual speaker reading one section aloud; that
measured pace prices every section's notes against the stated length. A slide whose notes outrun their
time is fixed by cutting words or splitting the slide, never by asking the speaker to talk faster.

Fixes land on approved slides; list every one, re-run the section verification on touched slides and
the mechanical checks on the rebuilt master. A fix that changes a headline changes the storyline file
too; then the cross-check runs again. A fix that changes what a slide claims needs a fresh cold viewer.
Keep a record: one entry per pass, what stumbled, at which slide, what changed.

The user's own pass follows: rehearsing a talk deck aloud once end to end, or reading a reading deck
as its recipient would. Then deliver the storyline, the scripts, the master, the exports, the
cross-check tool and the record, in the agreed home.

## Numbers

The deck carries real numbers to a room that asks no footnotes. No claim the source does not support;
no measured-sounding statement about anything unmeasured; no number without a home; rounding only,
never beyond the inputs' precision; and when the honest answer is "not built or tested yet", the
slide says so.
