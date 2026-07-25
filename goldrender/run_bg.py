#!/usr/bin/env python3
"""
Background render + narration runner for platinum packs.
Launches in screen, logs progress, provides status.

Usage:
    # Launch storyboard (fast: narrated slideshow from 4 stills per scene)
    python run_bg.py life_crosses_barriers_platinum.py --storyboard

    # Launch production (full per-frame render + narration, parallel)
    python run_bg.py life_crosses_barriers_platinum.py --production

    # Check status
    python run_bg.py --status

    # Check status for a specific pack
    python run_bg.py --status life_crosses

    # Tail the log
    python run_bg.py --tail

    # Cancel a running render
    python run_bg.py --cancel
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runs"
LOG_DIR.mkdir(exist_ok=True)


def sanitize(s: str) -> str:
    return s.replace("_platinum", "").replace(".py", "").replace("/", "_")


def run_background(pack_path: str, mode: str, fps: int, width: int, height: int, voice: str):
    """Launch the render in a screen session."""
    pack = Path(pack_path)
    if not pack.exists():
        # Try goldrender/
        pack = ROOT / pack_path
    if not pack.exists():
        print(f"Pack not found: {pack_path}")
        sys.exit(1)

    name = sanitize(pack.stem)
    log_path = LOG_DIR / f"{name}.log"
    status_path = LOG_DIR / f"{name}.status.json"

    # Write initial status
    status_path.write_text(json.dumps({
        "pack": pack.name,
        "mode": mode,
        "status": "starting",
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }))

    script_path = ROOT / "render_narrate.py"

    # Build command
    cmd = [
        "python3", str(script_path), str(pack),
        f"--{mode}",
        "--fps", str(fps),
        "--width", str(width),
        "--height", str(height),
        "--voice", voice,
    ]

    # Status updater loop runs alongside
    wrapper_cmd = f"""
cd {shlex.quote(str(ROOT))}
(
  {' '.join(shlex.quote(str(c)) for c in cmd)}
) 2>&1 | tee {shlex.quote(str(log_path))}
python3 -c "
import json
from pathlib import Path
p = Path('{shlex.quote(str(status_path))}')
d = json.loads(p.read_text())
d['status'] = 'completed'
d['finished'] = '{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}'
p.write_text(json.dumps(d, indent=2))
"
echo 'RENDER_COMPLETE'
"""

    import shlex
    screen_cmd = [
        "screen", "-dmS", f"render_{name}",
        "bash", "-c", wrapper_cmd,
    ]

    subprocess.run(screen_cmd)
    print(f"Launched in screen session: render_{name}")
    print(f"  Log: {log_path}")
    print(f"  Run: python {sys.argv[0]} --status {name}")
    print(f"  Tail: python {sys.argv[0]} --tail {name}")


def show_status(pack_name: str | None = None):
    """Show running/completed renders."""
    statuses = sorted(LOG_DIR.glob("*.status.json"))
    if not statuses:
        print("No renders found.")
        return

    for sp in statuses:
        data = json.loads(sp.read_text())
        name = sp.stem.replace(".status", "")
        if pack_name and pack_name.lower() not in name.lower():
            continue

        status = data.get("status", "?")
        log = LOG_DIR / f"{name}.log"
        log_size = log.stat().st_size if log.exists() else 0

        # Check if screen session is still alive
        screen_check = subprocess.run(
            ["screen", "-ls"], capture_output=True, text=True, timeout=5
        )
        running = f"render_{name}" in screen_check.stdout

        print(f"{name:40s} {status:12s} {'RUNNING' if running else 'STOPPED':8s} {log_size//1024:>4d}K log")


def tail_log(pack_name: str):
    """Tail a render log."""
    logs = sorted(LOG_DIR.glob("*.log"))
    if not logs:
        print("No logs found.")
        return

    if pack_name:
        log = LOG_DIR / f"{sanitize(pack_name)}.log"
        if log.exists():
            subprocess.run(["tail", "-f", str(log)])
            return
        # Try substring
        for l in logs:
            if pack_name.lower() in l.stem.lower():
                subprocess.run(["tail", "-f", str(l)])
                return
        print(f"No log matching '{pack_name}'")
    else:
        # Show latest log
        latest = max(logs, key=lambda p: p.stat().st_mtime)
        subprocess.run(["tail", "-f", str(latest)])


def cancel_render(pack_name: str | None = None):
    """Kill screen sessions for renders."""
    result = subprocess.run(["screen", "-ls"], capture_output=True, text=True, timeout=5)
    lines = result.stdout.splitlines()
    killed = 0
    for line in lines:
        if "render_" in line:
            name = line.strip().split()[0]
            if pack_name and pack_name not in name:
                continue
            subprocess.run(["screen", "-S", name, "-X", "quit"])
            killed += 1
            print(f"Killed: {name}")
    if killed == 0:
        print("No running renders found.")


def parse_args():
    parser = argparse.ArgumentParser(description="Background render runner")
    parser.add_argument("pack", nargs="?", type=str, help="Pack file or name")
    parser.add_argument("--storyboard", action="store_true", help="Fast narrated storyboard")
    parser.add_argument("--production", action="store_true", help="Full production render")
    parser.add_argument("--status", nargs="?", const=True, default=False,
                        help="Show render status")
    parser.add_argument("--tail", nargs="?", const=True, default=False,
                        help="Tail render log")
    parser.add_argument("--cancel", nargs="?", const=True, default=False,
                        help="Cancel running renders")
    parser.add_argument("--fps", type=int, default=5, help="FPS for rendering")
    parser.add_argument("--width", type=int, default=640, help="Render width")
    parser.add_argument("--height", type=int, default=360, help="Render height")
    parser.add_argument("--voice", default="en-US-AriaNeural", help="TTS voice")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.cancel is not False:
        cancel_render(args.cancel if isinstance(args.cancel, str) else None)
        return

    if args.tail is not False:
        tail_log(args.tail if isinstance(args.tail, str) else None)
        return

    if args.status is not False:
        show_status(args.status if isinstance(args.status, str) else None)
        return

    if not args.pack:
        print("Specify a pack file or use --status/--tail/--cancel")
        sys.exit(1)

    if not args.storyboard and not args.production:
        print("Specify --storyboard (fast) or --production (full)")
        sys.exit(1)

    mode = "storyboard" if args.storyboard else "production"
    run_background(args.pack, mode, args.fps, args.width, args.height, args.voice)


if __name__ == "__main__":
    main()
