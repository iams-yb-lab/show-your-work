# How to make an explainer video — the source document

The document this film is made from. Everything the narrator says traces to a line here; every number
it speaks lives in [`NUMBERS.md`](NUMBERS.md) and is referred to below by key, never by value. How the
film's own claims are checked is in [`INTERNAL.md`](INTERNAL.md), which is never narrated.

## How sure this document is

**Read this before believing anything below.** Three grades of claim appear here, marked where they
are used, and the film carries the same distinction into the narration:

- **Measured** — re-derived this session by [`tools/verify_numbers.py`](tools/verify_numbers.py),
  which probes the media file and parses the scripts. Nothing is trusted because prose says it.
- **Recorded** — written down when it happened and not reproducible now, usually because the artifact
  it described was deleted. Spoken as *"the log records…"*, never as a measurement.
- **Reasoned** — an explanation offered for a measurement. The measurement is evidence, the
  explanation is argument, and neither gets promoted to the other.

**What has never been tested:** whether any of this works with a model other than Claude. That is
unknown, not broken, and the film says exactly that much.

## Where the viewer is standing

**You have finished the thing.** Now people have to understand it — a supervisor, a customer, a
committee, strangers — and none of them were there while you built it.

**What you want is a short, clean video that explains it.** Not a course, not a documentary. A few
minutes that leave someone able to say what you made and why it works.

**And you do not want to become a video producer to get one.** You want to hand the work to something
that can do it quickly, and end up with something you would actually put your name on. That is a
reasonable thing to want, and it is now a reasonable thing to get — as long as you know which parts
are yours to decide.

## Step one, and it takes about a minute

**Open the Claude app, or VS Code with Claude in it, and ask Claude to install the repository linked
below this video.** The whole repository, not one file — the stages depend on parts of it that are not
worth naming on screen. That is the entire setup: nothing to configure, no editing software to learn,
nothing else to download.

The link lives in the description, so **no address is ever spoken or shown.** From then on you talk to
Claude in plain language and it runs the four stages below, stopping at each one to show you what it
made and ask whether it is right.

## What a good explainer has to do

Three things, and they are the only three anyone is actually buying:

1. **The audience you picked understands it.** Not "people" — a named audience, with what they already
   know and what they do not written down before a word is drafted. A video aimed at everyone lands on
   nobody.
2. **Everything in it is true, and you can say why.** Every claim points back at something that
   supports it, and anything unbuilt, unmeasured or merely planned says so in the same breath. A
   confident voice over a wrong number does more damage than silence.
3. **Nothing in it sounds wrong.** No word clipped, no sentence hurried, no caption running a beat
   behind the speech. A viewer cannot say why they stopped trusting it, only that they did.

**That is the target**, and the machinery that proves it is the skill's job rather than yours, which
is why these three are stated as outcomes and no tolerance is ever taught.

## The architecture

Four stages, one order, each finished before the next begins:

| | stage | what comes out of it |
|---|---|---|
| 1 | **the document** | everything true about your subject, written down and checked |
| 2 | **the script** | the words, in order, each with the seconds it needs |
| 3 | **the sound** | one frozen recording, which from now on owns the clock |
| 4 | **the picture** | frames cut to fill lengths that are already decided |

**Each stage hands the next one something already finished**, and nothing upstream gets reopened.

## Who does what

**Claude does the labour:** the drafting, the counting, the recording, the checking, the handover.
Hours of fiddly work that has to be right rather than clever.

**You do three things it cannot do for you** — say who the audience is, say what is actually true
about your own work, and say yes or no at each stage. The last one is not a formality. **Judgement is
the one part of this that cannot be delegated**, because a model cannot know that a number is stale or
that a claim is one you would not defend in a room.

That division is why the stages stop and wait. A stage that never asks is a stage that has replaced
your judgement with its own guess.

## Stage 1 — the document

