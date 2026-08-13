# Narration — assembly v2, 84 s

For `out/anim/assembly_purple_v2.mp4`. **This table is the only home for the narration**:
[`tools/narrate.py`](../../../engine/narrate.py) parses it, so editing a line here changes the voice track
and nothing else needs touching. Frames are the animation's own schedule numbers, printed by
`animate_v2.ps1 -PlanOnly`; a line starts at `(frame − 1) / 30` seconds.

Eleven lines, 96 words over 84 s — about 69 words per minute, roughly half conversational pace.
That is the point: the viewer is watching something, most of the film is meant to be silent, and
a narrator who fills the gaps stops sounding certain. Each line names the thing that is on screen
*as it happens*, and nothing names a thing the picture is not showing.

| frame | at | on screen | line |
|---|---|---|---|
| 25 | 0.80 | bare copper-clad, camera already moving | It all begins with a piece of copper. |
| 190 | 6.30 | top etch front crossing the board | Everything that is not a path is taken away. |
| 440 | 14.63 | board turned over, bottom etch | Then the other side. |
| 620 | 20.63 | the top mask film touches down | A mask seals what must not be touched, and the pads are plated. |
| 800 | 26.63 | silkscreen drawing | And the board is given its names. |
| 900 | 29.97 | first supporting wave sets off | Then the parts arrive. A hundred and ten of them, each to one place. |
| 1534 | 51.10 | the Harting, landed and held | Sixty-four ways out to the rack. |
| 1732 | 57.70 | the ADC, landed | Twenty-four bits. The reason a millikelvin can be seen at all. |
| 1924 | 64.10 | the driver, landed | The driver moves heat in either direction. |
| 2152 | 71.70 | the controller, landed; camera retreating | And the controller, where the loop closes. |
| 2310 | 76.97 | light raking across the finished board | One millikelvin. Peak to peak. Held for an hour. |

## Delivery

- **Voice `en-GB-RyanNeural`, rate −12 %, pitch −4 Hz** — deep, calm, unhurried. Swap with
  `--voice`; `python tools/narrate.py --list` prints the candidates.
- **The last line is alone.** It lands after everything has stopped arriving, and it is the only
  claim the project still has to earn on the bench. Nothing plays over it but the music decaying.
- **The music ducks under speech and comes back up**, and there are no sound effects in this cut.
- Lines sit *after* each hero lands, never before: the viewer sees the part seat, then hears what
  it was. The one exception is the opening line, which has nothing to wait for.

## Facts used, and where each comes from

A narration track is the easiest place in a project for a retired number to survive, so every
claim is checkable and the ones that are *not* said are listed too.

| claim | source |
|---|---|
| a hundred and ten parts | the 110 non-DNP placed footprints with models in `out/scene/components_v2.json` — what lands on screen, not the board's full BOM (125 entries, 12 DNP) |
| sixty-four ways | the `HARTING_09031646921` footprint's own pin count, `C698356-CONN-TH_64P` |
| twenty-four bits | AD7124-8 datasheet |
| heat in either direction | MAX1968 topology, [`review-2026-08-10-drive-stage.md`](../../../../PCB/review-2026-08-10-drive-stage.md) |
| the loop closes on the board | firmware ground rule, `CLAUDE.md` |
| 1 mK peak to peak, one hour | the stability specification in [`../../docs/sources.md`](../../../../docs/sources.md) |

**Not said, on purpose:**

- 🔴 **The controller is never named.** The model on screen is a vendor **Teensy 3.6 assembly**
  standing in for the 4.1 the board carries — see *The Teensy* in [`RENDER-LOG.md`](../RENDER-LOG.md).
  Saying "Teensy 4.1" would put a part number in the audio that contradicts the picture.
- **No component counts except the 110 that land.** v1's narration said 31 resistors and 51
  ceramics; the live board is 36 and 52, which is exactly how a retired number survives.
- **No board dimensions, no layer count, and the word "accuracy" never appears** — the
  specification is *stability*, and calling it accuracy would misdescribe the whole design.
