#!/usr/bin/env python3
"""
RENDER ALL PLATINUM ESSAYS WITH AUDIO-SYNCHRONIZED TIMING

Discovers Platinum-house renderer scripts, imports their SCENES and render_frame
functions, synthesizes narration scene-by-scene, measures the real audio, retimes
each visual scene to that measured duration, renders the video, muxes narration,
and packages completed MP4s into ZIP archives.

Designed for renderers such as:
    attention_creates_finite_self_platinum.py
    recognition_before_perception_platinum.py
    time_is_produced_by_forgetting_platinum.py
    reality_localizes_itself_platinum.py
    gods_under_pressure_platinum.py
    freedom_before_causality_platinum.py
    why_fiction_feels_more_real_platinum.py
    the_mirror_and_the_overflow_platinum.py
    the_one_does_not_command_platinum.py
    memory_before_brains_platinum.py
    body_electrical_society_platinum.py
    cells_that_solve_problems_platinum.py
    ...and other compatible renderers.

REQUIREMENTS
------------
Required:
    Python 3.10+
    ffmpeg + ffprobe
    Pillow
    NumPy

TTS: install at least one backend.

Recommended online voice:
    pip install edge-tts

Local fallback:
    sudo apt install espeak-ng

FULL MODE
---------
Calls each renderer's real render_frame() for every frame. Highest fidelity,
but computationally expensive.

DELIVERY MODE
-------------
Samples each authored scene at its mature conceptual frame, then creates subtle
continuous camera motion for the exact narration duration. Much faster and still
preserves scene-to-line matching.

EXAMPLES
--------
# Render every renderer beside this script, using Edge TTS:
python render_all_platinum.py --mode full --tts edge

# Fast audio-synchronized delivery renders:
python render_all_platinum.py --mode delivery --tts edge

# Render three named essays:
python render_all_platinum.py \
    --include attention_creates_finite_self \
              recognition_before_perception \
              time_is_produced_by_forgetting

# Local offline narration:
python render_all_platinum.py --tts espeak --voice en-gb

# Resume interrupted work:
python render_all_platinum.py --resume

# Rebuild one film:
python render_all_platinum.py --include attention_creates_finite_self --force

OUTPUT
------
rendered_platinum/
    <essay_slug>/
        audio_raw/
        audio_padded/
        scene_frames/
        scene_video/
        final/
            <essay_slug>.mp4
        timing.json
        status.json
    rendered_platinum_all.zip
    rendered_platinum_part_001.zip
    render_manifest.json
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import wave
import zipfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Pillow is required: pip install pillow") from exc


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_SOURCE_DIR = SCRIPT_PATH.parent
DEFAULT_OUTPUT_DIR = SCRIPT_PATH.parent / "rendered_platinum"

VIDEO_EXT = ".mp4"
AUDIO_CODEC = "aac"
VIDEO_CODEC = "libx264"


# ---------------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------------

def run(
    command: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and result.returncode != 0:
        joined = " ".join(command)
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {joined}\n{detail}")
    return result


def require_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required executable not found on PATH: {name}")
    return path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "essay"


def natural_key(path: Path) -> list[Any]:
    return [
        int(piece) if piece.isdigit() else piece.lower()
        for piece in re.split(r"(\d+)", path.name)
    ]


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def ffprobe_duration(path: Path) -> float:
    result = run(
        [
            require_executable("ffprobe"),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture=True,
    )
    try:
        return float(result.stdout.strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Could not determine duration of {path}") from exc


def has_audio_stream(path: Path) -> bool:
    result = run(
        [
            require_executable("ffprobe"),
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(path),
        ],
        capture=True,
        check=False,
    )
    return bool((result.stdout or "").strip())


def scene_value(scene: Any, name: str, default: Any = None) -> Any:
    if isinstance(scene, dict):
        return scene.get(name, default)
    return getattr(scene, name, default)


def set_scene_value(scene: Any, name: str, value: Any) -> None:
    if isinstance(scene, dict):
        scene[name] = value
    else:
        setattr(scene, name, value)


def serialise_scene(scene: Any) -> dict[str, Any]:
    if is_dataclass(scene):
        return asdict(scene)
    if isinstance(scene, dict):
        return dict(scene)
    fields = ("title", "narration", "duration", "visual", "params")
    return {field: getattr(scene, field, None) for field in fields}


def safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Renderer discovery and loading
# ---------------------------------------------------------------------------

def discover_renderers(
    source_dir: Path,
    include: list[str],
    exclude: list[str],
) -> list[Path]:
    candidates = sorted(
        [
            path for path in source_dir.glob("*_platinum.py")
            if path.resolve() != SCRIPT_PATH
        ],
        key=natural_key,
    )

    def matches_any(path: Path, terms: Iterable[str]) -> bool:
        stem = path.stem.lower()
        return any(term.lower() in stem for term in terms)

    if include:
        candidates = [path for path in candidates if matches_any(path, include)]
    if exclude:
        candidates = [path for path in candidates if not matches_any(path, exclude)]

    return candidates


def load_renderer(path: Path) -> ModuleType:
    module_name = f"platinum_{slugify(path.stem)}_{abs(hash(path))}"

    code = path.read_text(encoding="utf-8")
    # Strip `from __future__ import annotations` — it breaks dataclasses
    # under importlib due to PEP 563 deferred evaluation.
    code = re.sub(
        r'^from\s+__future__\s+import\s+annotations\s*\n',
        '',
        code,
        flags=re.MULTILINE,
    )

    module = ModuleType(module_name)
    module.__file__ = str(path.resolve())
    module.__name__ = module_name
    module.__package__ = None
    module.__dict__.update({
        "__builtins__": __builtins__,
        "__file__": str(path.resolve()),
        "__name__": module_name,
    })
    sys.modules[module_name] = module

    exec(code, module.__dict__)

    scenes = getattr(module, "SCENES", None)
    render_frame = getattr(module, "render_frame", None)

    if not isinstance(scenes, (list, tuple)) or not scenes:
        raise RuntimeError(f"{path.name} does not expose a non-empty SCENES list")
    if not callable(render_frame):
        raise RuntimeError(f"{path.name} does not expose render_frame()")

    for index, scene in enumerate(scenes, 1):
        narration = scene_value(scene, "narration")
        if not isinstance(narration, str) or not narration.strip():
            raise RuntimeError(
                f"{path.name}: scene {index} has no usable narration"
            )

    return module


def infer_film_slug(module: ModuleType, source_path: Path) -> str:
    output = getattr(module, "OUTPUT", None)
    if isinstance(output, Path) and output.name.startswith("output_"):
        return slugify(output.name.removeprefix("output_"))
    return slugify(source_path.stem.removesuffix("_platinum"))


# ---------------------------------------------------------------------------
# Narration cleanup and TTS
# ---------------------------------------------------------------------------

SPEECH_REPLACEMENTS = {
    "Śiva": "Shiva",
    "Śakti": "Shakti",
    "Bhairava": "Bhairava",
    "Kālī": "Kali",
    "kāla": "kaala",
    "Kāla": "Kaala",
    "svātantrya": "svaatantrya",
    "Svātantrya": "Svaatantrya",
    "spanda": "spanda",
    "Spanda": "Spanda",
    "vimarśa": "vimarsha",
    "Vimarśa": "Vimarsha",
    "prakāśa": "prakaasha",
    "Prakāśa": "Prakaasha",
    "pratyabhijñā": "pratyabhijnaa",
    "Pratyabhijñā": "Pratyabhijnaa",
    "sādhāraṇīkaraṇa": "saadhaaranikarana",
    "karuṇa": "karuna",
    "Karuṇa": "Karuna",
    "karuṇā": "karunaa",
    "vīra": "veera",
    "Vīra": "Veera",
    "śṛṅgāra": "shringara",
    "Śṛṅgāra": "Shringara",
    "śānta": "shaanta",
    "Śānta": "Shaanta",
    "rasa": "rasa",
    "Rasa": "Rasa",
    "āsvāda": "aasvaada",
    "Akrama": "Akrama",
    "kañcuka": "kanchuka",
    "kañcukas": "kanchukas",
    "niyati": "niyati",
    "ābhāsa": "aabhaasa",
    "aham": "aham",
    "idam": "idam",
    "Plotinus": "Plotinus",
    "Proclus": "Proclus",
    "Abhinavagupta": "Abhinavagupta",
}


def prepare_speech_text(text: str, replacements: bool = True) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if replacements:
        for source, target in SPEECH_REPLACEMENTS.items():
            text = text.replace(source, target)
    return text


async def edge_save(text: str, voice: str, rate: str, pitch: str, out_path: Path) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("edge-tts is not installed. Run: pip install edge-tts") from exc

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))


def synth_edge(text: str, out_path: Path, voice: str, rate: str, pitch: str) -> None:
    asyncio.run(edge_save(text, voice, rate, pitch, out_path))


def synth_espeak(text: str, out_path: Path, voice: str, words_per_minute: int) -> None:
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("Neither espeak-ng nor espeak is installed. Install one or use --tts edge.")
    wav_path = out_path.with_suffix(".wav")
    run([exe, "-v", voice, "-s", str(words_per_minute), "-w", str(wav_path), text])
    run([require_executable("ffmpeg"), "-y", "-i", str(wav_path), "-ar", "48000", "-ac", "1", "-c:a", "aac", "-b:a", "160k", str(out_path)])
    safe_unlink(wav_path)


def synth_silence(out_path: Path, duration: float) -> None:
    run([
        require_executable("ffmpeg"), "-y",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-t", f"{duration:.6f}",
        "-c:a", "aac", "-b:a", "160k", str(out_path),
    ])


def synthesise_scene(
    text: str, out_path: Path, *, backend: str, voice: str, rate: str, pitch: str,
    words_per_minute: int, retries: int,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and ffprobe_duration(out_path) > 0.05:
        return

    speech = prepare_speech_text(text)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        safe_unlink(out_path)
        try:
            if backend == "edge":
                synth_edge(speech, out_path, voice, rate, pitch)
            elif backend == "espeak":
                synth_espeak(speech, out_path, voice, words_per_minute)
            elif backend == "silence":
                estimated = max(0.8, len(speech.split()) / 2.7)
                synth_silence(out_path, estimated)
            else:
                raise ValueError(f"Unknown TTS backend: {backend}")
            if not out_path.exists() or ffprobe_duration(out_path) <= 0.05:
                raise RuntimeError("TTS produced no usable audio")
            return
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(8, attempt * 2))
    raise RuntimeError(f"TTS failed after {retries} attempt(s): {last_error}")


def pad_audio(source: Path, target: Path, total_duration: float, fade_out: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = ffprobe_duration(target)
        if abs(existing - total_duration) < 0.08:
            return

    source_duration = ffprobe_duration(source)
    fade_start = max(0.0, source_duration - fade_out)
    filter_graph = (
        f"afade=t=out:st={fade_start:.6f}:d={fade_out:.6f},"
        f"apad=pad_dur={max(0.0, total_duration-source_duration):.6f},"
        f"atrim=0:{total_duration:.6f},"
        "aresample=48000"
    )
    run([
        require_executable("ffmpeg"), "-y", "-i", str(source),
        "-af", filter_graph,
        "-ar", "48000", "-ac", "1",
        "-c:a", "aac", "-b:a", "160k", str(target),
    ])


# ---------------------------------------------------------------------------
# Full procedural rendering
# ---------------------------------------------------------------------------

def render_full_scene(
    module: ModuleType, scene: Any, *, scene_index: int, scene_dir: Path,
    output_path: Path, fps: int, width: int, height: int, duration: float,
    jpeg_quality: int, resume: bool,
) -> None:
    frame_count = max(2, round(duration * fps))
    scene_dir.mkdir(parents=True, exist_ok=True)
    set_scene_value(scene, "duration", duration)

    for frame_index in range(frame_count):
        frame_path = scene_dir / f"{frame_index:05d}.jpg"
        if resume and frame_path.exists() and frame_path.stat().st_size > 1000:
            continue
        image = module.render_frame(scene, frame_index, frame_count, width, height, scene_index * 100000 + frame_index)
        if not isinstance(image, Image.Image):
            raise TypeError(f"{module.__name__}.render_frame returned {type(image).__name__}, expected PIL.Image.Image")
        image.convert("RGB").save(frame_path, quality=jpeg_quality, subsampling=0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        require_executable("ffmpeg"), "-y",
        "-framerate", str(fps),
        "-i", str(scene_dir / "%05d.jpg"),
        "-c:v", VIDEO_CODEC, "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(output_path),
    ])


# ---------------------------------------------------------------------------
# Fast delivery rendering
# ---------------------------------------------------------------------------

def render_delivery_scene(
    module: ModuleType, scene: Any, *, scene_index: int, still_path: Path,
    output_path: Path, fps: int, width: int, height: int, duration: float,
    mature_point: float, jpeg_quality: int, resume: bool,
) -> None:
    still_path.parent.mkdir(parents=True, exist_ok=True)

    if not (resume and still_path.exists() and still_path.stat().st_size > 1000):
        virtual_frames = max(80, round(duration * 10))
        frame_index = min(virtual_frames - 1, max(0, round((virtual_frames - 1) * mature_point)))
        set_scene_value(scene, "duration", duration)
        image = module.render_frame(scene, frame_index, virtual_frames, width, height, scene_index * 100000 + frame_index)
        image.convert("RGB").save(still_path, quality=jpeg_quality, subsampling=0)

    frames = max(2, round(duration * fps))
    zoom_expr = f"min(zoom+0.00045,1.065)"
    x_expr = "iw/2-(iw/zoom/2)"
    y_expr = "ih/2-(ih/zoom/2)"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        require_executable("ffmpeg"), "-y",
        "-loop", "1", "-i", str(still_path),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={width}x{height}:fps={fps},"
        "format=yuv420p",
        "-frames:v", str(frames),
        "-c:v", VIDEO_CODEC, "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(output_path),
    ])


# ---------------------------------------------------------------------------
# Concatenation and muxing
# ---------------------------------------------------------------------------

def concat_media(paths: list[Path], target: Path, *, stream_copy: bool = True) -> None:
    if not paths:
        raise ValueError("No media paths supplied for concatenation")
    target.parent.mkdir(parents=True, exist_ok=True)
    concat_file = target.with_suffix(target.suffix + ".concat.txt")
    concat_file.write_text(
        "\n".join("file '" + str(path.resolve()).replace("'", "'\\''") + "'" for path in paths),
        encoding="utf-8",
    )
    command = [require_executable("ffmpeg"), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file)]
    if stream_copy:
        command += ["-c", "copy"]
    else:
        command += ["-c:v", VIDEO_CODEC, "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    command += [str(target)]
    run(command)


def mux_audio_video(video: Path, audio: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        require_executable("ffmpeg"), "-y",
        "-i", str(video), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", AUDIO_CODEC, "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(target),
    ])


# ---------------------------------------------------------------------------
# One-film pipeline
# ---------------------------------------------------------------------------

def render_film(renderer_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    module = load_renderer(renderer_path)
    slug = infer_film_slug(module, renderer_path)
    film_root = args.output_dir / slug

    raw_audio_dir = film_root / "audio_raw"
    padded_audio_dir = film_root / "audio_padded"
    frames_dir = film_root / "scene_frames"
    stills_dir = film_root / "scene_stills"
    scene_video_dir = film_root / "scene_video"
    final_dir = film_root / "final"

    final_path = final_dir / f"{slug}.mp4"
    timing_path = film_root / "timing.json"
    status_path = film_root / "status.json"

    if args.force and film_root.exists():
        shutil.rmtree(film_root)

    if args.resume and final_path.exists() and final_path.stat().st_size > 100_000 and has_audio_stream(final_path):
        return {
            "slug": slug, "source": str(renderer_path), "output": str(final_path),
            "status": "already_complete", "duration_seconds": ffprobe_duration(final_path),
            "scene_count": len(module.SCENES),
        }

    film_root.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    scenes = [copy.deepcopy(scene) for scene in module.SCENES]

    status: dict[str, Any] = {
        "slug": slug, "source": str(renderer_path), "mode": args.mode, "tts": args.tts,
        "started_at_epoch": time.time(), "status": "working",
        "scenes_total": len(scenes), "scenes_complete": 0,
    }
    atomic_json(status_path, status)

    timings: list[dict[str, Any]] = []
    scene_video_paths: list[Path] = []
    scene_audio_paths: list[Path] = []

    print(f"\n=== {slug} ===")
    print(f"Source: {renderer_path.name}")
    print(f"Scenes: {len(scenes)} | Mode: {args.mode} | TTS: {args.tts}")

    for index, scene in enumerate(scenes, 1):
        title = str(scene_value(scene, "title", f"Scene {index}"))
        narration = str(scene_value(scene, "narration", "")).strip()

        raw_audio = raw_audio_dir / f"scene_{index:03d}.m4a"
        padded_audio = padded_audio_dir / f"scene_{index:03d}.m4a"
        scene_video = scene_video_dir / f"scene_{index:03d}.mp4"

        print(f"[{index:03d}/{len(scenes):03d}] {title}")

        synthesise_scene(narration, raw_audio, backend=args.tts, voice=args.voice,
                         rate=args.rate, pitch=args.pitch,
                         words_per_minute=args.words_per_minute, retries=args.tts_retries)

        speech_duration = ffprobe_duration(raw_audio)
        total_duration = max(args.minimum_scene_duration, speech_duration + args.scene_gap)
        pad_audio(raw_audio, padded_audio, total_duration, fade_out=args.audio_fade)

        if not (args.resume and scene_video.exists() and scene_video.stat().st_size > 50_000
                and abs(ffprobe_duration(scene_video) - total_duration) < 0.12):
            if args.mode == "full":
                render_full_scene(module, scene, scene_index=index,
                    scene_dir=frames_dir / f"scene_{index:03d}", output_path=scene_video,
                    fps=args.fps, width=args.width, height=args.height,
                    duration=total_duration, jpeg_quality=args.jpeg_quality, resume=args.resume)
            else:
                render_delivery_scene(module, scene, scene_index=index,
                    still_path=stills_dir / f"scene_{index:03d}.jpg", output_path=scene_video,
                    fps=args.fps, width=args.width, height=args.height,
                    duration=total_duration, mature_point=args.mature_point,
                    jpeg_quality=args.jpeg_quality, resume=args.resume)

        video_duration = ffprobe_duration(scene_video)
        timings.append({
            "scene_id": f"scene_{index:03d}", "title": title, "narration": narration,
            "speech_duration": round(speech_duration, 4), "total_duration": round(total_duration, 4),
            "video_duration": round(video_duration, 4), "visual": scene_value(scene, "visual"),
        })
        scene_video_paths.append(scene_video)
        scene_audio_paths.append(padded_audio)

        status["scenes_complete"] = index
        status["last_scene"] = title
        atomic_json(status_path, status)
        atomic_json(timing_path, {"slug": slug, "mode": args.mode, "fps": args.fps,
            "width": args.width, "height": args.height, "scene_gap": args.scene_gap, "scenes": timings})

    joined_video = film_root / f"{slug}.video_only.mp4"
    joined_audio = film_root / f"{slug}.audio_only.m4a"
    concat_media(scene_video_paths, joined_video, stream_copy=True)
    concat_media(scene_audio_paths, joined_audio, stream_copy=True)
    mux_audio_video(joined_video, joined_audio, final_path)

    final_duration = ffprobe_duration(final_path)
    status.update({"status": "complete", "finished_at_epoch": time.time(),
        "duration_seconds": round(final_duration, 3), "output": str(final_path)})
    atomic_json(status_path, status)

    if args.cleanup_intermediate:
        safe_unlink(joined_video)
        safe_unlink(joined_audio)
        if args.mode == "delivery":
            shutil.rmtree(stills_dir, ignore_errors=True)
        else:
            shutil.rmtree(frames_dir, ignore_errors=True)
        shutil.rmtree(scene_video_dir, ignore_errors=True)

    return {"slug": slug, "source": str(renderer_path), "output": str(final_path),
        "status": "complete", "duration_seconds": final_duration,
        "scene_count": len(scenes), "mode": args.mode, "tts": args.tts}


# ---------------------------------------------------------------------------
# ZIP packaging
# ---------------------------------------------------------------------------

def zip_files(paths: list[Path], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in paths:
            archive.write(path, arcname=path.name)


def package_results(completed: list[dict[str, Any]], output_dir: Path, zip_limit_mb: int) -> list[Path]:
    mp4s = [Path(item["output"]) for item in completed
            if item.get("status") in {"complete", "already_complete"} and item.get("output") and Path(item["output"]).exists()]
    if not mp4s:
        return []
    zip_paths: list[Path] = []
    max_bytes = zip_limit_mb * 1024 * 1024
    if sum(path.stat().st_size for path in mp4s) <= max_bytes:
        target = output_dir / "rendered_platinum_all.zip"
        zip_files(mp4s, target)
        return [target]
    part, part_bytes, part_number = [], 0, 1
    for path in mp4s:
        size = path.stat().st_size
        if part and part_bytes + size > max_bytes:
            target = output_dir / f"rendered_platinum_part_{part_number:03d}.zip"
            zip_files(part, target), zip_paths.append(target)
            part_number += 1; part, part_bytes = [], 0
        part.append(path); part_bytes += size
    if part:
        target = output_dir / f"rendered_platinum_part_{part_number:03d}.zip"
        zip_files(part, target), zip_paths.append(target)
    return zip_paths


# ---------------------------------------------------------------------------
# CLI and main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Platinum essay scripts with measured narration timing.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR, help="Folder containing *_platinum.py renderers.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output folder.")
    parser.add_argument("--include", nargs="*", default=[], help="Only renderer stems containing any of these terms.")
    parser.add_argument("--exclude", nargs="*", default=[], help="Skip renderer stems containing any of these terms.")
    parser.add_argument("--mode", choices=("full", "delivery"), default="delivery", help="Full procedural frames or fast audio-synced delivery rendering.")
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--jpeg-quality", type=int, default=94)
    parser.add_argument("--mature-point", type=float, default=0.72, help="Representative animation point used in delivery mode.")
    parser.add_argument("--tts", choices=("edge", "espeak", "silence"), default="edge")
    parser.add_argument("--voice", default="en-GB-RyanNeural", help="Edge voice name or espeak language voice.")
    parser.add_argument("--rate", default="-4%", help="Edge TTS speaking-rate adjustment.")
    parser.add_argument("--pitch", default="-2Hz", help="Edge TTS pitch adjustment.")
    parser.add_argument("--words-per-minute", type=int, default=155, help="Espeak speed.")
    parser.add_argument("--tts-retries", type=int, default=3)
    parser.add_argument("--scene-gap", type=float, default=0.42, help="Silence added after each narration scene.")
    parser.add_argument("--minimum-scene-duration", type=float, default=1.0)
    parser.add_argument("--audio-fade", type=float, default=0.035)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True, help="Reuse completed audio, frames, and scenes.")
    parser.add_argument("--force", action="store_true", help="Delete selected film output before rebuilding.")
    parser.add_argument("--continue-on-error", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cleanup-intermediate", action="store_true", help="Remove intermediate files after successful muxing.")
    parser.add_argument("--zip-limit-mb", type=int, default=1800, help="Maximum approximate size per ZIP archive.")
    parser.add_argument("--no-zip", action="store_true", help="Do not package MP4s.")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    require_executable("ffmpeg")
    require_executable("ffprobe")
    if args.fps < 1: raise ValueError("--fps must be at least 1")
    if args.width < 320 or args.height < 180: raise ValueError("Resolution is unreasonably small")
    if not 0.0 <= args.mature_point <= 1.0: raise ValueError("--mature-point must be between 0 and 1")
    if args.scene_gap < 0: raise ValueError("--scene-gap cannot be negative")
    args.source_dir = args.source_dir.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    validate_args(args)

    renderers = discover_renderers(args.source_dir, args.include, args.exclude)
    if not renderers:
        print(f"No compatible *_platinum.py files found in {args.source_dir}", file=sys.stderr)
        return 2

    print(f"Discovered {len(renderers)} renderer(s):")
    for path in renderers:
        print(f"  - {path.name}")

    results: list[dict[str, Any]] = []

    for renderer in renderers:
        try:
            result = render_film(renderer, args)
            results.append(result)
            print(f"COMPLETE: {result['slug']} ({result.get('duration_seconds', 0)/60:.2f} min)")
        except KeyboardInterrupt:
            print("\nInterrupted. Progress has been saved; rerun with --resume.")
            atomic_json(args.output_dir / "render_manifest.json", results)
            return 130
        except Exception as exc:
            failed = {"slug": slugify(renderer.stem.removesuffix("_platinum")), "source": str(renderer),
                       "status": "failed", "error": str(exc), "traceback": traceback.format_exc()}
            results.append(failed)
            print(f"FAILED: {renderer.name}\n{exc}", file=sys.stderr)
            if not args.continue_on_error:
                break

        atomic_json(args.output_dir / "render_manifest.json", {
            "generated_at_epoch": time.time(), "source_dir": str(args.source_dir),
            "output_dir": str(args.output_dir),
            "settings": {"mode": args.mode, "fps": args.fps, "width": args.width, "height": args.height, "tts": args.tts, "voice": args.voice, "rate": args.rate, "scene_gap": args.scene_gap},
            "results": results,
        })

    zip_paths: list[Path] = []
    if not args.no_zip:
        zip_paths = package_results(results, args.output_dir, args.zip_limit_mb)

    complete_count = sum(item.get("status") in {"complete", "already_complete"} for item in results)
    failed_count = sum(item.get("status") == "failed" for item in results)

    print(f"\n{'='*50}")
    print(f"Completed: {complete_count} | Failed: {failed_count}")
    for item in results:
        if item.get("status") in {"complete", "already_complete"}:
            print(f"  MP4: {item['output']}")
        else:
            print(f"  ERROR: {item['source']} — {item.get('error')}")
    for zp in zip_paths:
        print(f"  ZIP: {zp}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
