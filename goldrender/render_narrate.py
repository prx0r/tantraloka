#!/usr/bin/env python3
"""
Unified render + narrate pipeline for platinum packs.
Two modes: --storyboard (fast) and --production (full).

Usage:
    # Quick narrated contact sheet slideshow (5 minutes)
    python render_narrate.py life_crosses_barriers_platinum.py --storyboard

    # Full render with narration (parallel, uses all cores)
    python render_narrate.py life_crosses_barriers_platinum.py --production

    # Just generate narration for already-rendered pack
    python render_narrate.py life_crosses_barriers_platinum.py --narrate-only

    # Options
    python render_narrate.py pack.py --storyboard --fps 5 --width 640 --height 360
"""
import argparse, asyncio, importlib.util, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

import edge_tts


def require_ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH")
    return exe


def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=15,
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


def load_pack(pack_path: str):
    """Import a platinum pack and return its SCENES and metadata."""
    path = Path(pack_path).resolve()
    if not path.exists():
        raise FileNotFoundError(pack_path)

    spec = importlib.util.spec_from_file_location("pack_mod", path)
    mod = importlib.util.module_from_spec(spec)

    # Workaround: dataclasses + from __future__ import annotations need special handling.
    # Use exec directly instead.
    code = path.read_text()
    code = code.replace("from __future__ import annotations\n", "")
    code = code.replace("from __future__ import annotations", "")
    exec(code, mod.__dict__)

    return mod


def load_scenes_from_timeline(output_dir: Path) -> list[dict]:
    tl = output_dir / "narration_timeline.json"
    if not tl.exists():
        return []
    data = json.loads(tl.read_text())
    return data.get("scenes", [])


def preview_output(mod) -> Path:
    """Find or determine the output directory from the pack module."""
    if hasattr(mod, "OUTPUT"):
        return Path(mod.OUTPUT)
    # Guess from main file
    return Path("output_" + Path(mod.__file__).stem.replace("_platinum", ""))


def generate_contact_sheet_stills(mod, output_dir: Path, width=1280, height=720):
    """Use the pack's own render_frame to produce 4 stills per scene (fast)."""
    scenes = mod.SCENES
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    contact_stills = []

    for idx, scene in enumerate(scenes, 1):
        scene_dir = frames_dir / f"scene_{idx:03d}"
        scene_dir.mkdir(exist_ok=True)
        for si, u in enumerate([0.0, 0.35, 0.72, 0.99]):
            out = scene_dir / f"still_{si:02d}.jpg"
            if out.exists():
                continue
            frame_idx = int(u * 59)
            frame_count = 60
            im = mod.render_frame(scene, frame_idx, frame_count, width, height, idx * 1000 + si)
            im.save(out, quality=92)
        contact_stills.append(scene_dir)

    return contact_stills


def build_narrated_storyboard(mod, output_dir: Path, args):
    """
    Fast mode: narrated slideshow using 4 stills per scene + edge-tts.
    Yields a watchable narrated video in ~5 minutes total.
    """
    scenes = mod.SCENES
    ffmpeg = require_ffmpeg()

    # 1. Ensure stills exist
    print("Generating contact sheet stills...")
    generate_contact_sheet_stills(mod, output_dir, args.width, args.height)

    # 2. Narrate
    print("Generating narration...")
    asyncio.run(narrate(mod, output_dir, args))

    # 3. Build per-scene slideshow clips from the 4 stills
    scenes_dir = output_dir / "scenes"
    scenes_dir.mkdir(exist_ok=True)

    narration_dir = output_dir / "narration"
    slideshow_clips = []

    print("Assembling narrated storyboard...")
    for idx, scene in enumerate(scenes, 1):
        scene_dir = output_dir / "frames" / f"scene_{idx:03d}"
        clip_path = scenes_dir / f"scene_{idx:03d}.mp4"
        audio_path = narration_dir / f"scene_{idx:03d}.wav"

        if clip_path.exists():
            slideshow_clips.append(clip_path)
            continue

        stills = sorted(scene_dir.glob("still_*.jpg"))
        if not stills:
            continue

        dur = scene.duration if hasattr(scene, 'duration') else scene.get('duration', 6.0)

        # Build slideshow: each still gets 25% of scene duration
        # Use concat with crossfade (or just image sequence with per-image duration)
        # Simplest: use ffmpeg with concat of individual image inputs
        filter_parts = []
        input_idx = 0
        inputs = []
        still_dur = dur / len(stills)

        for s in stills:
            inputs.extend(["-loop", "1", "-i", str(s), "-t", str(still_dur)])

        # If audio exists, use it; otherwise generate silent
        has_audio = audio_path.exists()

        if has_audio:
            inputs.extend(["-i", str(audio_path)])

        filter_complex = (
            f"[0:v][1:v][2:v][3:v]"
            f"concat=n={len(stills)}:v=1:a=0,format=yuv420p[v]"
        )

        cmd = [ffmpeg, "-y"] + inputs
        if has_audio:
            audio_idx = len(stills)
            filter_complex = (
                f"[0:v][1:v][2:v][3:v]"
                f"concat=n={len(stills)}:v=1:a=0[v];"
                f"[v][{audio_idx}:a]concat=n=1:v=0:a=1[a]"
            )
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
            ])
        else:
            cmd.extend(["-filter_complex", filter_complex, "-map", "[v]"])

        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p", str(clip_path)])

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        slideshow_clips.append(clip_path)
        print(f"  Scene {idx:02d}/{len(scenes):02d} — {dur:.1f}s")

    # 4. Concatenate all scene clips
    if slideshow_clips:
        final = output_dir / "life_crosses_barriers_storyboard.mp4"
        concat_txt = output_dir / "storyboard_concat.txt"
        concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in slideshow_clips))

        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_txt), "-c", "copy", "-movflags", "+faststart",
             str(final)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"\nNarrated storyboard: {final}")

    return slideshow_clips


