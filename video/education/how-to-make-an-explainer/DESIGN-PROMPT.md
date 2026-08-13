# Paste this into Claude Design

You are drawing the picture for a finished explainer video. **The audio already exists and is
final.** Every duration below is decided; nothing about the sound may be re-cut, re-timed or
regenerated to suit the picture. The picture fills the time it is given.

## What you are delivering

**A self-contained HTML bundle that plays the film — not a video file.** You cannot encode video;
your encoder only fires from a human clicking Export, so do not try, and do not ask for ffmpeg to
be run on your side. Hand back the page. Rendering it to a 1080p file is done here.

Two things about that page, because they are the ones that go wrong:

- **Embed the combined audio track named below** — narration *and music*, 270.3 s.
  A bundle that carries the narration alone is silent where the music should be, and that has
  already happened once on this film.
- **Leave burned-in captions off.** The caption file ships separately; frames with subtitles baked
  into them cannot be un-baked.

## Where everything is

| file | what it is |
|---|---|
| `C:\temperature-controller\video\out\education\how-to-make-an-explainer\master\combined-audio.wav` | **the audio for the page** — narration and music, lossless 48 kHz stereo, -14.12 LUFS, -1.17 dBTP. Use this one. |
| `C:\temperature-controller\video\out\education\how-to-make-an-explainer\master\narration-master.wav` | narration only, no music. **Not this one** — it is the mistake to avoid. |
| `C:\temperature-controller\video\education\how-to-make-an-explainer\script\captions.srt` | captions, timed off the audio, one entry per line of narration |
| `C:\temperature-controller\video\out\education\how-to-make-an-explainer\cues.json` | the machine-readable cue sheet this prompt was generated from |
| `C:\temperature-controller\video\education\how-to-make-an-explainer\images\MANIFEST.md` | the image manifest. **It is deliberately empty** — nothing in this film is photographed. |
| `C:\temperature-controller\video\education\how-to-make-an-explainer\SOURCE.md` | the source document, if you need the meaning behind a line |

## Delivery spec

- **1920×1080, 16:9, 30 fps** — the page must render at that size without cropping or letterboxing
- **Exactly 270.3 s of timeline**, ending when the audio ends
- Captions available but **off by default**; the `.srt` is delivered separately

## The look

Dark, typographic motion graphics. The film's subject is a process, so the picture is
built from the artifacts of that process rather than from stock imagery: a checklist that ticks, a
document with one fact lit up, a script with each line's seconds drawn beside it, a waveform, a scene
table, a prompt being pasted. Nothing is photographed. One accent colour, used to mean "this is the
thing being talked about right now" and never decoratively. Type is the main character; motion is slow
and purposeful, never bouncy. Every scene opens on a held frame so the music mark lands on the cut.

## Scene table — locked

| scene | title | in | out | duration | hole before first word |
|---|---|---|---|---|---|
| 1 | Where you're standing | 0:00.0 | 0:23.2 | 23.2 s | 1.00 s |
| 2 | Step one | 0:23.2 | 0:43.0 | 19.7 s | 1.00 s |
| 3 | Three things it has to do | 0:43.0 | 1:13.5 | 30.6 s | 1.00 s |
| 4 | Four stages, and who does what | 1:13.5 | 1:48.7 | 35.1 s | 1.00 s |
| 5 | Stage one, and stage two | 1:48.7 | 2:25.1 | 36.4 s | 1.00 s |
| 6 | Stage three, the sound | 2:25.1 | 3:28.4 | 63.3 s | 1.00 s |
| 7 | Stage four, one paste | 3:28.4 | 3:54.1 | 25.8 s | 1.00 s |
| 8 | Four stages, and where to start | 3:54.1 | 4:30.3 | 36.2 s | 1.00 s |

**Scene boundaries came from the audio and are contiguous** — each scene ends exactly where the
next begins, and the table sums to the file duration. The hole at the top of every scene is
silence with a music mark in it: put the cut there, and hold the first frame of the new scene
through it. Do not speak-over it and do not fill it with motion.

## Cue sheet, with one instruction per line

`start` is when the words begin. `slot` is how long that line has before the next one starts —
that is the time its visual has, and no more.

### Scene 1 — Where you're standing  (0:00.0 → 0:23.2)

**0:00.9** · slot 4.9 s · line 1

> You finished the thing. Now other people have to understand it, and none of them were there.

A finished thing, drawn as a clean geometric object, complete and still. Then faces or figures appear around it as abstract marks — an audience arriving after the fact.

**0:05.8** · slot 3.7 s · line 2

> You want a few clean minutes that explain it, not a course.

The object shrinks into a video frame: a small player rectangle with a short timeline. Beside it, the words A FEW CLEAN MINUTES.

**0:09.5** · slot 2.4 s · line 3

> And you don't want to become a video producer to get one.

