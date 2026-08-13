# Upload copy

What goes in the box when the film is posted. **One blank to fill: the repository link.** The film says
"the link is below this video" at 4:18 (cue 53), so an empty description makes the narration wrong.

## Title

> How to make an explainer video about your own work

## Description

```
You finished the thing. Now other people have to understand it — and you don't want to become a
video producer to get one video.

This is the method, and it's four stages in one order: the document, the script, the sound, the
picture. Each one finishes before the next begins, and getting them out of order is what produces
narration cut off mid-sentence and captions running a beat behind.

Everything here is one installable skill. Open the Claude app, or VS Code with Claude in it, and ask
it to install the repository:

>>> FILL IN: repository link <<<

Built and verified with Claude. Other models are untested — that's unknown, not broken.

Captions are available as a subtitle track rather than burned into the frames.

00:00  Where you're standing
00:23  Step one
00:43  Three things it has to do
01:13  Four stages, and who does what
01:48  Stage one, and stage two
02:25  Stage three, the sound
03:28  Stage four, one paste
03:54  Four stages, and where to start
```

Chapter times are the scene in-points from
[`NUMBERS.md`](NUMBERS.md)'s timeline, rounded down to the second as YouTube requires.

## Uploading

- **Video:** `how-to-make-an-explainer-1080p.mp4` — 1920×1080, 30 fps, H.264 High, AAC 48 kHz stereo,
  −14.13 LUFS, faststart. Nothing to transcode before upload.
- **Subtitles:** upload `captions.srt` as an English track. Do not burn it in; the render deliberately
  has captions off.
- **Loudness:** already at the level streaming platforms normalise to, so it will not be turned down.

## If the link does not exist yet

Cue 53 is its own performance section — 3.7 s, one sentence, at 4:18. Re-recording that line alone is
minutes of work, so **the honest fallback is to re-record it** rather than post a film that points at
nothing. `audio/generate.py --sections R` regenerates it; the section boundary is a scene break, so
nothing else moves.
