# Proposal: every film ends on an authorship card

**Status: waiting for the exact phrase.** This document holds skill text and nothing else. If it is
applied, the pull request that applies it deletes this file.

## What this changes

Three files, all additions — no existing sentence is reworded or removed:

| file | where | what |
|---|---|---|
| `education-video/interview.md` | the question list, and a new short section | one GATE 0 question: is this film about a project, and who gets credited |
| `education-video/SKILL.md` | GATE 3, GATE 5, GATE 6 | the mix carries the card's tail; the composition's duration excludes the card; the card is part of the film |
| `showoff-render/SKILL.md` | GATE 5 | the card as frames numbered past the last rendered one |

## Why

A film made with these skills ends on its last narrated line and carries no attribution. There is
nowhere in a finished film that says who made it, who built the thing it is about, that the
narration is synthetic, or who is answerable for the numbers. `education-video/SKILL.md` says
*"Nothing else: the film is the message"*, and the reference film's picture brief bans logos
outright — so the absence is deliberate, and this proposal is a change of mind rather than a
patch over an oversight.

The case for changing it: these films carry real numbers to people who will believe them. The
skill already accepts that premise — *"A beautiful film that overclaims is worse than no film"* —
and it already requires the source document to state its evidence status before any claim. An
unsigned film asks a viewer to extend trust with nobody's name attached to it. The synthetic
narration sharpens it: the lab's acceptable-use statement asks that generated voice be disclosed,
and at present there is no place in a film where that disclosure could go.

**Be clear about the evidence behind this proposal: it is a direct commission, not friction
entries.** The usual and better route is a pattern of recorded runs arguing that a skill got
something wrong. Nothing here comes from that. It comes from the user asking for a standard
authorship card for every film, and settling its content, its style and its behaviour in an
interview. A reviewer should weigh it on that basis and not look for entries that do not exist.

## What already exists, and is not part of this

The tooling is built, tested and in the repository at `_shared/endcard/`. It builds a card from a
per-film credits file, checks it against the shared composition rules in a browser, renders it
through the film's own exporter so it stream-copies onto the picture, and joins the two. None of
that needed a skill edit, and none of it is proposed here.

**Only the gate text is.** Without it the card exists and nothing tells anyone to make one.

## The cost, stated plainly

**A six-second card needs six more seconds of audio.** The delivery step refuses a picture and an
audio track that differ by more than one frame. So the card is not a GATE 6 afterthought: either
the mix is rendered longer at GATE 3, or the locked mix is padded with silence and the film goes
quiet under the card. The first is better and it is why the question belongs in the interview.

That is the whole cost, and it is the reason the GATE 3 and GATE 5 additions below exist rather
than a single GATE 6 paragraph.

---

# The text

## 1. `education-video/interview.md`

**In "Cover at minimum, one question each", insert after item 11 and renumber nothing else —
this becomes item 12:**

```
12. **Credits** — is the film about something somebody built? If it is, who built it, and who
    else must appear: sources, supervisors, funder, the institution answerable for it.
```

**And add this section, immediately after "Where the film's files live":**

```
## Who the film credits

**Ask this at GATE 0, not at the end.** Every film ends on an authorship card, and a card
assembled after the picture is locked is a list of whoever happened to be in the room. The
question is short and it has one branch that matters:

**Is this film about a project — something somebody designed, built, measured or wrote?** If it
is, the card credits those people as well as the film's, and it will not build without them. A
film about a project that credits only its film-makers takes credit for someone else's work. If
it is not — an explainer about a standard, a method, an idea — the film's own credits are the
whole list, and there is no project block.

Then collect, in the same window or the next: who wrote and produced the film, whose voice it is
and whether it is synthetic, who built the project and in what roles, the source document,
image and music licences, supervisors, funder, the institution that stands behind the claims,
and where a viewer takes a correction.

**Ask how long the card holds, too**, and carry the answer to GATE 3. Six seconds is the
default. It is not a picture decision: the mix has to be that much longer or the film will not
deliver, which is settled at the audio gate and expensive to revisit after it.
```

## 2. `education-video/SKILL.md`

**In GATE 3, append to the paragraph beginning "The stage is not over when the voice is":**

```
**The mix runs past the last word by the length of the end card**, which GATE 0 settled — six
seconds unless the user said otherwise. Let the music tail run out underneath it. This is the
one thing about the card that cannot be fixed later: the delivered film's picture and audio may
differ by no more than one frame, so a mix locked at the length of the narration forces the card
to be silent, or forces this gate open again after it was approved.
```

**In GATE 5, append to the paragraph beginning "The duration lives in the page":**

```
**The card is not part of this composition.** Its duration is the narration's, not the film's
total: the card is built and rendered separately and joined to the picture at GATE 6, so that a
change to a credit never costs a re-render of the film.
```

**In GATE 6, insert before the paragraph beginning "Measure the file you are handing over":**

```
**The film ends on its authorship card, and the card is not optional.** It says who made the
film, who built the thing it is about, what in it was generated, who stands behind the claims
and where a viewer takes a correction. `_shared/endcard/` builds it from a credits file kept
with the film — never inside the skill — checks it against the same composition rules the
picture obeys, and renders it through this skill's own exporter so it joins the picture as a
stream copy with neither re-encoded. Its own README is the method.

**The disclosure line is required and it is the reason the card exists.** The narration is
synthetic and the picture was generated; a film that does not say so is asking a viewer to
assume otherwise. Never ship a card whose disclosure was left blank because the film "obviously"
looks generated.

**Join the card before the mux, not after.** The joined picture is what `deliver_film.py` takes
as `--picture`, and the audio it takes is the longer mix from GATE 3. If that mix was locked at
the narration's length, pad it with silence and say plainly that the film goes quiet under the
card — never quietly shorten the card to fit the audio that exists.
```

## 3. `showoff-render/SKILL.md`

**In GATE 5, append after "Render once, at final resolution, to the film's directory":**

```
**Then put the authorship card on the end.** `_shared/endcard/` renders it as PNGs numbered past
the last rendered frame, at the render's own width and height, and the frame encoder picks them
up because it globs and sorts — so the card costs no video work and no re-encode. It credits
whoever built the hardware as well as whoever made the film, and it states that the footage is
generated. A cinematic render of somebody else's board that carries no attribution is the case
this exists for.
```

---

## What a reviewer should push back on

- **The card is a change of mind about "the film is the message".** That line is good and this
  weakens it. The counter-argument is that it was written about *chat noise at handover*, not
  about the film's own content — but a reviewer is entitled to disagree.
- **Six seconds is a real cost** on a ninety-second film, and nobody has yet watched one end this
  way. The first film to use it is the evidence, and it does not exist.
- **`showoff-render` films ship silent**, so its card costs nothing in audio and everything in
  screen time. It may want a shorter default than six seconds.
- **None of the tooling has run on a finished film.** It has been proven end to end on a
  throwaway clip — the join is frame-exact and the stream hash is unchanged — but the first real
  film is still the one that tests it.
