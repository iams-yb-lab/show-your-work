---
name: technical-report
description: Use when the user wants to write a report or technical write-up that presents a project to readers outside it — a design report, a findings report, documentation a reader with background but no project context must understand on their own. Start here BEFORE writing any outline or section. Triggers on "design report", "write a report", "write up this project", "document this design", "present this project", "make this understandable to outsiders".
---

# Technical report — process notes

The order that works is **evidence → skeleton → sections → cold read**. Prose written before the
evidence is mapped asserts things nothing supports; sections written before the structure is settled
get rebuilt after every cross-reference exists.

This file is a toolbox, not a procedure to recite. How the report is written — its register, its
structure, whether it ends on a decision — belongs to the user and the project's style guide; nothing
here is an opinion on that. What is here is the process that keeps the numbers right and the reader
able to follow.

## Who the report is for

The reader has the background and none of the context: they can follow the mathematics and the
physics, and they have never heard of the project, its parts or its vocabulary. Turn that into two
written lists, what may be assumed and what must be taught, and check every section against them.

## What to settle first

Read the project first; ask what it leaves open, in plain prose, together.

- Where the report lives (report, evidence map, cold-read record), never beside this skill.
- Who reads it: the two lists above, in the user's words.
- The subject and where the evidence is: design files, data, data sheets, calculations, earlier
  documents; and what exists only in the user's memory, which will be written down and labelled as
  their statement.
- What has been done, per subsystem: built, measured, simulated, specified, intended. This becomes
  the front matter and bounds every sentence.
- Whether there is a quantitative target and its pass rule, or the honest absence of one.
- What the report must not claim: the scope limits, collected now, kept as a section.
- Where it will be read and how long it may be.

Write the answers down with the report's files.

## The evidence map

Read every source end to end before writing a word of report. Then one entry per number and per
load-bearing claim: value, unit, one home (the file and place it lives, linked at every point of use),
and an honest status: measured (where, on what), specified (whose document, typical or maximum),
calculated (from which inputs), assumed (whose assumption), or unknown.

- Two sources that disagree are reconciled here or recorded as an open contradiction the report
  carries visibly. Never silently pick one.
- Namesake quantities are inventoried now, with the distinct name the prose will use for each.
- A number with no home does not go in the map, and therefore never in the report.

Show the map and ask whether the statuses are honest.

## The skeleton

Every section at one to three sentences. Structure is cheap to move now and expensive after prose and
cross-references exist. Front matter states the evidence status before any claim. Order sections so
that no section uses a term or idea a later one defines; record per section the question it answers,
the map entries it draws on and the new terms it introduces. That last list is the vocabulary plan the
sections are checked against. Show the skeleton and ask whether the sections and order are right.

## The sections

One at a time, verified before the user sees it. If a later section finds that an earlier approved one
must change, say so and ask before editing it.

Verify each section: every number against the map (value, unit, status, home); every claim against the
front matter, nothing measured-sounding about the unmeasured; every calculation re-derived by a
different route or a fresh subagent, now, while it is one section's worth; every term against the
vocabulary plan, defined before use and exactly once; every cross-reference resolving. Numbers appear
once and link home; claims carry their status in the sentence, not a footnote; comparisons use
identical columns at identical operating points; namesakes keep their distinct names at every
appearance.

## The cold read

The report claims to work on a reader with background and no context; the honest test is a reader who
has none: a fresh subagent or a colleague. It gets the audience description, the report and reporting
instructions, and reads nothing else. It reports, with locations: every term met before the report
taught it; every question left open; every claim taken as measured; its own playback of what the
report concluded. The user judges whether that playback matches what the report meant.

Alongside it, a mechanical pass over the whole document: term-before-definition order; any number
appearing twice with two values; compared tables still carrying identical columns; every link
resolving; the front matter still true of the finished document; the scope section covering everything
the report does not claim.

Fix what both surface, list every fix, and re-run the section verification on touched sections. A
re-test needs a new cold reader. Keep the record: one entry per reading, what stumbled, where, what
changed.

## The user's read, then delivery

The user reads the report end to end; a report every check passed can still lose its reader, and
only a person notices where. A wording fix re-runs the section verification; a fix that changes what a
section claims needs a fresh cold read. Then deliver the report, the evidence map and the cold-read
record, in the agreed home, links resolving.

## Numbers

No claim the evidence map does not support; no measured-sounding statement about anything unmeasured;
no number without a home; rounding only, never beyond the inputs' precision; and when the honest
answer is "not built or tested yet", the front matter says so.