async def narrate(mod, output_dir: Path, args):
    """Generate edge-tts narration per scene. Returns list of scene audio durations."""
    scenes = mod.SCENES
    narration_dir = output_dir / "narration"
    narration_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for idx, scene in enumerate(scenes, 1):
        wav = narration_dir / f"scene_{idx:03d}.wav"
        if wav.exists():
            dur = get_audio_duration(wav)
            results.append({"index": idx, "duration": dur, "cached": True})
            continue

        text = scene.narration if hasattr(scene, 'narration') else scene.get('narration', '')
        if not text:
            results.append({"index": idx, "duration": 0, "cached": False})
            continue

        await edge_tts.Communicate(text, args.voice).save(str(wav))
        dur = get_audio_duration(wav)
        results.append({"index": idx, "duration": dur, "cached": False})

        scene_dur = scene.duration if hasattr(scene, 'duration') else scene.get('duration', 6.0)
        status = "OK" if abs(dur - scene_dur) < 2.0 else f"MISMATCH ({dur:.1f}s audio vs {scene_dur:.1f}s scene)"

    # Build concatenated full narration
    wavs = sorted(narration_dir.glob("scene_*.wav"))
    if wavs:
        combined = narration_dir / "narration_full.wav"
        if not combined.exists():
            concat_txt = narration_dir / "concat.txt"
            concat_txt.write_text("\n".join(f"file '{w.resolve()}'" for w in wavs))
            ffmpeg = require_ffmpeg()
            subprocess.run(
                [ffmpeg, "-y", "-f", "concat", "-safe", "0",
                 "-i", str(concat_txt), "-c", "copy", str(combined)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    return results


def render_parallel(mod, output_dir: Path, args):
    """
    Production mode: render all scenes in parallel using multiprocessing.
    Each scene farmed to a separate process.
    Then narrate and mux.
    """
    import multiprocessing as mp
    from functools import partial

    scenes = mod.SCENES
    ncpus = args.workers or mp.cpu_count()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "frames").mkdir(exist_ok=True)
    (output_dir / "scenes").mkdir(exist_ok=True)

    print(f"Production render of {len(scenes)} scenes on {ncpus} workers...")
    print(f"  Resolution: {args.width}x{args.height} @ {args.fps}fps")

    # Build render args for each scene
    render_tasks = []
    for idx, scene in enumerate(scenes, 1):
        frame_count = max(2, round(scene.duration * args.fps))
        render_tasks.append((idx, scene, frame_count, args.width, args.height))

    def render_one(task):
        idx, scene, frame_count, w, h = task
        frame_dir = output_dir / "frames" / f"scene_{idx:03d}"
        frame_dir.mkdir(parents=True, exist_ok=True)
        scene_mp4 = output_dir / "scenes" / f"scene_{idx:03d}.mp4"

        if scene_mp4.exists():
            return idx, "cached"

        for fi in range(frame_count):
            path = frame_dir / f"{fi:05d}.jpg"
            if path.exists():
                continue
            u = fi / max(1, frame_count - 1)
            t = u * scene.duration
            # Render frame using the pack's functions (imported in each worker)
            im = mod.render_frame(scene, fi, frame_count, w, h, idx * 1000 + fi)
            im.save(path, quality=92, subsampling=0)

        # Encode to MP4
        ffmpeg = require_ffmpeg()
        subprocess.run(
            [ffmpeg, "-y", "-framerate", str(args.fps),
             "-i", str(frame_dir / "%05d.jpg"),
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", str(scene_mp4)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return idx, "rendered"

    # Run in parallel
    start = time.time()
    with mp.Pool(ncpus) as pool:
        for idx, status in pool.imap_unordered(render_one, render_tasks):
            elapsed = time.time() - start
            scene = scenes[idx - 1]
            title = scene.title if hasattr(scene, 'title') else scene.get('title', '')
            print(f"  [{idx:02d}/{len(scenes):02d}] {title} — {status} ({elapsed:.0f}s)", flush=True)

    # Concatenate
    scene_mp4s = sorted((output_dir / "scenes").glob("scene_*.mp4"))
    if scene_mp4s:
        final = output_dir / "life_crosses_barriers.mp4"
        # Check if there's a pack-specific name
        if hasattr(mod, "OUTPUT"):
            # Try to find the pack's own naming convention
            pass
        concat_txt = output_dir / "concat.txt"
        concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_mp4s))
        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_txt), "-c", "copy", "-movflags", "+faststart",
             str(final)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        total_dur = sum(s.duration for s in scenes)
        print(f"\n  Final: {final} ({total_dur:.0f}s, {total_dur/60:.1f} min)")

    return scene_mp4s


