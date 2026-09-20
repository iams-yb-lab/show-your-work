# Closing credit slate

Every film made with this skill ends on a credit slate held for 2–3 seconds: the lab's logo and
name, the video title, the release date, the lab website as text and QR code, and a bottom strip of
the organisations that support the lab. The layout is fixed here; a project describes its lab once
in a `slate.json` and supplies a title and date per film.

```bash
pip install segno playwright                     # once
python build_slate.py --config /path/to/slate.json \
    --title "How an ECDL picks its colour" --date 2026-10-01 --out out/A1_slate --png
```

`slate.json` fields: `lab_name`, `subline`, `url`, `lab_logo {file, height}`, `supporters_caption`,
`supporters [{name, file, height}]`, `seconds`. File paths are relative to the JSON. Logo heights are
in pixels on the 1920×1080 canvas; choose them so marks of different aspect ratio read as equal weight.
The first project to use this is the Animator repository, whose configured copy lives in its `brand/`
directory with the logos in `Assets/`.

In the film: the composition shows the slate from `duration − seconds` to the end; the narration
master must carry that much silence at its tail before it is locked. Bilingual films use the same
slate with the title in each language.
