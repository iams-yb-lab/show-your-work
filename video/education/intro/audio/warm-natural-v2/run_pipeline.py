"""Unattended, resumable production pipeline for the protected-ending v2 revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
# .../video/education/intro/audio/warm-natural-v2 -> audio, intro, education, video
VIDEO = ROOT.parents[3]
REPO = VIDEO.parent
EDUCATION = VIDEO / "education" / "intro"
NATURAL_VOICE = VIDEO / "natural-voice"
WORK = VIDEO / "out" / "education" / "warm-natural-v2"
RELEASES = VIDEO / "out" / "releases"
LEGACY = Path(r"C:\Users\iams1\.codex\visualizations\2026\08\12\019ff5e6-333c-7732-a44f-7daa05aa5c47")
TEMP = Path(r"C:\Users\iams1\AppData\Local\Temp")
CHATTER_PYTHON = TEMP / "chatterbox-venv" / "Scripts" / "python.exe"
EDIT_PYTHON = TEMP / "editx-venv" / "Scripts" / "python.exe"
SR_PYTHON = TEMP / "sr-venv" / "Scripts" / "python.exe"
FFMPEG = Path(
    r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)
FFPROBE = FFMPEG.with_name("ffprobe.exe")

SOURCE_VIDEO = EDUCATION / "picture" / "Temperature Controller Intro 1080p.mp4"
SOURCE_CAPTIONS = EDUCATION / "script" / "captions.srt"
SOURCE_SCRIPT = EDUCATION / "script" / "voiceover-script.md"
PROFILE = NATURAL_VOICE / "profiles" / "warm-natural"
PROMPT_SOURCE = PROFILE / "warm_narrator_prompt.wav"
PROMPT_METADATA_SOURCE = PROFILE / "warm_narrator_prompt.json"
REFERENCE = ROOT / "reference"
REFERENCE_MANIFEST_SOURCE = REFERENCE / "approved-manifest-v1.json"
REFERENCE_GROUPS_SOURCE = REFERENCE / "approved-groups-v1.json"
CHECKPOINT = REPO / "checkpoints" / "MossFormer2_SR_48K" / "do_03925000"

RAW = WORK / "voice-raw-selected"
ALIGNED = WORK / "voice-aligned-24k"
RESTORED = WORK / "voice-restored-48k"
MUSIC_DIR = WORK / "music"
MIX_DIR = WORK / "mix"
HAPPY_MUSIC = MUSIC_DIR / "happy-welcoming-major-key.wav"
FINAL_AUDIO = WORK / "deliverables" / "Temperature Controller Intro - Warm Natural Narration v2.wav"
FINAL_VIDEO = RELEASES / "Temperature Controller Intro 1080p - Warm Natural Narration v2.mp4"
STATUS = ROOT / "pipeline-status.json"
LOG = ROOT / "pipeline.log"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_status(phase: str, **extra: object) -> None:
    payload = {"phase": phase, "updated": now(), **extra}
    STATUS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n[{payload['updated']}] {phase}", flush=True)


def run_stage(label: str, command: list[str]) -> None:
    write_status(label, command=command)
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    with LOG.open("a", encoding="utf-8") as log:
        log.write(f"\n\n[{now()}] {label}\n{' '.join(command)}\n")
        log.flush()
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log.write(line)
            log.flush()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"{label} failed with exit code {return_code}")
    write_status(f"{label}-complete", elapsed_seconds=round(time.monotonic() - started, 1))


def probe(path: Path) -> dict:
    result = subprocess.check_output(
        [str(FFPROBE), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        text=True,
        encoding="utf-8",
    )
    return json.loads(result)


def video_stream_md5(path: Path) -> str:
    return subprocess.check_output(
        [str(FFMPEG), "-v", "error", "-i", str(path), "-map", "0:v:0",
         "-c", "copy", "-f", "md5", "-"],
        text=True,
        encoding="utf-8",
    ).strip()


def copy_verified(source: Path, target: Path) -> None:
    if target.exists():
        if sha256(source) != sha256(target):
            raise RuntimeError(f"Existing preserved input differs: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def capture_environment() -> None:
    target = ROOT / "environment.txt"
    if target.exists():
        return
    sections = []
    for label, executable in (
        ("chatterbox", CHATTER_PYTHON),
        ("alignment-and-mix", EDIT_PYTHON),
        ("speech-restoration", SR_PYTHON),
    ):
        freeze = subprocess.run(
            [str(executable), "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        version = subprocess.check_output([str(executable), "--version"], text=True, stderr=subprocess.STDOUT)
        sections.append(f"[{label}]\npython={executable}\n{version.strip()}\n{freeze.stdout.strip()}\n")
    target.write_text("\n".join(sections), encoding="utf-8")


def initial_hashes() -> dict:
    prior_files = [
        LEGACY / "Temperature Controller Intro - Warm Natural Narration and Music.wav",
        LEGACY / "Temperature Controller Intro 1080p - Warm Natural Narration.mp4",
    ]
    return {
        "source_video": sha256(SOURCE_VIDEO),
        "captions": sha256(SOURCE_CAPTIONS),
        "voiceover_script": sha256(SOURCE_SCRIPT),
        "prompt": sha256(PROMPT_SOURCE),
        "speech_restoration_checkpoint": sha256(CHECKPOINT),
        "prior_deliverables": {
            str(path): sha256(path) for path in prior_files if path.exists()
        },
    }


def verify_unchanged(before: dict) -> None:
    checks = {
        "source_video": SOURCE_VIDEO,
        "captions": SOURCE_CAPTIONS,
        "voiceover_script": SOURCE_SCRIPT,
        "prompt": PROMPT_SOURCE,
        "speech_restoration_checkpoint": CHECKPOINT,
    }
    for key, path in checks.items():
        after = sha256(path)
        if before[key] != after:
            raise RuntimeError(f"Protected source changed: {path}")
    for path_string, expected in before["prior_deliverables"].items():
        path = Path(path_string)
        if not path.exists() or sha256(path) != expected:
            raise RuntimeError(f"Prior deliverable changed: {path}")


def finish_report(hashes_before: dict) -> dict:
    alignment = json.loads((ALIGNED / "alignment-report.json").read_text(encoding="utf-8"))
    mix = json.loads((MIX_DIR / "mix-report.json").read_text(encoding="utf-8"))
    source_md5 = video_stream_md5(SOURCE_VIDEO)
    final_md5 = video_stream_md5(FINAL_VIDEO)
    if source_md5 != final_md5 or source_md5 != mix["video_stream_md5"]:
        raise RuntimeError(
            f"Video stream integrity failed: source={source_md5}, final={final_md5}, "
            f"mix={mix['video_stream_md5']}"
        )
    return {
        "phase": "complete",
        "updated": now(),
        "final_audio": str(FINAL_AUDIO),
        "final_video": str(FINAL_VIDEO),
        "source_and_prior_outputs_untouched": True,
        "script_changed": False,
        "script_cues": 49,
        "minimum_protected_tail_seconds": alignment["minimum_protected_tail_seconds"],
        "alignment_warnings": alignment["warnings"],
        "happy_music": {
            "key": "G major",
            "bpm": 104.0,
            "target_lufs": -29.5,
            "noise_sources": 0,
        },
        "video_stream_md5_identical": True,
        "video_stream_md5": source_md5,
        "video_reencoded": mix["video_reencoded"],
        "max_voice_tempo": mix["max_tempo"],
        "final_loudness": mix["final_loudness"],
        "final_video_probe": probe(FINAL_VIDEO),
        "final_audio_probe": probe(FINAL_AUDIO),
        "protected_input_hashes": hashes_before,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Fully decode and re-verify existing v2 deliverables without replacing them.",
    )
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    FINAL_AUDIO.parent.mkdir(parents=True, exist_ok=True)
    FINAL_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    for required in (
        SOURCE_VIDEO, SOURCE_CAPTIONS, SOURCE_SCRIPT, PROMPT_SOURCE,
        PROMPT_METADATA_SOURCE, REFERENCE_MANIFEST_SOURCE, REFERENCE_GROUPS_SOURCE,
        CHECKPOINT, CHATTER_PYTHON, EDIT_PYTHON, SR_PYTHON, FFMPEG, FFPROBE,
    ):
        if not required.exists():
            raise FileNotFoundError(required)
    if FINAL_AUDIO.exists() != FINAL_VIDEO.exists():
        raise FileExistsError("Only one v2 deliverable exists; refusing an ambiguous resume")
    if FINAL_AUDIO.exists() and args.verify_existing:
        write_status("verify-existing")
        hashes_before = initial_hashes()
        verify_unchanged(hashes_before)
        run_stage("full-decode-verification", [
            str(FFMPEG), "-v", "error", "-i", str(FINAL_VIDEO),
            "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-",
        ])
        final_report = finish_report(hashes_before)
        (ROOT / "protected-input-hashes.json").write_text(
            json.dumps(hashes_before, indent=2), encoding="utf-8"
        )
        (ROOT / "final-report.json").write_text(
            json.dumps(final_report, indent=2), encoding="utf-8"
        )
        write_status("complete", **{key: value for key, value in final_report.items() if key != "phase"})
        print(json.dumps(final_report, indent=2), flush=True)
        return 0
    if FINAL_AUDIO.exists() or FINAL_VIDEO.exists():
        raise FileExistsError("v2 deliverables already exist; refusing to overwrite them")

    write_status("preserve-inputs")
    hashes_before = initial_hashes()
    (ROOT / "protected-input-hashes.json").write_text(json.dumps(hashes_before, indent=2), encoding="utf-8")
    capture_environment()

    raw_targets = list(RAW.glob("*_raw.wav")) if RAW.exists() else []
    if not (RAW / "generation-report.json").exists() or len(raw_targets) != 23:
        command = [
            str(CHATTER_PYTHON), str(ROOT / "regenerate_selected_raw.py"),
            "--repo", str(EDUCATION / "script"), "--out", str(RAW),
            "--prompt", str(PROFILE / "warm_narrator_prompt.wav"),
            "--settings-out", str(ROOT / "education-v2-generation-settings.json"),
        ]
        legacy_takes = LEGACY / "chatterbox-intro-context-warm"
        if legacy_takes.exists():
            command.extend(["--legacy-dir", str(legacy_takes)])
        run_stage("regenerate-approved-untrimmed-performances", command)
    else:
        write_status("regenerate-approved-untrimmed-performances-complete", resumed=True)

    aligned_targets = list(ALIGNED.glob("line*_best.wav")) if ALIGNED.exists() else []
    if not (ALIGNED / "alignment-report.json").exists() or len(aligned_targets) != 49:
        run_stage("align-with-protected-endings", [
            str(EDIT_PYTHON), str(ROOT / "align_preserve_endings.py"),
            "--repo", str(EDUCATION / "script"), "--raw", str(RAW), "--out", str(ALIGNED),
            "--reference-manifest", str(REFERENCE / "approved-manifest-v1.json"),
        ])
    else:
        write_status("align-with-protected-endings-complete", resumed=True)

    restored_targets = list(RESTORED.glob("line*_best.wav")) if RESTORED.exists() else []
    if not (RESTORED / "sr-report.json").exists() or len(restored_targets) != 49:
        run_stage("speech-restoration", [
            str(SR_PYTHON), str(ROOT / "superresolve_voice.py"),
            "--src", str(ALIGNED), "--out", str(RESTORED),
            "--checkpoint", str(CHECKPOINT),
        ])
    else:
        write_status("speech-restoration-complete", resumed=True)

    source_probe = probe(SOURCE_VIDEO)
    video_duration = float(source_probe["format"]["duration"])
    if not HAPPY_MUSIC.exists() or not (MUSIC_DIR / "music-report.json").exists():
        run_stage("happy-welcoming-major-key-score", [
            str(EDIT_PYTHON), str(ROOT / "make_happy_music.py"),
            "--out", str(HAPPY_MUSIC), "--duration", str(video_duration),
        ])
    else:
        write_status("happy-welcoming-major-key-score-complete", resumed=True)

    run_stage("mix-master-and-stream-copy-video", [
        str(EDIT_PYTHON), str(ROOT / "mix_master_mux.py"),
        "--voice", str(RESTORED), "--music", str(HAPPY_MUSIC),
        "--video", str(SOURCE_VIDEO), "--work", str(MIX_DIR),
        "--audio-out", str(FINAL_AUDIO), "--video-out", str(FINAL_VIDEO),
    ])
    run_stage("full-decode-verification", [
        str(FFMPEG), "-v", "error", "-i", str(FINAL_VIDEO),
        "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-",
    ])

    verify_unchanged(hashes_before)
    final_report = finish_report(hashes_before)
    (ROOT / "final-report.json").write_text(json.dumps(final_report, indent=2), encoding="utf-8")
    write_status("complete", **{key: value for key, value in final_report.items() if key != "phase"})
    print(json.dumps(final_report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        ROOT.mkdir(parents=True, exist_ok=True)
        write_status("failed", error=f"{type(error).__name__}: {error}")
        raise
