"""Reproduce the approved warm synthetic narrator prompt with local Chatterbox.

This is the original prompt-selection procedure made self-contained. The output prompt is a
synthetic Chatterbox voice, not a clone of a real person. Keep the chosen WAV immutable: its
SHA-256 is the persistent voice identity used by the narration pipeline.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch


TEXT = (
    "Hi, thanks for taking a look. This is a project we're building together, and in the "
    "next few minutes I'll show you what it does, why it matters, and where you can help."
)
TAKES = [
    {"exaggeration": 0.32, "cfg_weight": 0.42},
    {"exaggeration": 0.36, "cfg_weight": 0.42},
    {"exaggeration": 0.38, "cfg_weight": 0.48},
    {"exaggeration": 0.42, "cfg_weight": 0.38},
]
TEMPERATURE = 0.80  # Chatterbox 0.1.7 default, made explicit for reproducibility.


def words(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9' ]+", " ", text.lower()).split()


def wer(reference: str, hypothesis: str) -> float:
    expected, observed = words(reference), words(hypothesis)
    matcher = difflib.SequenceMatcher(a=expected, b=observed)
    errors = sum(
        max(i2 - i1, j2 - j1)
        for operation, i1, i2, j1, j2 in matcher.get_opcodes()
        if operation != "equal"
    )
    return errors / max(1, len(expected))


def conditioning_trim(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Trim only the conditioning prompt; never use this on deliverable sentence endings."""
    intervals = librosa.effects.split(audio, top_db=40)
    if len(intervals) == 0:
        return audio
    first = max(0, intervals[0][0] - round(0.06 * sample_rate))
    last = min(len(audio), intervals[-1][1] + round(0.06 * sample_rate))
    return audio[first:last]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    from chatterbox.tts import ChatterboxTTS
    from transformers import pipeline

    model = ChatterboxTTS.from_pretrained(device="cuda")
    sample_rate = model.sr
    transcriber = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-base.en",
        device="cuda",
    )
    takes = []
    for take_number, params in enumerate(TAKES, 1):
        seed = 1_700 + take_number * 23
        torch.manual_seed(seed)
        generated = model.generate(TEXT, temperature=TEMPERATURE, **params)
        audio = conditioning_trim(
            generated.detach().cpu().numpy().squeeze().astype(np.float32),
            sample_rate,
        )
        take_path = output.with_name(f"warm_prompt_take{take_number}.wav")
        sf.write(take_path, audio, sample_rate)
        hypothesis = transcriber({"raw": audio, "sampling_rate": sample_rate})["text"].strip()
        error_rate = wer(TEXT, hypothesis)
        f0, _, _ = librosa.pyin(audio, fmin=60, fmax=300, sr=sample_rate)
        voiced_f0 = f0[~np.isnan(f0)]
        median_f0 = float(np.median(voiced_f0))
        f0_iqr = float(np.percentile(voiced_f0, 75) - np.percentile(voiced_f0, 25))
        score = (
            error_rate * 50
            + abs(median_f0 - 118) / 8
            + 0.3 * abs(f0_iqr - 24) / 8
            + abs(len(audio) / sample_rate - 11.5) / 8
        )
        result = {
            "take": take_number,
            "seed": seed,
            "path": str(take_path),
            "duration": len(audio) / sample_rate,
            "wer": error_rate,
            "f0": median_f0,
            "f0_iqr": f0_iqr,
            "temperature": TEMPERATURE,
            **params,
            "hyp": hypothesis,
            "score": score,
        }
        takes.append(result)
        print(
            f"take {take_number}: {result['duration']:.2f}s; WER={error_rate:.3f}; "
            f"F0={median_f0:.1f}; IQR={f0_iqr:.1f}; score={score:.2f}",
            flush=True,
        )

    valid = [take for take in takes if take["wer"] <= 0.04 and 100 <= take["f0"] <= 140]
    chosen = min(valid or takes, key=lambda take: take["score"])
    shutil.copyfile(chosen["path"], output)
    output.with_suffix(".json").write_text(
        json.dumps({"text": TEXT, "chosen": chosen, "takes": takes}, indent=2),
        encoding="utf-8",
    )
    print(f"CHOSEN take {chosen['take']} -> {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