A crowded editing timeline slides in from the side, dense with tracks, and is pushed back out. It should look like work nobody wants.

**0:11.9** · slot 4.6 s · line 4

> You want to hand the work to something that can do it quickly, and still end up with something you'd put your name on.

A hand-off gesture, abstract: the object passes from one side of frame to a simple machine outline on the other, which returns it polished.

**0:16.5** · slot 7.8 s · line 5

> That's a reasonable thing to want. It's also, now, a reasonable thing to get — as long as you know which parts are yours to decide.

Two labels settle side by side: THINGS IT DECIDES and THINGS YOU DECIDE. The second is the accent colour. Hold.

### Scene 2 — Step one  (0:23.2 → 0:43.0)

**0:24.3** · slot 6.0 s · line 6

> Open the Claude app, or VS Code with Claude in it. Ask it to install the repository linked below this video.

An application window opens, drawn not photographed, with a text box in it. A line of typed instruction appears: install the repository. Then VS CODE appears as a second, equal option.

**0:30.3** · slot 5.5 s · line 7

> That's the setup. Nothing to configure, no editing software to learn, nothing else to download.

Three struck-through labels stack up: CONFIGURE, EDITING SOFTWARE, DOWNLOADS. Each one greys out as it is dismissed.

**0:35.8** · slot 3.5 s · line 8

> From there you talk in plain language, and Claude runs four stages.

The window recedes and four numbered plates appear in a row, unlabelled for now — the four stages, arriving as shapes before they get names.

**0:39.4** · slot 4.7 s · line 9

> It stops at every one to show you what it made and ask whether it's right.

A single plate lifts and a small question mark rests on it, with the word APPROVE beneath. It waits, visibly, rather than advancing.

### Scene 3 — Three things it has to do  (0:43.0 → 1:13.5)

**0:44.1** · slot 3.6 s · line 10

> Before any of that, three things your video has to do.

Clear to ground. THREE THINGS counts up as three empty rows.

**0:47.7** · slot 6.9 s · line 11

> One. The people you aimed it at understand it — the ones you named before writing a word. Aim at everyone, land on nobody.

Row one fills: a target with one figure standing at its centre and a crowd greyed out behind it. Label AIMED AT SOMEONE.

**0:54.7** · slot 5.5 s · line 12

> Two. Everything in it is true, and you can say why. If something isn't built or measured yet, the video says so.

Row two fills: a claim in quotation marks with a thin line drawn from it down to a document beneath. Label TRUE, AND YOU CAN SAY WHY.

**1:00.1** · slot 4.8 s · line 13

> A confident voice over a wrong number does more damage than saying nothing.

The same claim, now with a wrong number in it, glowing in the accent colour while a confident waveform runs under it. Uncomfortable, briefly.

**1:04.9** · slot 5.1 s · line 14

> Three. Nothing sounds wrong: no clipped word, no hurried sentence, no caption running behind.

Row three fills: a caption box drifting a beat behind a waveform, then snapping into place. Label NOTHING SOUNDS WRONG.

**1:10.0** · slot 5.2 s · line 15

> Your viewer won't know why they stopped trusting you. Only that they did.

A viewer figure turns away. No explanation on screen. Hold on the empty frame a moment longer than feels comfortable.

### Scene 4 — Four stages, and who does what  (1:13.5 → 1:48.7)

**1:15.1** · slot 3.7 s · line 16

> Four stages, one order, each finished before the next begins.

The four plates return, now in a single row with an arrow between each. This is the architecture card and it should read as the film's spine.

**1:18.8** · slot 3.1 s · line 17

> The document: everything true about your subject, written down and checked.

Plate one lights: THE DOCUMENT, with a page of text behind it and one line highlighted.

**1:21.9** · slot 4.3 s · line 18

> The script: the words, in order, each with the seconds it needs.

Plate two lights: THE SCRIPT, with lines of narration each carrying a small bar showing its seconds.

**1:26.2** · slot 4.0 s · line 19

> The sound: one recording, frozen — from here on, it owns the clock.

Plate three lights: THE SOUND, with a waveform, and a clock icon moving from the picture plate onto this one.

**1:30.2** · slot 3.6 s · line 20

> The picture: frames cut to fill lengths already decided.

Plate four lights: THE PICTURE, drawn as frames filling a fixed-width box that is already the right size.

**1:33.7** · slot 4.3 s · line 21

> Claude does all four. The drafting, the counting, the recording, the checking.

A bracket appears around all four plates, labelled CLAUDE. Small motion inside each plate — work happening.

**1:38.1** · slot 6.0 s · line 22

> You do the three things it can't: say who this is for, say what's actually true about your work, and say yes or no at each stage.

Three items step outside the bracket: WHO IT'S FOR, WHAT'S TRUE, YES OR NO. Accent colour, larger than the plates.

