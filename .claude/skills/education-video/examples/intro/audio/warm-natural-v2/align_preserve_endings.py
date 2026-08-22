"""Align approved raw takes while preserving releases, breaths, and a quiet post-roll."""

from __future__ import annotations

import argparse
import difflib
import json
import math
import re
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


GROUPS = [
    [1, 2, 3], [4, 5, 6, 7], [8, 9, 10], [11, 12, 13, 14], [15, 16],
    [17, 18, 19], [20, 21], [22, 23], [24, 25, 26], [27, 28],
    [29, 30, 31], [32, 33], [34, 35], [36, 37, 38], [39, 40],
    [41, 42], [43, 44], [45, 46], [47, 48, 49],
]
SELECTED_GROUP_TAKES = {
    1: 1, 2: 3, 3: 2, 4: 1, 5: 3, 6: 4, 7: 3, 8: 3, 9: 2,
    10: 2, 11: 1, 12: 1, 13: 4, 14: 2, 15: 4, 16: 4, 17: 1,
    18: 4, 19: 2,
}
SELECTED_RETAKES = {5: 3, 31: 4, 34: 5, 41: 4}
RETAKE_TEXTS = {
    5: "Past a kelvin. Past fifty milli-kelvin.",
    31: ("For scale: at twenty-five degrees C, one milli-kelvin is forty-four parts per "
         "million of the thermister's resistance."),
    34: ("But that ruler is also a ceiling. Once the thermister passes twenty-two K ohms, "
         "around eight degrees C, the reading clips."),
    41: ("Arm two has the lowest costed drift, about zero point two one milli-kelvin for every "
         "kelvin the board moves."),
}
POST_ROLL_SECONDS = 0.16
INTER_SENTENCE_GUARD_SECONDS = 0.025
END_FADE_SECONDS = 0.012
START_FADE_SECONDS = 0.005


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
    text = re.sub(r"thermistor", "ther-MISS-ter", text, flags=re.IGNORECASE)
    text = re.sub(r"thermoelectric", "thermo-electric", text, flags=re.IGNORECASE)
    text = re.sub(r"millikelvin", "milli-kelvin", text, flags=re.IGNORECASE)
    text = re.sub(r"ratiometric", "ratio-metric", text, flags=re.IGNORECASE)
    return text.replace("—", ",").replace("–", ",")


