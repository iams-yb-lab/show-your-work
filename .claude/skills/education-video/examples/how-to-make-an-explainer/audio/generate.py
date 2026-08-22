#!/usr/bin/env python3
"""
generate.py — seeded takes of whole performance sections. Runs in the chatterbox venv.

One narrator for the whole film: the approved `warm-natural` profile, its prompt WAV unmodified, and
one fixed parameter set. **Only the seed varies between takes** — a parameter sweep would change
narrator identity, which is the one thing that has to hold still.

Nothing here trims, normalises, denoises or resamples anything. The model's own beginning and ending
are the deliverable.

    python3 audio/generate.py --sections A,L,Q,R --takes 2
    python3 audio/generate.py --all --takes 4
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sections import load  # noqa: E402


def skills_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "_shared").is_dir() and (d / "natural-voice").is_dir():
            return d
    raise SystemExit("not inside a skills tree")


AUDIO = Path(__file__).resolve().parent
FILM = AUDIO.parent
SKILLS = skills_root(AUDIO)
PROFILE_DIR = SKILLS / "natural-voice/profiles/warm-natural"
OUT = SKILLS.parents[1] / "out/education/how-to-make-an-explainer/takes"

# Held constant for every take of every section. Inside the profile's proven range, and the same
# exaggeration and cfg_weight the prompt itself was selected at.
PARAMS = {"exaggeration": 0.36, "cfg_weight": 0.42, "temperature": 0.78}
CONDITIONING_EXAGGERATION = 0.36


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_for(section_id: str, take: int) -> int:
    """Deterministic, and distinct per section and take, so any take can be reproduced alone."""
    base = sum((ord(c) - 64) * 97 for c in section_id)
    return 7_300_000 + base * 131 + take * 29


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", help="comma-separated ids, e.g. A,L,Q,R")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    profile = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
    prompt = PROFILE_DIR / profile["prompt_file"]
    actual = sha256(prompt)
    if actual != profile["prompt_sha256"]:
        raise SystemExit(f"prompt WAV has changed: {actual} != {profile['prompt_sha256']}. "
                         f"A changed prompt is a new profile, never an edit to this one.")

    wanted = None if args.all else {s.strip().upper() for s in (args.sections or "").split(",") if s.strip()}
    if not args.all and not wanted:
        raise SystemExit("give --sections A,B,… or --all")
    chosen = [s for s in load() if args.all or s["id"] in wanted]
    missing = (wanted or set()) - {s["id"] for s in chosen}
    if missing:
        raise SystemExit(f"no such section(s): {sorted(missing)}")

    args.out.mkdir(parents=True, exist_ok=True)
    from chatterbox.tts import ChatterboxTTS

    model = ChatterboxTTS.from_pretrained(device="cuda")
    model.prepare_conditionals(str(prompt), exaggeration=CONDITIONING_EXAGGERATION)
    print(f"chatterbox {importlib.metadata.version('chatterbox-tts')}, sr={model.sr}, "
          f"prompt {profile['prompt_sha256'][:12]}", flush=True)

    report = []
    for section in chosen:
        for take in range(1, args.takes + 1):
            target = args.out / f"{section['id']}_take{take}_raw.wav"
            seed = seed_for(section["id"], take)
            if not target.exists():
                torch.manual_seed(seed)
                wave = model.generate(section["said"], **PARAMS)
                audio = wave.detach().cpu().numpy().squeeze().astype(np.float32)
                # FLOAT, not PCM_24: this model's output goes above full scale on some seeds
                # (1.09 and 1.10 were measured here), and an integer write clips it silently.
                # Level is reduced once, downward, at delivery — never in the raw take.
                sf.write(target, audio, model.sr, subtype="FLOAT")
            else:
                audio, rate = sf.read(target, dtype="float32", always_2d=False)
                if rate != model.sr:
                    raise SystemExit(f"unexpected sample rate in {target}: {rate}")
            row = {
                "section": section["id"], "take": take, "seed": seed, "params": PARAMS,
                "scene": section["scene"], "cues": section["cues"], "words": section["words"],
                "text": section["text"], "said": section["said"],
                "path": str(target), "duration_s": round(len(audio) / model.sr, 3),
                "sample_rate": model.sr, "peak": round(float(np.max(np.abs(audio))), 5),
                "sha256": sha256(target),
            }
            report.append(row)
            print(f"  [{section['id']}] take {take}  {row['duration_s']:6.2f} s  "
                  f"peak {row['peak']:.3f}  seed {seed}", flush=True)

    meta = {
        "profile": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "prompt": str(prompt),
        "prompt_sha256": profile["prompt_sha256"],
        "model": "ChatterboxTTS",
        "chatterbox_package_version": importlib.metadata.version("chatterbox-tts"),
        "torch_version": torch.__version__,
        "sample_rate": model.sr,
        "params_held_constant": PARAMS,
        "conditioning_exaggeration": CONDITIONING_EXAGGERATION,
        "varied": "seed only",
        "script_sha256": sha256(FILM / "script/voiceover-script.md"),
        "takes": report,
    }
    out_json = args.out.parent / "generation.json"
    existing = {}
    if out_json.exists():
        existing = json.loads(out_json.read_text(encoding="utf-8"))
        known = {(r["section"], r["take"]) for r in report}
        meta["takes"] = [r for r in existing.get("takes", [])
                         if (r["section"], r["take"]) not in known] + report
    out_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"{len(report)} take(s) written; record: {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