**1:44.1** · slot 5.8 s · line 23

> That last one isn't a formality. A model can't know a number has gone stale.

A number on the document quietly changes from fresh to stale — same digits, different colour — while the machine outline carries on unaware.

### Scene 5 — Stage one, and stage two  (1:48.7 → 2:25.1)

**1:49.8** · slot 4.7 s · line 24

> Stage one, the document. Claude asks what the thing is, and writes it down with you.

Scene opens on plate one, enlarged. A conversation forms as two columns of short lines, a document assembling on the right as it goes.

**1:54.5** · slot 5.1 s · line 25

> It presses on which of your numbers are measured and which are only planned, and won't let the same fact in twice.

Two stamps drop onto figures in that document: MEASURED and PLANNED. Then a duplicated fact appears twice and one copy is struck out.

**1:59.6** · slot 3.8 s · line 26

> Your part: tell it the truth about your own work, and say when the document is right.

The document turns to face the viewer. A single approval mark waits on it, accent colour.

**2:03.4** · slot 4.6 s · line 27

> Because nothing later can repair a wrong number. Animation only enlarges it.

A wrong number in the document is blown up until it fills the frame. Nothing else changes; it just gets bigger.

**2:08.0** · slot 8.0 s · line 28

> Stage two, the script. Claude turns the document into the words, in order, each line given the seconds it needs so nothing has to be hurried.

Cut to plate two. The document's lines flow into script lines, and a bar grows beside each one, longer for longer lines. No two bars the same length.

**2:16.0** · slot 2.5 s · line 29

> It refuses any claim the document doesn't make.

A line arrives without a thread back to the document and is refused — it slides out of frame.

**2:18.5** · slot 7.9 s · line 30

> Your part: read it once. It's the last cheap moment to change a word — after this, a change costs a re-recording.

One script line is held under a cursor while a re-record symbol appears beside it and is crossed out. Label THE LAST CHEAP MOMENT.

### Scene 6 — Stage three, the sound  (2:25.1 → 3:28.4)

**2:26.4** · slot 3.3 s · line 31

> Stage three. Claude records it, and freezes one file.

Cut to plate three. A waveform draws itself left to right and then locks, with a padlock or frozen edge — one file, finished.

**2:29.8** · slot 4.0 s · line 32

> That happens before a single frame exists — and it's the one idea here worth keeping.

The picture plate is shown empty and unstarted beside the finished waveform. Emphasise the order: sound solid, picture blank.

**2:33.8** · slot 5.0 s · line 33

> A finished picture has a fixed length. Change what's on screen halfway through and you render it again.

A picture strip of fixed width. A frame in its middle is changed and the whole strip has to be redrawn — show the redraw cost as the strip flickering back to the start.

**2:38.8** · slot 6.7 s · line 34

> Speech has no such give. A sentence takes as long as it takes, and read faster, your listener hears the hurry instead of the sentence.

A sentence drawn as an elastic band that will not compress. Squeeze it and the words visibly crowd; release and they settle.

**2:45.5** · slot 4.0 s · line 35

> So whichever one you finish first becomes the box the other has to fit.

Two boxes, one rigid and one elastic, and whichever is drawn first becomes the container the other must fit inside. Show it both ways.

**2:49.5** · slot 5.9 s · line 36

> Finish the picture first and the sentence is what gets damaged: cut short, hurried, or spliced — and all three are audible.

Picture-first: the sentence is cut short, hurried, then spliced from two pieces with a visible seam. All three damages named on screen, briefly.

**2:55.5** · slot 5.9 s · line 37

> Finish the sound first and the picture absorbs it instead. A diagram resting a moment longer is invisible.

Sound-first: the picture box simply stretches to fit, and a diagram sits a moment longer. Nothing breaks. No label needed.

**3:01.4** · slot 3.0 s · line 38

> So the thing that can't be squeezed sets the clock.

One line of type alone on the ground: THE THING THAT CAN'T BE SQUEEZED SETS THE CLOCK.

**3:04.4** · slot 5.1 s · line 39

> From that one file, the captions come off word by word — and so does every length the picture gets cut to.

Captions drop out of the waveform one word at a time, each landing under the sound it belongs to. Then scene-boundary marks fall out of the same waveform.

**3:09.5** · slot 6.9 s · line 40

> Claude also checks the recording actually said the script. On one film, five lines were rewritten because a word had gone missing.

The script and the transcript sit side by side; one word differs and is ringed in the accent colour.

**3:16.4** · slot 6.5 s · line 41

> Your part: listen. Timing and pronunciation can be checked automatically. Whether it sounds like a person cannot.

Two checkmarks appear beside TIMING and PRONUNCIATION. A third row, SOUNDS LIKE A PERSON, stays empty — no mark is available for it.

**3:22.9** · slot 6.7 s · line 42

