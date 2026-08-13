# Narration — scene 1, board assembly

For the 32.5 s assembly animation (`out/anim/assembly_purple.mp4`). Timecodes are the
animation's own beats, taken from the schedule `animate_assembly.py` prints, so a line lands
while the thing it names is still moving. **If the animation is retimed, re-read that
schedule rather than nudging these by ear.**

Written to be *said*, not read: short clauses, one idea each, no subordinate stacks. Total
78 words over 32.5 s is about 145 words per minute — deliberately under conversational pace,
because the viewer is also looking at something.

| in | out | frames | on screen | line |
|---|---|---|---|---|
| 0:00 | 0:03 | 1–90 | bare board | "One bare board. A hundred and sixty-three millimetres by a hundred." |
| 0:03 | 0:09 | 90–276 | 31 resistors, then 51 ceramics | "Thirty-one chip resistors go down first. Then fifty-one ceramic capacitors — the network every measurement rests on." |
| 0:09 | 0:13 | 276–396 | diodes, regulator, reference, headers | "Diodes, the regulator, the voltage reference. Then the headers." |
| 0:13 | 0:16 | 396–480 | four Phoenix terminal blocks | "Screw terminals: the thermistor comes in here, the cooler here." |
| 0:16 | 0:18 | 480–540 | inductors, trimmers, switch, bulk cap | "Inductors, three trimmers, and the bulk capacitor." |
| 0:18 | 0:20 | 540–600 | Harting DIN 41612 | "A sixty-four-way connector to the rack." |
| 0:20 | 0:24 | 600–720 | ADC descends and lands | "The AD7124-8. Twenty-four bits, and the reason a millikelvin can be seen at all." |
| 0:24 | 0:28 | 720–830 | TEC driver descends and lands | "The MAX1968 drives the cooler — about three amps, either direction." |
| 0:28 | 0:31 | 830–930 | Teensy descends and lands | "And the controller. The loop closes here, on the board, not over a network." |
| 0:31 | 0:32.5 | 930–974 | held hero shot | "One millikelvin, peak to peak, held for an hour." |

## Delivery notes

- **Leave the last line alone in the silence.** It is the spec, and the only claim in the
  script that the project has to earn on the bench. Do not talk over the hero shot.
- **"AD7124-8" is said "A-D seven-one-two-four dash eight"**, and MAX1968 "max nineteen
  sixty-eight". Naming the parts out loud is the point — it is what makes the animation a
  technical document rather than a graphic.
- Nothing here says "we designed" or "our board". The parts and the numbers carry it.
- The two hero lines sit *after* each part starts moving, not before: the viewer sees a
  component descend, then hears what it is.

## Facts used, and where each comes from

Every claim is checkable, because a narration track is the easiest place in a project for a
retired number to survive:

| claim | source |
|---|---|
| 163 × 100 mm | board edge bounding box, `dump_components.py` |
| 31 chip resistors, 51 ceramic capacitors | the group tally `animate_assembly.py` prints |
| 64-way connector | the `HARTING_09031646921` footprint's own pin count |
| 24-bit ADC | AD7124-8 datasheet |
| ~3 A either direction | the drive envelope in [`review-2026-08-10-drive-stage.md`](../../../../PCB/review-2026-08-10-drive-stage.md) |
| loop closes locally | firmware ground rule, `CLAUDE.md` |
| 1 mK p-p over one hour | the project spec in [`../../docs/sources.md`](../../../../docs/sources.md) |

**Not said, on purpose:** any layer count (unverified), any accuracy figure (the spec is
*stability*, and saying "accuracy" would misdescribe the whole design), and the word
"Teensy" is left as "the controller" — the model on screen is a Teensy 3.6 standing in for
the 4.1 the board carries, so naming it would put a wrong part number in the audio.
