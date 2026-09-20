# Friction from `iams110-shayne`

Raw entries, newest last, awaiting review. Format and redaction rule: `feedback/README.md`.

### 2026-08-20 · education-video
- **complaint:** User picked education-video after I recommended slide-deck
- **mistake:** Front-loaded a recommendation against the animated branch on deadline grounds before confirming the deadline was real; the footer date was stale
- **fix:** Asked branch, audience and deadline in one AskUserQuestion window, then accepted the choice and restated the SVG-rework cost as a cost rather than a blocker
- **rule:** Confirm the constraint before arguing from it — a recommendation built on an unverified deadline has to be walked back the moment the date is questioned
- **cost:** 1 turn

### 2026-08-21 · education-video
- **complaint:** It is honestly a bit indefinite... especially when it comes to understanding which laser beam an atom will scatter
- **mistake:** Wrote a scene asserting sigma-plus/minus without ever defining what circular polarization is, and buried the payoff question in an aside
- **fix:** Split one scene into six, built circular polarization from the rotating E field, and stated the load-bearing fact (a photon's spin points along its own line of travel) so the answer became forced rather than asserted
- **rule:** Before a scene can assert a rule, name the physical fact the rule rests on -- if the viewer cannot derive it, you are asking them to memorise
- **cost:** 1 gate rerun

### 2026-08-21 · natural-voice
- **complaint:** no it sux
- **mistake:** Offered the stored warm-natural profile as the recommended voice on the strength of its register matching the brief, without flagging that it is male and the brief never settled narrator gender
- **fix:** Ran the full prompt-selection procedure on six female candidates, one variable, loudness-matched before listening; user chose af_heart
- **rule:** Voice gender is a GATE 0 question, not an attribute of a profile match -- ask it before recommending any stored identity
- **cost:** 1 full render discarded

### 2026-08-21 · education-video
- **complaint:** the html package is downloaded please give me the completed mp4 video
- **mistake:** First serial render ran at 2.7 fps (~100 min) and the mux used -shortest, which silently removed four frames from the end of the film
- **fix:** Parallelised across four browsers since seeked frames are deterministic (11 min), verified per-segment frame counts before concatenating, and dropped -shortest after proving the concat itself was frame-exact
- **rule:** Count the frames in the artifact you deliver, not in the pieces you built it from -- a mux flag can shorten a film that every input got right
- **cost:** 1 render discarded

### 2026-09-20 · education-video
- **complaint:** bench rule and verdict endings offered; gate ceremony; skill jargon in documents
- **mistake:** followed the skill's verdict requirement and interview ceremony literally and let its vocabulary into documents and options
- **fix:** skill reworked to process-only; content standard moved to a project style guide
- **rule:** the skill has no opinion on content; its vocabulary never reaches deliverables or questions
- **cost:** 3 turns