def norm_words(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    text = re.sub(r"\b22\s*k\b", "twenty two k", text)
    aliases = {
        r"\bpid\b": "p i d", r"\bpwm\b": "p w m", r"\bad\b": "a d",
        r"\bad7124\b": "a d seven one two four", r"\b1968\b": "nineteen sixty eight",
        r"\b7124\b": "seven one two four", r"\bii\b": "two",
    }
    for pattern, replacement in aliases.items():
        text = re.sub(pattern, replacement, text)
    text = text.replace("set point", "setpoint")
    text = text.replace("ratio metric", "ratiometric").replace("ratio-metric", "ratiometric")
    text = text.replace("thermo electric", "thermoelectric").replace("thermo-electric", "thermoelectric")
    text = text.replace("milli kelvin", "millikelvin").replace("milli-kelvin", "millikelvin")
    text = text.replace("ther miss ter", "thermistor").replace("ther-miss-ter", "thermistor")
    numbers = {
        "24": "twenty four", "22": "twenty two", "25": "twenty five", "8": "eight",
        "4.1": "four point one", "2.5": "two point five", "0.21": "zero point two one",
        "50": "fifty", "44": "forty four", "1": "one", "2": "two", "3": "three",
        "4": "four",
    }
    for old, new in numbers.items():
        text = re.sub(rf"(?<![\w.]){re.escape(old)}(?![\w.])", new, text)
    return re.sub(r"[^a-z0-9' ]+", " ", text).split()


def wer(reference: str, hypothesis: str) -> float:
    expected, observed = norm_words(reference), norm_words(hypothesis)
    matcher = difflib.SequenceMatcher(a=expected, b=observed)
    errors = sum(
        max(i2 - i1, j2 - j1)
        for operation, i1, i2, j1, j2 in matcher.get_opcodes()
        if operation != "equal"
    )
    return errors / max(1, len(expected))


def whisper_words(result: dict) -> list[dict]:
    words: list[dict] = []
    for segment in result.get("segments", []):
        for item in segment.get("words", []):
            for token in norm_words(item["word"]):
                words.append({
                    "token": token,
                    "start": float(item["start"]),
                    "end": float(item["end"]),
                })
    return words


def aligned_word_bounds(group_rows: list[dict], result: dict) -> dict[int, dict]:
    expected: list[tuple[str, int]] = []
    for row in group_rows:
        expected.extend((token, row["line"]) for token in norm_words(row["spoken"]))
    observed = whisper_words(result)
    matcher = difflib.SequenceMatcher(
        a=[item[0] for item in expected],
        b=[item["token"] for item in observed],
        autojunk=False,
    )
    mapping: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            mapping[block.a + offset] = block.b + offset

    bounds: dict[int, dict] = {}
    for row in group_rows:
        expected_indices = [
            index for index, item in enumerate(expected)
            if item[1] == row["line"] and index in mapping
        ]
        if not expected_indices:
            raise RuntimeError(f"No aligned words for cue {row['line']}")
        observed_indices = [mapping[index] for index in expected_indices]
        first, last = min(observed_indices), max(observed_indices)
        hypothesis = " ".join(item["token"] for item in observed[first:last + 1])
        bounds[row["line"]] = {
            "speech_start": observed[first]["start"],
            "speech_end": observed[last]["end"],
            "hypothesis": hypothesis,
            "wer": wer(row["spoken"], hypothesis),
        }
    return bounds


def protect_clip(source: np.ndarray, sample_rate: int, start: float, end: float) -> np.ndarray:
    first = max(0, round(start * sample_rate))
    last = min(len(source), round(end * sample_rate))
    clip = source[first:last].astype(np.float32, copy=True)
    if clip.size == 0:
        raise RuntimeError(f"Empty clip at {start:.3f}-{end:.3f}")
    fade_in = min(len(clip), round(START_FADE_SECONDS * sample_rate))
    if fade_in:
        phase = np.linspace(0.0, math.pi / 2, fade_in, dtype=np.float32)
        clip[:fade_in] *= np.sin(phase) ** 2
    fade_out = min(len(clip), round(END_FADE_SECONDS * sample_rate))
    if fade_out:
        phase = np.linspace(math.pi / 2, 0.0, fade_out, dtype=np.float32)
        clip[-fade_out:] *= np.sin(phase) ** 2
    post_roll = np.zeros(round(POST_ROLL_SECONDS * sample_rate), dtype=np.float32)
    return np.concatenate((clip, post_roll))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-manifest", type=Path, required=True)
    args = parser.parse_args()

    repo, raw, out = args.repo.resolve(), args.raw.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    captions_path = repo / "captions.srt"
    if not captions_path.exists():
        captions_path = out.parent / "reference" / "captions.srt"
    captions = read_srt(captions_path)
    reference = json.loads(args.reference_manifest.resolve().read_text(encoding="utf-8"))
    reference_by_line = {int(item["line"]): item for item in reference}
    if len(reference_by_line) != 49 or len(captions) != 49:
        raise RuntimeError("Expected exactly 49 settled cues")
    for line_id, row in captions.items():
        if row["caption"] != reference_by_line[line_id]["caption"]:
            raise RuntimeError(f"Caption mismatch at cue {line_id}; refusing to change the script")

    import whisper

    asr = whisper.load_model("base.en", device="cuda")
    manifest_by_line: dict[int, dict] = {}
    alignment_report: list[dict] = []

    for group_id, line_ids in enumerate(GROUPS, 1):
        take = SELECTED_GROUP_TAKES[group_id]
        source_path = raw / f"group{group_id:02d}_take{take}_raw.wav"
        source, sample_rate = librosa.load(source_path, sr=None, mono=True)
        result = asr.transcribe(str(source_path), language="en", fp16=True, word_timestamps=True)
        group_rows = []
        for line_id in line_ids:
            row = dict(captions[line_id])
            row["spoken"] = spoken(row["caption"])
            group_rows.append(row)
        bounds = aligned_word_bounds(group_rows, result)

        for position, row in enumerate(group_rows):
            line_id = row["line"]
            item = bounds[line_id]
            clip_start = max(0.0, item["speech_start"] - 0.07)
            if position + 1 < len(group_rows):
                next_start = bounds[group_rows[position + 1]["line"]]["speech_start"]
                clip_end = max(item["speech_end"] + 0.04, next_start - INTER_SENTENCE_GUARD_SECONDS)
                clip_end = min(clip_end, next_start - 0.005, len(source) / sample_rate)
            else:
                clip_end = len(source) / sample_rate
            clip = protect_clip(source, sample_rate, clip_start, clip_end)
            target = out / f"line{line_id:02d}_best.wav"
            sf.write(target, clip, sample_rate, subtype="PCM_24")
            entry = dict(reference_by_line[line_id])
            entry.update({
                "spoken": row["spoken"],
                "group": group_id,
                "group_take": take,
                "source_kind": "untrimmed-context-group",
                "source_path": str(source_path),
                "source_start": clip_start,
                "source_end": clip_end,
                "speech_start_in_source": item["speech_start"],
                "speech_end_in_source": item["speech_end"],
                "duration": len(clip) / sample_rate,
                "protected_tail_seconds": clip_end - item["speech_end"] + POST_ROLL_SECONDS,
                "post_roll_seconds": POST_ROLL_SECONDS,
                "alignment_hyp": item["hypothesis"],
                "alignment_wer": item["wer"],
            })
            manifest_by_line[line_id] = entry
            alignment_report.append({
                "line": line_id,
                "source": str(source_path),
                "hypothesis": item["hypothesis"],
                "wer": item["wer"],
                "speech_end": item["speech_end"],
                "clip_end": clip_end,
                "protected_tail_seconds": entry["protected_tail_seconds"],
            })
            print(
                f"cue {line_id:02d}: group {group_id:02d}/{take}; "
                f"WER={item['wer']:.3f}; protected tail={entry['protected_tail_seconds']:.3f}s",
                flush=True,
            )

    # Install the four approved line-specific performances, again from untrimmed output.
    for line_id, take in SELECTED_RETAKES.items():
        source_path = raw / f"line{line_id:02d}_retake{take}_raw.wav"
        source, sample_rate = librosa.load(source_path, sr=None, mono=True)
        result = asr.transcribe(str(source_path), language="en", fp16=True, word_timestamps=True)
        words = whisper_words(result)
        if not words:
            raise RuntimeError(f"No Whisper word timestamps for retake cue {line_id}")
        speech_start, speech_end = words[0]["start"], words[-1]["end"]
        clip_start = max(0.0, speech_start - 0.07)
        clip_end = len(source) / sample_rate
        clip = protect_clip(source, sample_rate, clip_start, clip_end)
        target = out / f"line{line_id:02d}_best.wav"
        sf.write(target, clip, sample_rate, subtype="PCM_24")
        hypothesis = result["text"].strip()
        accuracy = wer(RETAKE_TEXTS[line_id], hypothesis)
        entry = manifest_by_line[line_id]
        entry.update({
            "group_take": f"line-retake-{take}",
            "source_kind": "untrimmed-line-retake",
            "source_path": str(source_path),
            "source_start": clip_start,
            "source_end": clip_end,
            "speech_start_in_source": speech_start,
            "speech_end_in_source": speech_end,
            "duration": len(clip) / sample_rate,
            "protected_tail_seconds": clip_end - speech_end + POST_ROLL_SECONDS,
            "post_roll_seconds": POST_ROLL_SECONDS,
            "alignment_hyp": hypothesis,
            "alignment_wer": accuracy,
        })
        alignment_report = [item for item in alignment_report if item["line"] != line_id]
        alignment_report.append({
            "line": line_id,
            "source": str(source_path),
            "hypothesis": hypothesis,
            "wer": accuracy,
            "speech_end": speech_end,
            "clip_end": clip_end,
            "protected_tail_seconds": entry["protected_tail_seconds"],
        })
        print(
            f"cue {line_id:02d}: retake {take}; WER={accuracy:.3f}; "
            f"protected tail={entry['protected_tail_seconds']:.3f}s",
            flush=True,
        )

    # Cue 13's raw replay slurred "PWM command" in this GPU run. Preserve the exact previously
    # approved contextual performance, but move its ending from last-word + 100 ms to just before
    # cue 14 starts in the same continuous group recording. This keeps the original wording and
    # restores the natural release/pause that the old per-line cut discarded.
    line_id = 13
    legacy_path = out.parent / "reference" / "approved-audio" / "group04_take1.wav"
    legacy_audio, legacy_rate = librosa.load(legacy_path, sr=None, mono=True)
    legacy_entry = reference_by_line[line_id]
    next_legacy_entry = reference_by_line[14]
    clip_start = float(legacy_entry["source_start"])
    speech_end = max(clip_start, float(legacy_entry["source_end"]) - 0.10)
    clip_end = min(
        len(legacy_audio) / legacy_rate,
        float(next_legacy_entry["source_start"]) - INTER_SENTENCE_GUARD_SECONDS,
    )
    clip = protect_clip(legacy_audio, legacy_rate, clip_start, clip_end)
    sf.write(out / f"line{line_id:02d}_best.wav", clip, legacy_rate, subtype="PCM_24")
    entry = manifest_by_line[line_id]
    entry.update({
        "group_take": "approved-v1-context-with-extended-ending",
        "source_kind": "approved-context-group-extended-ending",
        "source_path": str(legacy_path),
        "source_start": clip_start,
        "source_end": clip_end,
        "speech_start_in_source": clip_start + 0.07,
        "speech_end_in_source": speech_end,
        "duration": len(clip) / legacy_rate,
        "protected_tail_seconds": clip_end - speech_end + POST_ROLL_SECONDS,
        "post_roll_seconds": POST_ROLL_SECONDS,
        "alignment_hyp": legacy_entry["alignment_hyp"],
        "alignment_wer": legacy_entry["alignment_wer"],
        "selection_note": "exact approved v1 performance; ending extended into its original group pause",
    })
    alignment_report = [item for item in alignment_report if item["line"] != line_id]
    alignment_report.append({
        "line": line_id,
        "source": str(legacy_path),
        "hypothesis": entry["alignment_hyp"],
        "wer": entry["alignment_wer"],
        "speech_end": speech_end,
        "clip_end": clip_end,
        "protected_tail_seconds": entry["protected_tail_seconds"],
        "selection_note": entry["selection_note"],
    })
    print(
        f"cue {line_id:02d}: exact approved v1 performance; "
        f"protected tail={entry['protected_tail_seconds']:.3f}s",
        flush=True,
    )

    manifest = [manifest_by_line[line_id] for line_id in sorted(manifest_by_line)]
    # Extend only the internal voice slot when a following visual silence permits it.
    for index, entry in enumerate(manifest):
        next_start = manifest[index + 1]["start"] if index + 1 < len(manifest) else 338.1
        desired_end = entry["start"] + entry["duration"] / 1.15 + 0.08
        available_end = next_start - 0.04
        if desired_end > entry["end"] and desired_end <= available_end:
            original_end = entry["end"]
            entry["end"] = desired_end
            entry["audio_slot_end_original"] = original_end
            entry["timing_note"] = "voice slot extended into visual silence to keep tempo at or below 1.15x"

    warnings = [item for item in alignment_report if item["wer"] > 0.18]
    minimum_tail = min(item["protected_tail_seconds"] for item in alignment_report)
    if warnings:
        raise RuntimeError(f"Alignment gate failed: {[item['line'] for item in warnings]}")
    if minimum_tail < POST_ROLL_SECONDS - 1e-6:
        raise RuntimeError(f"Ending-tail gate failed: minimum tail {minimum_tail:.3f}s")

    alignment_report.sort(key=lambda item: item["line"])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out / "alignment-report.json").write_text(
        json.dumps({
            "cues": len(manifest),
            "script_changed": False,
            "post_roll_seconds": POST_ROLL_SECONDS,
            "inter_sentence_guard_seconds": INTER_SENTENCE_GUARD_SECONDS,
            "end_fade_seconds": END_FADE_SECONDS,
            "minimum_protected_tail_seconds": minimum_tail,
            "warnings": warnings,
            "lines": alignment_report,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"DONE: 49 cues; minimum protected ending tail={minimum_tail:.3f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