**Claude asks you what the thing is, and writes the document with you.** It presses on which numbers
are measured and which are only planned, and it will not let the same fact into the file twice. What it
holds itself to is longer than this and is not the viewer's problem — [`INTERNAL.md`](INTERNAL.md).

**Your part: tell it the truth about your own work, and say when the document is right.** Nothing else
in the process can repair a wrong number here. Animation only enlarges it.

## Stage 2 — the script

**Claude turns the document into the words**, in order, each line given the seconds it needs so nothing
has to be hurried, and refuses any claim the document does not make.

**Your part: read it once.** This is the last cheap moment to change a word — after it, a wording
change costs a re-recording.

## Stage 3 — the sound, before any picture exists

**Claude records it and freezes one file.** From then on, the captions come off that recording word by
word, and so does every length the picture will be cut to. It also checks the recording actually said
the script — on one film `TRIAL.reworded` lines were rewritten because a word had gone missing, one of
them a *"can't"* whose lost negation inverted the sentence. Recorded.

**Your part: listen.** Timing and pronunciation can be checked automatically; whether it sounds like a
person cannot. The log records `VOICE.binned` complete soundtracks thrown away in this repo *after*
passing every measurement. That is why the file comes to you and not to another check.

## Stage 4 — the picture, and the paste that ends it

By now every length is already decided, so the picture has one job: **fill the time it is given.**

**What you get from Claude at this point is a single prompt.** It already contains the scene list with
its start and end times, what each scene shows, what the video should look like, what must never be
drawn, and where every file it needs is sitting on your disk. **You paste it into Claude Design and
wait.** What comes back is a finished video with the sound already in it — not a silent picture you
then have to combine with something.

That is the whole of stage 4 from where you sit: one paste, then a wait. The last check — that picture
and script still agree — is arithmetic rather than watching, because a video is never signed off by
staring at it hoping.

## The verdict

**Do it in this order: document → script → sound → picture.** Each stage hands the next one something
already finished.

Why each alternative loses:

- **Picture first** — the normal way, and the expensive one. The container is rigid, so the sentence is
  what gets damaged: a re-render to fix properly, audible repairs when it isn't.
- **Document last, or never** — the video becomes where the thinking happens, so its errors arrive at
  full volume with a confident voice on top.
- **Script skipped** — a wording problem found in the recording costs a take; found in the script it
  costs a keystroke.
- **Sound last** — nothing sets the clock, so every length is a guess the picture gets cut to.

## The skill, and its honest limit

All four stages come out of one repository, and the skill is named at each stage of the film: it holds
the checklist, refuses to open a stage early, and will not start the picture before the sound is
frozen. **The link is in the description**, so nothing in the film dates when the address changes.

**Built and verified with Claude. Other models are untested** — unknown, not broken.

## Scope limits — do not narrate

- **Nothing specific to the hardware this repo is about.** No part numbers, no component values, no
  thermoelectric anything. The failures above are told generically, so the method travels.
- **No voice-engine or model names, no memory or GPU figures.** They date fast and turn a method film
  into a tool review.
- **No claim about how anything sounds** — not natural, not human, not good. There is no instrument for
  it here, and the film would be breaking its own rule while stating it.
- **No selling.** No superlatives about the tool, no promises about speed, no "effortless". The film
  states what the thing does and what it cannot do, and lets that be the argument.
- **No address, ever.** No URL spoken, no URL on screen, no repository name, no skill name. It goes in
  the video description, where it can change without touching a frame or a syllable.
- **Nothing about what is inside the repository beyond the four stages.** It is installed whole; which
  parts do what is not the viewer's problem.
- **No second copy of any number.** Every figure the narrator speaks comes from
  [`NUMBERS.md`](NUMBERS.md), by key, and nothing here restates one.
- **None of the verification machinery.** No tolerances, no gate names, no checklist internals, no
  loudness or alignment plumbing — all of it is in [`INTERNAL.md`](INTERNAL.md) and stays there.
