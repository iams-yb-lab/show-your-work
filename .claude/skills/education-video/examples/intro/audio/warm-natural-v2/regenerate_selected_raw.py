"""Recreate only the approved Chatterbox performances without trimming their endings."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch


GROUPS = [
    [1, 2, 3], [4, 5, 6, 7], [8, 9, 10], [11, 12, 13, 14], [15, 16],
    [17, 18, 19], [20, 21], [22, 23], [24, 25, 26], [27, 28],
    [29, 30, 31], [32, 33], [34, 35], [36, 37, 38], [39, 40],
    [41, 42], [43, 44], [45, 46], [47, 48, 49],
]

# These are the takes that passed the original Whisper, pitch, and timing gates.
SELECTED_GROUP_TAKES = {
    1: 1, 2: 3, 3: 2, 4: 1, 5: 3, 6: 4, 7: 3, 8: 3, 9: 2,
    10: 2, 11: 1, 12: 1, 13: 4, 14: 2, 15: 4, 16: 4, 17: 1,
    18: 4, 19: 2,
}

GROUP_PARAMS = {
    1: {"exaggeration": 0.36, "cfg_weight": 0.42, "temperature": 0.80},
    2: {"exaggeration": 0.40, "cfg_weight": 0.38, "temperature": 0.78},
    3: {"exaggeration": 0.32, "cfg_weight": 0.46, "temperature": 0.74},
    4: {"exaggeration": 0.34, "cfg_weight": 0.38, "temperature": 0.72},
}

RETAKE_TEXTS = {
    5: "Past a kelvin. Past fifty milli-kelvin.",
    31: ("For scale: at twenty-five degrees C, one milli-kelvin is forty-four parts per "
         "million of the thermister's resistance."),
    34: ("But that ruler is also a ceiling. Once the thermister passes twenty-two K ohms, "
         "around eight degrees C, the reading clips."),
    41: ("Arm two has the lowest costed drift, about zero point two one milli-kelvin for every "
         "kelvin the board moves."),
}
SELECTED_RETAKES = {5: 3, 31: 4, 34: 5, 41: 4}
RETAKE_PARAMS = {
    1: {"exaggeration": 0.36, "cfg_weight": 0.42, "temperature": 0.78},
    2: {"exaggeration": 0.32, "cfg_weight": 0.46, "temperature": 0.74},
    3: {"exaggeration": 0.40, "cfg_weight": 0.38, "temperature": 0.72},
    4: {"exaggeration": 0.34, "cfg_weight": 0.35, "temperature": 0.70},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stamp(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read_srt(path: Path) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    for block in re.split(r"\r?\n\r?\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = block.splitlines()
        start, end = [stamp(item.strip()) for item in lines[1].split("-->")]
        line_id = int(lines[0])
        rows[line_id] = {
            "line": line_id,
            "start": start,
            "end": end,
            "caption": " ".join(lines[2:]).strip(),
        }
    return rows


def spoken(text: str) -> str:
    replacements = {
        "AD7124-8": "A D seven one two four dash eight",
        "24-bit": "twenty-four bit",
        "Teensy 4.1": "Teensy four point one",
        "PID": "P I D",
        "PWM": "P W M",
        "MAX1968": "Max nineteen sixty-eight",
        "22 kΩ": "twenty-two K ohms",
        "8 °C": "eight degrees C",
        "25 °C": "twenty-five degrees C",
        "2.5 V": "two point five volts",
        "0.21 millikelvin": "zero point two one millikelvin",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # These are pronunciation hints only. Captions and voiceover-script.md are untouched.
    text = re.sub(r"thermistor", "ther-MISS-ter", text, flags=re.IGNORECASE)
    text = re.sub(r"thermoelectric", "thermo-electric", text, flags=re.IGNORECASE)
    text = re.sub(r"millikelvin", "milli-kelvin", text, flags=re.IGNORECASE)
    text = re.sub(r"ratiometric", "ratio-metric", text, flags=re.IGNORECASE)
    return text.replace("—", ",").replace("–", ",")


def legacy_trim(y: np.ndarray, sample_rate: int, pad: float = 0.06) -> np.ndarray:
    """Reproduce the former cut so deterministic replay can be verified."""
    intervals = librosa.effects.split(y, top_db=40)
    if len(intervals) == 0:
        return y
    first = max(0, intervals[0][0] - round(pad * sample_rate))
    last = min(len(y), intervals[-1][1] + round(pad * sample_rate))
    return y[first:last]


def legacy_comparison(raw: np.ndarray, sample_rate: int, legacy_path: Path | None) -> dict:
    if legacy_path is None or not legacy_path.exists():
        return {"available": False}
    old, old_rate = sf.read(legacy_path, dtype="float32", always_2d=False)
    if old.ndim > 1:
        old = old.mean(axis=1)
    replay = legacy_trim(raw, sample_rate)
    count = min(len(old), len(replay))
    error = float(np.max(np.abs(old[:count] - replay[:count]))) if count else 1.0
    return {
        "available": True,
        "legacy_path": str(legacy_path),
        "legacy_duration": len(old) / old_rate,
        "replayed_trim_duration": len(replay) / sample_rate,
        "length_delta_samples": len(replay) - len(old),
        "max_abs_sample_delta": error,
        "same_performance": abs(len(replay) - len(old)) <= 2 and error <= 4.0e-5,
    }


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--legacy-dir", type=Path)
    parser.add_argument("--settings-out", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    out = args.out.resolve()
    prompt = args.prompt.resolve()
    legacy = args.legacy_dir.resolve() if args.legacy_dir else None
    out.mkdir(parents=True, exist_ok=True)
    rows = read_srt(repo / "captions.srt")

    from chatterbox.tts import ChatterboxTTS

    model = ChatterboxTTS.from_pretrained(device="cuda")
    sample_rate = model.sr
    report: list[dict] = []
    print(f"Chatterbox loaded; sample_rate={sample_rate}", flush=True)

    for group_id, line_ids in enumerate(GROUPS, 1):
        take = SELECTED_GROUP_TAKES[group_id]
        params = GROUP_PARAMS[take]
        seed = 2_600_000 + group_id * 131 + take * 23
        target = out / f"group{group_id:02d}_take{take}_raw.wav"
        text = " ".join(spoken(rows[line_id]["caption"]) for line_id in line_ids)
        if not target.exists():
            conditioning_exaggeration = 0.36 if take <= 2 else 0.32
            model.prepare_conditionals(str(prompt), exaggeration=conditioning_exaggeration)
            torch.manual_seed(seed)
            wave = model.generate(text, **params)
            audio = wave.detach().cpu().numpy().squeeze().astype(np.float32)
            sf.write(target, audio, sample_rate, subtype="PCM_24")
        else:
            audio, loaded_rate = sf.read(target, dtype="float32", always_2d=False)
            if loaded_rate != sample_rate:
                raise RuntimeError(f"Unexpected sample rate in {target}: {loaded_rate}")
        old_path = legacy / f"group{group_id:02d}_take{take}.wav" if legacy else None
        comparison = legacy_comparison(audio, sample_rate, old_path)
        row = {
            "kind": "context-group",
            "group": group_id,
            "line_ids": line_ids,
            "take": take,
            "seed": seed,
            "params": params,
            "path": str(target),
            "duration": len(audio) / sample_rate,
            "sha256": sha256(target),
            "legacy_comparison": comparison,
        }
        report.append(row)
        print(
            f"group {group_id:02d} take {take}: {row['duration']:.2f}s; "
            f"same approved performance={comparison.get('same_performance', 'unavailable')}",
            flush=True,
        )

    model.prepare_conditionals(str(prompt), exaggeration=0.36)
    for line_id, take in SELECTED_RETAKES.items():
        param_index = ((take - 1) % 4) + 1
        params = RETAKE_PARAMS[param_index]
        seed = 4_100_000 + line_id * 151 + take * 31
        target = out / f"line{line_id:02d}_retake{take}_raw.wav"
        if not target.exists():
            torch.manual_seed(seed)
            wave = model.generate(RETAKE_TEXTS[line_id], **params)
            audio = wave.detach().cpu().numpy().squeeze().astype(np.float32)
            sf.write(target, audio, sample_rate, subtype="PCM_24")
        else:
            audio, loaded_rate = sf.read(target, dtype="float32", always_2d=False)
            if loaded_rate != sample_rate:
                raise RuntimeError(f"Unexpected sample rate in {target}: {loaded_rate}")
        old_path = legacy / f"line{line_id:02d}_retake{take}.wav" if legacy else None
        comparison = legacy_comparison(audio, sample_rate, old_path)
        row = {
            "kind": "line-retake",
            "line": line_id,
            "take": take,
            "seed": seed,
            "params": params,
            "text": RETAKE_TEXTS[line_id],
            "path": str(target),
            "duration": len(audio) / sample_rate,
            "sha256": sha256(target),
            "legacy_comparison": comparison,
        }
        report.append(row)
        print(
            f"line {line_id:02d} retake {take}: {row['duration']:.2f}s; "
            f"same approved performance={comparison.get('same_performance', 'unavailable')}",
            flush=True,
        )

    settings = {
        "profile": "warm-natural-narrator-v2",
        "purpose": "Warm, welcoming technical introduction; not an epic/deep announcer read.",
        "model": "ChatterboxTTS",
        "chatterbox_package_version": package_version("chatterbox-tts"),
        "torch_version": torch.__version__,
        "sample_rate": sample_rate,
        "prompt": str(prompt),
        "prompt_sha256": sha256(prompt),
        "captions_sha256": sha256(repo / "captions.srt"),
        "voiceover_script_sha256": sha256(repo / "voiceover-script.md"),
        "selected_group_takes": SELECTED_GROUP_TAKES,
        "group_params": GROUP_PARAMS,
        "selected_line_retakes": SELECTED_RETAKES,
        "retake_params": RETAKE_PARAMS,
        "generation_report": report,
        "ending_policy": "Keep the untrimmed model output; alignment adds protected post-roll.",
        "script_changed": False,
    }
    settings_text = json.dumps(settings, indent=2)
    settings_path = args.settings_out.resolve() if args.settings_out else out.parent / "voice-settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(settings_text, encoding="utf-8")
    (out / "generation-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"DONE: {len(report)} approved raw performances reconstructed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
