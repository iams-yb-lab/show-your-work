# Slide scripts — how-to-use-the-skills deck

Talk deck. Per slide: the headline (byte-identical to STORYLINE.md), what the slide shows,
the speaker notes (your voice, spoken register), and the trace. Written act by act at
GATE 3; an act appears here only after the one before it was approved.

---

## ACT I — WHERE YOU'RE STANDING

### Slide 1

**Headline:** You've finished real work — and now it has to reach people who weren't there.

**Shows:** One centred node — "your finished work" (a board, a design, a result — drawn as
a small PCB glyph). Three arrows out to the audiences it must reach: a *reader* (Lucide
`file-text`), a *room* (Lucide `presentation`), a *viewer* (Lucide `play`). No other text.

**Says (notes):**
"You know this moment. The design works, the measurements are in, the hard part is done —
and now somebody says: can you write that up? Can you present it? Can you make a video?
And that part always costs more than it should, because you're starting from a blank page
every time. This talk is about not starting from a blank page. Everything I'll show you is
one repository you already have access to."

**Trace:** Framing slide — no factual claim. The "one repository" line is the repo itself.

---

### Slide 2

**Headline:** The complaint about AI writing is almost never that it's wrong — it's that nobody can read it.

**Shows:** Two posts from r/ClaudeCode, three weeks old, side by side and whole: "Opus 5 —
unreadable jargon" (140 up, 90 comments) and "Going back to 4.8 due to Opus 5 word salad?"
(316 up, 238 comments). Source and score labelled above each, so the attribution reads before
the quote.

**Asset:** `assets/reddit-unreadable-jargon.png` (2022×982) and `assets/reddit-word-salad.png`
(2014×734), user-supplied 2026-08-19, uncropped. Each shown at 820px — 0.41× — so the post
titles land near 22px and the body text near 11px. **Below the GATE 0 floor, deliberately, in
line with slides 8–10:** the audience is meant to read the two titles and the vote counts, and
the speaker reads the rest aloud. If this slide has to work without a speaker, crop each post
to its title and first paragraph and the floor is recoverable.

**Two further images were requested for this slide and are not in it:** an illustration of a
press compacting pages, and a banner reading "AI Slop Explained". Both were pasted into the
session rather than saved, so no file exists to embed. Both are also third-party artwork with
no known licence, which is a separate reason to source or replace them before they go on a
projected slide. Drop the files in `assets/` and the slide takes a second row.

**Says (notes):** see the master. The point to land: every complaint on that screen is about
the *output being unreadable*, not about the model being wrong — a process problem, not a
capability problem, and therefore fixable by the thing on the next two slides.

**Trace and its limits — read this before presenting.** These posts are evidence that people
find raw model output unreadable. They are **not** evidence that AI-generated *reports* are
slop; neither post is about a generated document. The headline is written to claim only what
the posts show. Do not upgrade it in the room. Quoted under fair use as published criticism,
attributed on screen to r/ClaudeCode with the authors' own usernames visible in the captures;
nothing retouched, no vote count altered.

---

### Slide 3

**Headline:** This repo turns finished work into four deliverables — a report, a deck, an explainer film, a showoff film — one skill each.

**Shows:** The map. Four labelled boxes — `technical-report`, `slide-deck`,
`education-video`, `showoff-render` — each with an arrow to its deliverable (document
glyph, slides glyph, film glyph ×2). Beneath the two films, one shared strip:
`natural-voice` — "rides along whenever anything speaks". Repo name small at top.

**Says (notes):**
"Four things you might need to hand somebody, four skills, and the names say what they do.
technical-report writes the document that stands alone. slide-deck builds a presentation —
including this one. education-video makes an explainer film, and showoff-render makes the
cinematic hardware shot. There's a fifth skill, natural-voice, that you never call
directly — it kicks in automatically whenever generated speech is involved, because voice
is where video projects die. You don't install anything for any of this: open a Claude
Code session in the repo directory and the skills load."

