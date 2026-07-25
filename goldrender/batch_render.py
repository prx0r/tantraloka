#!/usr/bin/env python3
"""
Tantrāloka Batch Render Engine
Renders all platinum packs or selected subsets with resume, logging, and reporting.

Usage:
    python batch_render.py                   # Render all packs (preview mode)
    python batch_render.py --full            # Full render (all scenes → MP4)
    python batch_render.py --pack fire       # Render one pack by name match
    python batch_render.py --tier 1          # Render first 10 packs
    python batch_render.py --list            # List all discoverable packs
    python batch_render.py --force           # Re-run even if previously completed
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RENDERS_DIR = ROOT / "renders"
BATCH_LOG = RENDERS_DIR / "render.log"
BATCH_MANIFEST = RENDERS_DIR / "batch_manifest.json"

# Packs grouped by when they were written (for tier filtering)
ALL_PACKS = sorted(ROOT.glob("*_platinum.py"))
# Infer tiers by creation order (first 10 = T1, next 10 = T2, etc.)
TIER_MAP = {}
for i, p in enumerate(ALL_PACKS):
    tier = (i // 10) + 1
    TIER_MAP[p.name] = tier


def discover_packs(args) -> list[Path]:
    """Discover and filter packs based on CLI args."""
    packs = list(ALL_PACKS)

    if args.pack:
        packs = [p for p in packs if args.pack.lower() in p.stem.lower()]
        if not packs:
            print(f"No packs matching '{args.pack}'")
            sys.exit(1)

    if args.tier:
        packs = [p for p in packs if TIER_MAP.get(p.name, 99) == args.tier]
        if not packs:
            print(f"No packs in tier {args.tier}")
            sys.exit(1)

    if args.until:
        packs = packs[:args.until]

    return packs


def pack_output_dir(pack: Path) -> Path:
    """Detect the output dir a pack will write to."""
    # Most packs use output_{stem} named dir
    stem = pack.stem
    # Remove trailing _platinum or _pack
    for suffix in ["_platinum", "_pack"]:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return ROOT / f"output_{stem}"


def pack_already_done(pack: Path) -> bool:
    """Check if a pack has already been fully rendered."""
    outdir = pack_output_dir(pack)
    mp4s = list(outdir.glob("*.mp4")) if outdir.exists() else []
    return len(mp4s) > 0


def render_pack(pack: Path, args) -> dict:
    """Run a single pack and return its result record."""
    record = {
        "name": pack.stem,
        "status": "pending",
        "started": None,
        "completed": None,
        "elapsed_seconds": 0,
        "error": None,
        "output_dir": str(pack_output_dir(pack)),
        "mp4": None,
    }

    # Check if already done
    if not args.force and pack_already_done(pack):
        record["status"] = "skipped"
        record["error"] = "already rendered"
        return record

    print(f"\n{'='*60}")
    print(f"  Rendering: {pack.stem}")
    print(f"{'='*60}")

    mode = "preview" if args.preview else ("scene" if args.scene else "full")
    cmd = [sys.executable, str(pack)]

    if args.preview:
        cmd.append("--preview")
    elif args.scene:
        cmd.extend(["--scene", str(args.scene)])

    if args.fps and args.fps != 10:
        cmd.extend(["--fps", str(args.fps)])
    if args.width and args.width != 1280:
        cmd.extend(["--width", str(args.width)])
    if args.height and args.height != 720:
        cmd.extend(["--height", str(args.height)])

    start = time.time()
    record["started"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=args.timeout if args.timeout else None,
        )
        elapsed = time.time() - start
        record["elapsed_seconds"] = round(elapsed, 1)

        # Log output
        for line in result.stdout.split("\n"):
            if line.strip():
                print(f"  {line.strip()}")
        if result.stderr:
            for line in result.stderr.split("\n")[-5:]:
                if line.strip():
                    print(f"  [stderr] {line.strip()}")

        if result.returncode == 0:
            record["status"] = "done"
            # Find the output MP4
            outdir = pack_output_dir(pack)
            mp4s = list(outdir.glob("*.mp4")) if outdir.exists() else []
            if mp4s:
                record["mp4"] = str(mp4s[0])
            print(f"  ✓ Completed in {elapsed:.1f}s")
        else:
            record["status"] = "failed"
            record["error"] = f"exit code {result.returncode}"
            print(f"  ✗ Failed (exit {result.returncode})")

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        record["elapsed_seconds"] = round(elapsed, 1)
        record["status"] = "failed"
        record["error"] = "timeout"
        print(f"  ✗ Timed out after {elapsed:.1f}s")

    except Exception as e:
        elapsed = time.time() - start
        record["elapsed_seconds"] = round(elapsed, 1)
        record["status"] = "failed"
        record["error"] = str(e)
        print(f"  ✗ Error: {e}")

    record["completed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))
    return record


def write_log(records: list[dict]):
    """Write a human-readable log."""
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    with open(BATCH_LOG, "w") as f:
        f.write(f"Batch Render Log — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        for r in records:
            status_icon = "✓" if r["status"] == "done" else ("⏭" if r["status"] == "skipped" else "✗")
            f.write(f"  {status_icon} {r['name']:45s} {r['status']:8s} {r['elapsed_seconds']:6.1f}s\n")
            if r["error"]:
                f.write(f"     Error: {r['error']}\n")
        done = sum(1 for r in records if r["status"] == "done")
        skipped = sum(1 for r in records if r["status"] == "skipped")
        failed = sum(1 for r in records if r["status"] == "failed")
        total_elapsed = sum(r["elapsed_seconds"] for r in records)
        f.write(f"\n{'='*60}\n")
        f.write(f"  Total: {len(records)}  Done: {done}  Skipped: {skipped}  Failed: {failed}\n")
        f.write(f"  Total render time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)\n")


def write_manifest(records: list[dict], args):
    """Write a JSON batch manifest."""
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    done = sum(1 for r in records if r["status"] == "done")
    skipped = sum(1 for r in records if r["status"] == "skipped")
    failed = sum(1 for r in records if r["status"] == "failed")
    total_elapsed = sum(r["elapsed_seconds"] for r in records)

    manifest = {
        "batch_id": time.strftime("batch_%Y%m%d_%H%M%S"),
        "started": records[0]["started"] if records else None,
        "completed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_elapsed_seconds": round(total_elapsed, 1),
        "config": {
            "fps": args.fps or 10,
            "width": args.width or 1280,
            "height": args.height or 720,
            "mode": "preview" if args.preview else "full",
            "tier": args.tier,
        },
        "packs_total": len(records),
        "packs_rendered": done,
        "packs_skipped": skipped,
        "packs_failed": failed,
        "packs": records,
    }

    with open(BATCH_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nManifest: {BATCH_MANIFEST}")


def list_packs(packs: list[Path]):
    """List all discoverable packs with metadata."""
    print(f"{'Pack':45s} {'Tier':6s} {'Scenes':7s} {'Status':10s}")
    print("-" * 70)
    for p in packs:
        # Try to extract scene count
        with open(p) as f:
            content = f.read()
        scene_count = content.count('Scene("') + content.count('Scene(\n')
        tier = TIER_MAP.get(p.name, "?")
        status = "ready"
        if pack_already_done(p):
            status = "rendered"
        print(f"{p.stem:45s} T{tier:<4} {scene_count:<5} {status:10s}")


def parse_args():
    parser = argparse.ArgumentParser(description="Tantrāloka Batch Render Engine")
    parser.add_argument("--list", action="store_true", help="List all packs and exit")
    parser.add_argument("--full", action="store_true", help="Full render (default is preview)")
    parser.add_argument("--preview", action="store_true", help="Preview mode (4 stills per pack)")
    parser.add_argument("--pack", type=str, help="Render packs matching name (substring)")
    parser.add_argument("--tier", type=int, help="Render a specific tier (1-4)")
    parser.add_argument("--until", type=int, help="Render first N packs only")
    parser.add_argument("--scene", type=int, help="Render a single scene from each pack")
    parser.add_argument("--force", action="store_true", help="Re-render even if already done")
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--timeout", type=int, default=3600, help="Per-pack timeout in seconds")
    return parser.parse_args()


def main():
    args = parse_args()

    packs = discover_packs(args)

    if args.list:
        list_packs(packs)
        return

    if not packs:
        print("No packs found to render.")
        return

    # If neither --full nor --preview nor --scene, default to preview
    if not args.full and not args.preview and not args.scene:
        args.preview = True
        print("Defaulting to --preview mode (use --full for full render)")

    print(f"Found {len(packs)} packs to render (mode: {'preview' if args.preview else 'full'})")
    print(f"Timeout per pack: {args.timeout}s")

    records = []
    for i, pack in enumerate(packs):
        print(f"\n[{i+1}/{len(packs)}] ", end="")
        record = render_pack(pack, args)

        # Clean up preview frame dirs if preview mode
        if args.preview:
            outdir = pack_output_dir(pack)
            for frame_dir in (outdir / "frames").glob("scene_*"):
                shutil.rmtree(frame_dir, ignore_errors=True)

        records.append(record)

    write_log(records)
    write_manifest(records, args)

    print(f"\n{'='*60}")
    done = sum(1 for r in records if r["status"] == "done")
    skipped = sum(1 for r in records if r["status"] == "skipped")
    failed = sum(1 for r in records if r["status"] == "failed")
    total_elapsed = sum(r["elapsed_seconds"] for r in records)
    print(f"  Done: {done}  Skipped: {skipped}  Failed: {failed}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Log: {BATCH_LOG}")


if __name__ == "__main__":
    main()