def mux_narration(output_dir: Path):
    """Mux the full narration WAV into the final MP4."""
    mp4 = output_dir / "life_crosses_barriers.mp4"
    wav = output_dir / "narration" / "narration_full.wav"
    if not mp4.exists() or not wav.exists():
        return

    narrated = output_dir / "life_crosses_barriers_narrated.mp4"
    ffmpeg = require_ffmpeg()
    subprocess.run(
        [ffmpeg, "-y", "-i", str(mp4), "-i", str(wav),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(narrated)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"Narrated: {narrated}")


def parse_args():
    parser = argparse.ArgumentParser(description="Platinum Pack Render + Narrate Pipeline")
    parser.add_argument("pack", type=str, help="Path to _platinum.py file")
    parser.add_argument("--storyboard", action="store_true",
                        help="Fast mode: narrated slideshow from 4 stills per scene")
    parser.add_argument("--production", action="store_true",
                        help="Full render: parallel scene rendering + narration")
    parser.add_argument("--narrate-only", action="store_true",
                        help="Only generate narration for an already-rendered pack")
    parser.add_argument("--voice", default="en-US-AriaNeural",
                        help="Edge TTS voice")
    parser.add_argument("--fps", type=int, default=5,
                        help="Frames per second (default: 5 for draft)")
    parser.add_argument("--width", type=int, default=640,
                        help="Render width (default: 640 for draft)")
    parser.add_argument("--height", type=int, default=360,
                        help="Render height (default: 360 for draft)")
    parser.add_argument("--workers", type=int, default=0,
                        help="Parallel workers (default: CPU count)")
    return parser.parse_args()


def main():
    args = parse_args()
    mod = load_pack(args.pack)
    output_dir = preview_output(mod)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timeline first (fast, no frames needed)
    if hasattr(mod, "export_timeline"):
        tl = mod.export_timeline()
        print(f"Timeline: {tl}")
    print(f"Scenes: {len(mod.SCENES)}")
    print(f"Runtime: {sum(s.duration for s in mod.SCENES)/60:.1f} min")

    if args.narrate_only:
        asyncio.run(narrate(mod, output_dir, args))
        mux_narration(output_dir)
        return

    if args.storyboard:
        build_narrated_storyboard(mod, output_dir, args)
        return

    if args.production:
        asyncio.run(narrate(mod, output_dir, args))
        render_parallel(mod, output_dir, args)
        mux_narration(output_dir)
        return

    print("Specify --storyboard (fast) or --production (full). Use --narrate-only if already rendered.")


if __name__ == "__main__":
    main()