**Trace:** Five skills and what each covers — README.md:3–12 (skills table).
Skills load by opening a session in the directory — README.md:14–15. natural-voice scope
"any generated or synthetic speech" — README.md:8.

---

### Slide 4

**Headline:** Every skill runs the same shape: it interviews you, posts a checklist, and only you approve each gate.

**Shows:** The universal pipeline, one diagram: **posted checklist** (unticked boxes) →
**interview** (speech bubble: "where do the files go? who's the audience?") → **gates in a
row**, each gate with a loop back labelled *you approve*. The first gate after the
interview carries a highlight: *the source under it — document or CAD — is audited before
anything is built on it.*

**Says (notes):**
"Here's the shape, and it's the same in all four skills, so you learn it once. The first
thing you see is the plan, as a checklist — before any work happens. Then it interviews
you: where do the files go, who is this for, what's the one takeaway, what's the budget.
Real questions, and it won't guess when you don't answer. Then it works gate by gate, and
here's the important part — a gate closes when *you* say it's good. Never by itself. And
the first real gate is always the same: the source under the thing gets audited. No script
against a document that's half-finished, no render against CAD that's missing models.
That's what makes the later stages cheap instead of painful."

**Trace:** Post plan as unticked checklist before anything, then ask to begin — all four
SKILL.md "How this runs" sections (e.g. slide-deck SKILL.md; technical-report SKILL.md:45;
education-video SKILL.md:41; showoff-render SKILL.md:41). Interview first, unanswered
question is a question not a default — each skill's GATE 0. "A gate ends when the user
says it is good, never when you decide it is" — verbatim in all four. Source audited
first: technical-report GATE 1 (evidence map), slide-deck GATE 1 (the source),
education-video GATE 1 (source document), showoff-render GATE 1 (CAD readiness — "Nothing
renders until every box is ticked").
*Diagram-order note: the checklist is posted before the interview; the diagram shows that
true order (the headline lists the three features, non-temporally).*

---

## ACT II — THE DOCUMENTS: REPORT AND DECK

### Slide 5

**Headline:** technical-report builds the document that stands alone: evidence → skeleton → sections → cold read.

**Shows:** The technical-report pipeline as a gate diagram: **evidence map** (a mini table:
value · unit · one home · status) → **skeleton** (whole report, a few lines per section) →
**sections** (drawn one at a time, each with a verify tick before it advances) → **cold
read** (a reader figure with an empty head, arrow back: *plays the verdict back to you*).
Under the first box, small: *measured · specified · calculated · assumed — every number
wears one.*

**Says (notes):**
"The report skill is built around one contract: the reader has the background and none of
the context. They can follow the math; they've never heard of your project. So the order
is evidence, skeleton, sections, cold read — and it's not negotiable. Every number gets
mapped before any prose exists: its value, its unit, the one file it lives in, and an
honest status — measured, specified, calculated, or assumed. Then the skeleton — the whole
report at a few lines per section — because structure is cheap to move before prose exists
and ruinous after. Sections get written one at a time, verified before you ever see them.
And at the end, the document is tested on a reader who genuinely has no context."

**Trace:** Order "evidence → skeleton → sections → cold read, and it is not negotiable" —
technical-report SKILL.md:8. Reader contract "background and none of the context" —
SKILL.md:28–31. Evidence map: one home, statuses measured/specified/calculated/assumed —
SKILL.md:115–120. Skeleton first, structure cheap now, ruinous later — SKILL.md:133–135.
Sections one at a time, verified before shown — SKILL.md:171, 208.

---

### Slide 6

**Headline:** Say "write up this project as a report" and the skill takes over: interview, evidence map, skeleton — no prose until you approve the structure.

**Shows:** A chat mock, two bubbles. Yours: *"write up this project as a report"*.
Claude's reply, rendered as the real thing: the six-gate checklist verbatim from the skill
(`GATE 0 the interview … GATE 5 the user's read`) followed by *"Ready to begin?"* — then a
zoomed detail of the first interview questions: *where does the report live? who reads it —
what may they be assumed to know?*

**Says (notes):**
"This is literally what happens. One sentence from you, and the first thing back is the
plan as a checklist — you know the whole route before any work starts. Then the interview:
where does the report live, who reads it, what has actually been built versus only
designed, what must the report *not* claim. And here's what it refuses to do: it will not
write a paragraph of prose until you've approved the skeleton. Because rewriting structure
after the prose exists is the expensive way around."

**Trace:** The checklist text — technical-report SKILL.md:48–55, quoted verbatim in the
mock. "Ready to begin?" — SKILL.md:57. Interview questions shown — SKILL.md:88–107.
No-prose-before-approved-skeleton — the gate order itself, SKILL.md:64–67 ("prose is the
expensive half") and 133–135.

---

### Slide 7

**Headline:** slide-deck puts the argument on slides: source → storyline → slide scripts → build → cold pass.

**Shows:** The slide-deck pipeline: **source** (audited) → **storyline** (a column of
headline lines — and this column is *readable*: it is this deck's own five acts in
miniature) → **slide scripts** (per slide: shows / says / trace) → **build** (one HTML
file glyph) → **cold pass** (viewer with empty head, arrow back: *plays the takeaway
back*). The storyline column carries the flip-test label: *the headlines alone must carry
the whole argument.*

**Says (notes):**
"Same discipline, aimed at a room. The deck's argument gets written before any slide
exists: one line per slide, and each line is the slide's actual headline, as a full
sentence that asserts something. The test is brutal and simple — read only the headlines,
top to bottom. If they don't carry the whole argument on their own, the storyline is
wrong, and it gets fixed while it's still one line of text per slide. Only after you
approve that argument do slides get scripted, then built into a single HTML file, and then
a viewer with no context has to play the takeaway back."

**Trace:** Order "source → storyline → slide scripts → build → cold pass" — slide-deck
SKILL.md heading and gates. Headline as full-sentence assertion, one claim per slide —
SKILL.md GATE 2. The flip test "read the headlines alone… complete argument" — SKILL.md
GATE 2. One self-contained HTML master — SKILL.md GATE 4. Cold viewer plays back the
takeaway — SKILL.md GATE 5.

---

### Slide 8

**Headline:** Say "make slides about this project" and you get what you're watching — this deck is that run, gate by gate.

**Shows:** The whole editor window, unretouched and uncropped — this repository in the file
tree, the run in the chat panel, the sentence that was typed and the six-gate checklist that
came back with nothing ticked. First of three full-window captures (slides 7, 8, 9) that walk
the same run from start to delivery.

**Asset:** `assets/deck-run-original.png`, 3839×2086, whole. Shown at 1306px — **0.34×** —
which puts the screenshot's own text near 13px on the 1080p canvas. **This is deliberate and
it breaks the GATE 0 font floor.** The user's instruction at GATE 4 was to show the entire
work environment rather than a legible crop: the slide's job here is *this is a real tool on
a real desk*, and the audience is not asked to read it — the checklist's content is carried
by the speaker's notes and, legibly, by nothing on screen. Readable if a viewer opens the
PPTX or PDF and zooms; not readable from a seat. `render_check.py` does not and cannot catch
this — it measures computed DOM font-size and is blind to text inside a bitmap. The legible
crop this replaced is kept at `assets/slide7-checklist-gate0.png` if the call is reversed.

**Says (notes):** see the master's `<aside class="notes">` for slide 7 — the desk, the one
sentence, the six gates with nothing ticked, the storyline written before the slide, and the
footnote that slide-deck is the youngest of the four skills.

**Trace:** The screenshot itself (user-supplied, 2026-08-19), plus the run's own artifacts:
`presentation/GATE0-ANSWERS.md`, `presentation/STORYLINE.md` (this headline is its Act II
line 4), this file. "Not distilled from a produced deck… the first deck this skill produces
is its first evidence" — slide-deck SKILL.md, opening section.

---

### Slide 9

**Headline:** Every tick is your approval, not the skill's progress — this run stopped at GATE 2 and waited until you said go.

**Shows:** The same window later in the same run. GATE 0 and GATE 1 ticked and naming the
files they produced; GATE 2 marked *here*; 3, 4 and 5 still open.

**Asset:** `assets/deck-run-gate2-original.png`, 3839×2088, whole, at 1306px (0.34×) — same
deliberate floor break as slide 7, same reason. Legible crop kept at
`assets/slide8-checklist-gate2.png`.

**Two things are now on screen that earlier revisions cropped out**, because "the entire
window" was the instruction and cropping to flatter would be the dishonest move:
- "26 slides, inside the agreed 25–28" — true when written, three revisions stale by
  delivery. The notes address it head-on rather than hoping nobody reads it.
- A user message opening "I insist on editing the skills" — the repository's own override
  phrase for its read-only rule. At 13px it is not legible from a seat, but it is legible to
  anyone who zooms the export, and it sits three slides from the house rule on slide 16.
  Flagged for the speaker; the user's call to leave it in.

**Says (notes):** see the master. Two ticks, then a stop; and the twenty-six-slides cut told
in the past tense, as the argument for approving arguments before pixels.

**Trace:** The screenshot; `presentation/GATE0-ANSWERS.md` ("Length and slide budget" records
the 25–28 → 16–18 revision, "user's call"); `presentation/ASSETS.md` (Act IV removed at
GATE 3, user's call). The final count is this deck.

---

### Slide 10

**Headline:** This is the same run closed: six gates ticked, and every artifact it produced named on screen.

**Shows:** The same window at the end of the run. All six gates ticked, each naming its file;
below them the deck, the export and the tools by path; and last, the two closing notes that
record what went wrong.

**Asset:** `assets/deck-run-gate5-original.png`, 3839×2086, whole, at 1306px (0.34×). Same
floor break, same reason. **One thing on this capture is already stale:** it describes the
deck as "16 slides", which was true when it was taken and is not now — this slide is the
seventeenth. Left in, because retouching a screenshot to agree with the present is the one
thing a screenshot may never do; the notes may say it aloud if a room asks.

**Says (notes):** see the master. The point is the last paragraph on that screen — a cold
viewer flagged a numbering problem, the speaker assumed it was wrong, it was right, and the
retraction is in the record; and the run-screenshot slide was added after the cold pass and
so was never cold-viewed. Not that it went perfectly — that when it didn't, the process
wrote it down.

**Trace:** The screenshot; and every file it names, all present in `presentation/`:
`GATE0-ANSWERS.md`, `SOURCE-AUDIT.md`, `STORYLINE.md`, `SLIDE-SCRIPTS.md`, `COLD-PASS.md`,
`how-to-use-the-skills.html`, `exports/how-to-use-the-skills.pptx`, `tools/`. The two closing
notes are quoted from `COLD-PASS.md`, "Open honesty item, user's call".

---

## ACT III — THE VIDEOS

### Slide 11

**Headline:** Proof you can watch: the how-to-make-an-explainer film — 4 min 30 s, 8 scenes, 55 lines — came out of the workflow on the next two slides.

**Shows:** A film title card (user frame from `assets/explainer-frame.png` if supplied,
generated card otherwise) with the stat row in JetBrains Mono: `4:30 · 8 scenes · 55
lines · 1920×1080 · 30 fps`. Link line: **[YT-EDU-LINK]** with QR placeholder box —
both swapped for the real URL and a generated QR at the very end.

**Says (notes):**
"This isn't a proposed workflow — this film exists and you can watch it after the talk;
the link's on the slide. Four and a half minutes, eight scenes, fifty-five spoken lines,
and every one of those lines traces to an audited source document. Its whole artifact
trail — the interview answers, the source, the script with its traces, the design prompt,
the render log — is sitting in this same repository, so when you run the skill yourself,
you have a complete worked example to hold your run against."

**Trace:** "4:30.3 · 8 scenes · 55 lines · 893 words · 1920×1080, 30 fps" — explainer
README.md:7 (4:30.3 rounded to 4 min 30 s; 30.3 s → "four and a half minutes" in spoken
register). Made with the education-video skill — README.md:3–5. Artifact trail stage by
stage — README.md:13–27. Published on YouTube — the user's statement (2026-08-18), URL
pending as [YT-EDU-LINK].

---

### Slide 12

**Headline:** education-video runs document → script → audio → picture: the narration is recorded first and owns the timing.

**Shows:** The pipeline with **AUDIO** visually lifted: document → script → **audio** →
picture, the audio stage carrying a waveform block and a `natural-voice` badge. Beneath it,
a timeline strip: the locked waveform on top, and cue times + captions hanging *down from
it* — arrows from the waveform to the cuts, labelled *measured off the master, never
guessed*. A small crossed-out mirror of the pipeline (picture first, audio squeezed in)
labelled *the expensive way round*.

**Says (notes):**
"The explainer skill's whole trick is the order. The document is audited first, the script
is written against it — every spoken line traces to a line in the source — and then the
narration is recorded *before any picture exists*. The finished audio master is the timing
authority: caption timing and picture timing are measured off that file. Do it the other
way — build the picture, then squeeze narration into it — and you get sentences cut off
mid-breath and a narrator rushing the densest line. And the voice itself goes through the
natural-voice skill, which is not optional: two complete soundtracks got thrown away
before that method existed."

**Trace:** Order "document → script → audio → picture, and it is not negotiable" —
education-video SKILL.md:8. Backwards gives narration cut mid-sentence, rushed lines —
SKILL.md:8–10. Every claim traces to a source line — SKILL.md:121. "The audio is the
timing authority… lock a narration master, then take caption and picture timing off the
finished file" — SKILL.md:140–142. "Load the natural-voice skill. It is not optional — two
complete soundtracks were thrown away" — SKILL.md:139–140.

---

### Slide 13

**Headline:** Say "make an explainer video" and you approve a script, a soundtrack and an image set — then paste one prompt into Claude Design, which returns the picture.

**Shows:** Chat mock: *"make an explainer video about my project"* → the artifact trail as
a hand-off diagram: **script** (lines with trace marks) → **one combined soundtrack**
(waveform, *you approve it under music, not dry*) → **image manifest** (licensed stamps) →
**ONE PROMPT** (a single document glyph, oversized on purpose) → **Claude Design** → an
HTML page glyph → **your render** (file icon, `mp4`). The prompt glyph labelled: *works on
the first paste — no questions left in it*.

**Says (notes):**
"Here's what you actually approve, in order: the script — words and order, before anything
is recorded. Then the soundtrack — and not the dry voice: the combined track, voice over
music, because a voice approved dry is not a voice approved under music. Then the image
set, gathered and licensed. And then the skill's last deliverable, which surprises people:
it's a *prompt*, not a video. One self-contained message you paste into Claude Design,
which designs and returns the picture as a web page that plays the film. You never draw a
frame yourself — and rendering that page to an actual video file is the one part that
comes back to you, because Claude Design's encoder can't do it alone."

**Trace:** Five deliverables ending in "one prompt the user pastes into Claude Design…
returns an HTML bundle you then render" — education-video SKILL.md:27–32. "You never
design, draw or animate the picture" — SKILL.md:34–35. Combined track approved before
GATE 4, "a voice approved dry is not a voice approved under music" — SKILL.md:144–148.
Images licensed — SKILL.md:150–153. Prompt "has to work on the first paste", one message,
self-contained — SKILL.md:158–160. "Claude Design cannot encode video… rendering that page
to a file is yours" — SKILL.md:172–176.

---

### Slide 14

**Headline:** Proof you can watch: the assembly film — 84 seconds at 2560×1440 — approved on the first viewing of draft three.

**Shows:** Second film title card (user frame from `assets/assembly-frame.png` if
supplied, generated card otherwise), stat row in JetBrains Mono: `84 s · 2520 frames ·
2560×1440 · draft 3, first viewing`. Link line: **[YT-SHOWOFF-LINK]** with QR placeholder,
swapped at the very end.

**Says (notes):**
"The showoff skill's proof first, method next — link on the slide. Eighty-four seconds, 2560 by 1440,
clean on every check, and approved on the *first viewing* of the third draft. The honest
part of that sentence is 'third draft': draft one and draft two had real faults, humans
found them cheaply at low resolution, and the fixes happened before the expensive render.
The skill's whole job is making sure the expensive render only happens once. The full
story — what each draft got wrong and what it cost — is in the render log, in this
repository."

**Trace:** "assembly_purple_v2.mp4 — 84 s, 2520 frames, 2560×1440 — came out of it, clean
on every check, approved on the first viewing of the third draft… twelve stages and three
drafts" — showoff-render SKILL.md:8–10. Draft 1/draft 2 faults — SKILL.md:204–216. Full
arc in `video/showoff/assembly/RENDER-LOG.md` — SKILL.md:12–13. Published on YouTube — the
user's statement (2026-08-18), URL pending as [YT-SHOWOFF-LINK].

---

### Slide 15

**Headline:** showoff-render films hardware: CAD readiness → stills → motion → drafts → frozen final, and nothing renders until the CAD checks pass.

**Shows:** The pipeline: **CAD readiness** (a strip of 8 tick boxes, each with a two-word
label: model on disk · not gitignored · assembly-complete · colours vs photos · instance
count · DNP parts · revision frozen · swaps named) → **stills** (colour picked at final
quality) → **motion** (timing tables + a price tag) → **drafts** (an eye icon: *watched,
end to end*) → **frozen final** (a padlock on the camera, caption: *one camera edit once
voided 421 finished frames*).

**Says (notes):**
"The showoff skill is the same gate discipline pointed at Blender, and its first gate is
the one that saves you real money: nothing renders — not a draft, not a probe frame —
until eight checks on the CAD pass. Is every on-camera part actually on disk. Is a model
hiding behind gitignore. Do the colours match photographs of the real part — STEP colours
lie; a connector shipped near-white when the real one is beige. Is the revision frozen.
Each of those checks exists because skipping it once cost real render-hours. And at the
far end, the camera freezes before the final render, because a camera edit voids every
finished frame — four hundred and twenty-one finished frames went exactly that way once."

**Trace:** Gates — showoff-render SKILL.md:44–51. "Nothing renders until every box is
ticked. Not a draft, not a probe frame" — SKILL.md:103. The eight checks and their
stories (Harting near-white vs beige photos, gitignored model, frozen revision) —
SKILL.md:105–114. Camera edit voids frames, "421 finished 1440p frames were thrown away
exactly this way" — SKILL.md:193–198 (also 66–68).

---

### Slide 16

**Headline:** Say "make the board look amazing" and the costs stay honest: render hours are measured from probe frames, and you watch every draft.

**Shows:** Chat mock: *"make the board look amazing"* → three exhibits in a row:
**colour stills** side by side (pick the colour before any motion), the **cost bar** — two
bars generated from the numbers, `guess 10.5 h` vs `measured 16.1 h` — and a **draft
strip** at low resolution with an eye icon: *you watch it end to end*. Caption under the
draft strip: *every fault that mattered was found by a human watching — none by a check.*

**Says (notes):**
"Three things keep this from eating your week. Colour gets decided on final-quality stills
before any motion exists, because it's a lighting decision, and changing it later
invalidates everything. Cost gets *measured*, not guessed: a handful of probe frames at
final quality price the whole render — on the assembly film the guess said ten and a half
hours and the measurement said sixteen — and you approve those hours against the budget
you gave in the interview, before a single draft frame renders. And drafts get watched.
Not scored, watched. On the assembly film, every fault that mattered was caught by a human
watching a draft, and not one by the automated checks. The checks bound what they measure;
your eyes find what's wrong."

**Trace:** Colour decided on stills at final quality, "picking it later invalidates
everything" — showoff-render SKILL.md:139–141. Probe frames, "A guess was 10.5 h; the
measurement said 16.1 h" — SKILL.md:156–158. Approving measured cost against the GATE 0
budget — SKILL.md:159–160, 94–96. "WATCH IT. Non-negotiable… Every fault that mattered
was found by a human watching" and none by a check — SKILL.md:164–168, 180–182.

---

## ACT V — START NOW

*(Act IV was removed from the storyline at the user's direction before this act was
drafted; slides renumbered 14–15.)*

### Slide 17

**Headline:** Starting costs one sentence in Claude Code: name the output you want, and the interview takes it from there.

**Shows:** A terminal mock in two steps. **Step 0 — once:** a typed line — *"install the
skills from `<path to this repo>` into my project"* — with a one-line result: *skills +
the `video/` tree they depend on, copied, links verified.* **Step 1 — every time:** in
your own project, one typed sentence — *"write up this project as a report"* — and the
checklist appearing beneath it, unticked, with *Ready to begin?* at the bottom. To the
right, small, the other three sentences that would have worked: *"make slides about this
project" · "make an explainer video" · "make the board look amazing"*.

**Says (notes):**
"So here's everything you actually have to do. Once: copy the path of this skills repo,
and ask Claude to install it into your project — its installer carries the skills *and*
the method tree they point into, and checks every link on arrival. Don't try to make them
global under your home directory; the installer refuses, because the skills would lose the
tree they read from. From then on, starting costs one sentence in your own project; the
four on screen are lifted from the skills' own trigger lists. You'll get the plan as a
checklist, then the interview — and the first question is always *where do your files go*,
because your project's files live in your project, never inside the tooling. Two house
rules and I'm done: answer the interview honestly, especially about what's measured versus
what's only intended — the deliverable inherits your answers. And the skills themselves
are read-only; if a run needs something changed, write it down with your project, don't
edit the skill."

**Trace:** Install elsewhere via `python tools/install_skills.py /path/to/other/project`,
copies the skills and the tree, preserving geometry so every link resolves —
README.md:53–61. Global `~/.claude/skills/` install refused, and why — README.md:63–66.
The four trigger sentences — each SKILL.md frontmatter `description` (technical-report:
"write up this project"; slide-deck: "make slides"; education-video: "explainer video";
showoff-render: "make it look amazing"). Checklist first, then interview, first question
"where do the files go" — each SKILL.md GATE 0 (never next to the skill, never
defaulted). Read-only rule — README.md:101–108.

---

### Slide 18

**Headline:** Name the output, answer the interview, and the gates carry you to a delivered report, deck, or video.

**Shows:** Typographic slide: the takeaway, verbatim, large, on the cream paper with the
teal accent rule above it. Beneath, one quiet footer row: the four skill names ·
`[YT-EDU-LINK]` · `[YT-SHOWOFF-LINK]` (swapped for the real URLs at the very end).

**Says (notes):**
"That's the whole method in one sentence. Name the output. Answer the interview. Approve
the gates. The two films on the links are what came out the other side of exactly this
process — nothing on them was hand-animated, and nothing in them says more than its source
could defend. Questions."

**Trace:** The takeaway — GATE0-ANSWERS.md, verbatim, as required. "Nothing on them says
more than its source could defend" — the no-overclaiming rule each film ran under
(education-video SKILL.md:195–200; showoff-render's checks); the films' existence — the
user's YouTube statement, links pending.

---
