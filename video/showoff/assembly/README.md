# Showoff — the assembly film

84 seconds of the board building itself, rendered from `PCB_new.kicad_pcb`. Nothing here is
placed by hand: the parts, their order and the camera all come off the board.

| | |
|---|---|
| [`picture/`](picture/) | board → `.pcb3d` → Blender → frames → a silent MP4. Start at its [README](picture/README.md) |
| [`audio/`](audio/) | narration and score. [`AUDIO-LOG.md`](audio/AUDIO-LOG.md) is what was tried and rejected; [`VOICE-LOG.md`](audio/VOICE-LOG.md) is how the approved v7.2 was made |
| [`script/`](script/) | the narration tables and the animation brief |
| [`gallery/`](gallery/) | the four committed stills |
| [`RENDER-LOG.md`](RENDER-LOG.md) | the picture thread, session by session |

The audio reads the picture's own schedule: `audio/audio_cues.py` imports
`picture/animate_assembly_v2.py` and re-runs it, so all 110 landings sit on the frame the
renderer keyed them to. Retiming the animation moves the score with it.

**The board is not in this repository** — this pipeline renders whatever `.kicad_pcb` you give it,
and `picture/{render,animate,animate_v2}.ps1` now require `-Board` rather than defaulting to one
project's file. The two `script/narration-assembly*.md` traces cite that board's review and spec by
name, as text: they are a record of where those claims came from, not links you can follow.