> Two complete soundtracks were thrown out here after passing every check there was. That's why the file comes to you.

Two finished soundtrack bars, both showing every check passed, both dropped into a bin. Then a single ear or listener mark replaces them.

### Scene 7 — Stage four, one paste  (3:28.4 → 3:54.1)

**3:29.6** · slot 5.5 s · line 43

> Stage four, the picture. Every length is already decided, so it has one job: fill the time it's given.

Cut to plate four. The scene table appears with its durations already filled in, and empty frames waiting inside each row.

**3:35.1** · slot 3.8 s · line 44

> And from where you sit, it's one step. Claude hands you a single prompt.

Everything collapses into one document: a prompt, shown as a single block of text with a copy button.

**3:38.9** · slot 6.2 s · line 45

> It already carries the scene list, what each scene shows, what the video should look like, and where every file is sitting on your disk.

Four contents fly into that block and settle: the scene list, what each scene shows, the look, and file paths.

**3:45.1** · slot 2.6 s · line 46

> You paste it into Claude Design, and wait.

The block is picked up and dropped into a second window. Then a wait — a held frame with a quiet progress mark.

**3:47.7** · slot 8.1 s · line 47

> What comes back is a finished video with the sound already in it. Not a silent picture you then have to combine with something.

A finished video plays back small in frame with a speaker mark lit beside it, next to a rejected alternative: the same frame with a crossed-out silent mark.

### Scene 8 — Four stages, and where to start  (3:54.1 → 4:30.3)

**3:55.8** · slot 4.9 s · line 48

> Document, script, sound, picture. Do it backwards and each step has its own price.

The four plates return in order, then reverse, and each reversal cracks — one at a time, not all at once.

**4:00.8** · slot 4.6 s · line 49

> Picture first is the normal way, and the expensive one: the sentence is what gets damaged.

Reversal one: the picture drawn first, and the sentence inside it breaking. Cost label: A RE-RENDER.

**4:05.4** · slot 5.1 s · line 50

> Document last, and the video becomes where your thinking happens — errors at full volume, in a confident voice.

Reversal two: no document, and the video becomes the place where the thinking happens — errors amplified through a loudspeaker shape.

**4:10.5** · slot 4.3 s · line 51

> Skip the script, and a problem you'd have fixed with a keystroke costs a whole re-record.

Reversal three: a keystroke versus a whole recording, drawn as two very different sized blocks.

**4:14.8** · slot 3.6 s · line 52

> Sound last, and nothing sets the clock, so every length is a guess.

Reversal four: no sound, and every duration on the scene table turns into a question mark.

**4:18.4** · slot 3.7 s · line 53

> All four stages come out of one repository. The link is below this video.

Clear to ground. One repository mark, and the words THE LINK IS BELOW THIS VIDEO. No URL on screen.

**4:22.1** · slot 4.8 s · line 54

> Built and verified with Claude. Other models haven't been tested — that's unknown, not broken.

Two lines of type, plain: BUILT AND VERIFIED WITH CLAUDE, and beneath it, OTHER MODELS UNTESTED. The second is deliberately not styled as a warning.

**4:26.9** · slot 3.4 s · line 55

> Now go and explain the thing you made.

The finished object from cue 1 returns, now with an audience around it that is facing it. Hold to the end of the audio.

## Do not draw

- **No photographs, no stock imagery, no logos.** The image manifest is empty on purpose.
- **No hardware, circuit boards, lab equipment or scientific instruments.** The film has to work
  for whatever the viewer built; naming a field narrows it.
- **No URLs, repository names, skill names or file paths on screen.** The link lives in the video
  description. Cue 53 says so out loud.
- **No product UI screenshots or recognisable brand chrome.** Draw a generic app window instead.
- **No tolerances, gate names, checklists internals, loudness figures or engineering plumbing.**
  The viewer came for a clear video, not for a quality system.
- **No claim about how anything sounds** — not natural, not human, not studio quality.
- **No number that is not spoken in the line it sits under.**
- **No bouncy, springy or comedic motion**, and no whooshes, ticks or transitions implying sound;
  the audio is finished and cannot accommodate them.

## Hand back the page, and say four things about it

No rendering, no muxing, no export click. Just the bundle, plus these four facts so the render on
this side does not have to be guessed at:

1. **which audio you embedded**, by filename, and whether it is the combined mix or narration only;
2. **the page's total timeline length**, in seconds, to three decimals;
3. **how the page is driven** — does it play on load, on a click, or from a JS timeline object, and
   is there a single call or variable that seeks to a given second;
4. **anything in it that is not deterministic** — random seeds, `Date.now()`, animations tied to
   wall-clock time rather than the timeline. A frame-by-frame render of a page that drifts will
   not match the audio, and that is the one failure that is invisible until the whole film is out.

**You have everything. Nothing here needs to be asked back.**
