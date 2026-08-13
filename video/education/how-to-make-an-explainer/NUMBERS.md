# Numbers — the one home

Every figure this film speaks lives here and nowhere else. [`SOURCE.md`](SOURCE.md) refers to these
keys; the script traces each spoken number to a row. **Nothing gets a second copy** — not in the
script, not in the picture brief, not in a caption.

Re-derive every `measured` row with [`tools/verify_numbers.py`](tools/verify_numbers.py). The
`recorded` rows cannot be re-derived, and say so.

| key | value | grade | how |
|---|---|---|---|
| `REF.duration` | 338.100 s | measured | `ffprobe` on the delivered file |
| `REF.picture` | 1920×1080, 30 fps | measured | same probe |
| `REF.scenes` | 9 | measured | parsed from its script |
| `REF.cues` | 49 | measured | parsed from its script |
| `REF.words` | 689 | measured | parsed; a word is a token carrying a letter or digit |
| `REF.wpm` | 122.3 | measured | `REF.words` over `REF.duration` |
| `REF.slot_min` | 2.3 s | measured | parsed from its script |
| `REF.slot_max` | 13.0 s | measured | parsed from its script |
| `REF.slot_mean` | 6.88 s | measured | parsed from its script |
| `REF.hole_min` | 0.7 s | measured | scene start to first line, all 9 scenes |
| `REF.hole_max` | 1.9 s | measured | same |
| `REF.table_vs_file` | 0.000 s | measured | scene table span against the probed duration |
| `REF.traced` | 43 | recorded | counted when the script was written; not re-derivable |
| `TRIAL.cues` | 46 | measured | script recovered from git |
| `TRIAL.words` | 746 | measured | same, same word definition |
| `TRIAL.duration` | 237.6 s | recorded | the master was deleted with the film |
| `TRIAL.wpm` | 188.4 | reasoned | `TRIAL.words` over a recorded duration, so no better than it |
| `TRIAL.aligned` | 742 | recorded | word-level caption alignment, at the time |
| `VOICE.binned` | 2 | recorded | complete soundtracks discarded after passing every measurement |
| `TRIAL.reworded` | 5 | recorded | lines rewritten after a check caught the recording saying something else |
| `TOL.boundary` | 0.1 s | specified | the method's own limit, not a measurement |
| `TOL.total` | 0.05 s | specified | same |
| `FILM.runtime` | ~5 min | decided | raised from ~4 min when the premise changed; [`BRIEF.md`](BRIEF.md) |
| `FILM.scenes` | 8 | decided | raised from 7 when stage 4 became its own beat — the paste |
| `FILM.words` | ~890 | decided | tracks `FILM.runtime`; a budget, not a measurement |
| `DELIVER.picture` | 1920×1080, 30 fps, 16:9 | decided | stage 0; this film's own delivery spec |

A fifth grade appears above: **decided**. It is not evidence about the world, it is a choice this
film made, and the film must never speak one in a measuring voice.

## Reconciled, because the two films were counted differently

The reference film's script states its own length as 704 words, which is `REF.words` plus its 15
standalone em dashes counted as words. The trial film's 746 was recorded without counting its 5. So
the two films' words-per-minute figures were computed on different definitions of *word* and were
never comparable — the kind of quiet disagreement a second copy of a number produces. One definition
now applies to both: **a token counts only if it carries a letter or a digit.** Under it, 704 is wrong
and 746 reproduces exactly.

## Rounding for the narrator

Rounding is the only transform the script may apply, and never past the precision here. `REF.duration`
may be spoken as *"five and a half minutes"*; `REF.slot_mean` as *"about seven seconds"*. A number
this table does not carry may not be spoken at all.
