#!/usr/bin/env python3
"""
Background render + narration + publish runner for platinum packs.
Launches in screen, logs progress, provides status.

Usage:
    # Launch storyboard (fast: narrated slideshow)
    python run_bg.py life_crosses_barriers_platinum.py --storyboard

    # Launch + auto-publish to studio.tantrafiles.xyz when done
    python run_bg.py life_crosses_barriers_platinum.py --storyboard --publish

    # Production render with publish
    python run_bg.py life_crosses_barriers_platinum.py --production --publish

    # Check status
    python run_bg.py --status

    # Tail the log
    python run_bg.py --tail life_crosses

    # Cancel a running render
    python run_bg.py --cancel life_crosses
"""
import argparse, json, os, shlex, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runs"
LOG_DIR.mkdir(exist_ok=True)


def sanitize(s: str) -> str:
    return s.replace("_platinum", "").replace(".py", "").replace("/", "_")


def run_background(pack_path: str, mode: str, fps: int, width: int, height: int,
                   voice: str, publish: bool, slug: str):
    """Launch the render in a screen session."""
    pack = Path(pack_path)
    if not pack.exists():
        pack = ROOT / pack_path
    if not pack.exists():
        print(f"Pack not found: {pack_path}")
        sys.exit(1)

    name = sanitize(pack.stem)
    log_path = LOG_DIR / f"{name}.log"
    status_path = LOG_DIR / f"{name}.status.json"

    status_path.write_text(json.dumps({
        "pack": pack.name,
        "mode": mode,
        "publish": publish,
        "status": "starting",
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }))

    script_path = ROOT / "render_narrate.py"
    publish_script = ROOT / "publish_pipeline.py"

    render_cmd = [
        "python3", str(script_path), str(pack),
        f"--{mode}",
        "--fps", str(fps),
        "--width", str(width),
        "--height", str(height),
        "--voice", voice,
    ]

    # Build the wrapper command chain: render → (optionally) publish → update status
    lines = [
        f"cd {shlex.quote(str(ROOT))}",
        "(",
        "  " + " ".join(shlex.quote(str(c)) for c in render_cmd),
        f") 2>&1 | tee {shlex.quote(str(log_path))}",
    ]

    if publish:
        outdir = f"output_{name}"
        slug_arg = f"--slug {shlex.quote(slug)}" if slug else ""
        lines.append(
            f"R2_ACCESS_KEY=$({shlex.quote(str(shutil.which('grep')))} -oP 'R2_ACCESS_KEY=\\K.*' {shlex.quote(str(ROOT.parent / '.env'))} | head -1) "
            f"R2_SECRET_KEY=$({shlex.quote(str(shutil.which('grep')))} -oP 'R2_SECRET_KEY=\\K.*' {shlex.quote(str(ROOT.parent / '.env'))} | head -1) "
            f"python3 {shlex.quote(str(publish_script))} {shlex.quote(str(ROOT / outdir))} {slug_arg} "
            f"--narrated 2>&1 | tee -a {shlex.quote(str(log_path))}"
        )

    lines.extend([
        'python3 -c "'
        f"import json; from pathlib import Path; "
        f"p = Path('{shlex.quote(str(status_path))}'); "
        f"d = json.loads(p.read_text()); "
        f"d['status'] = 'completed'; "
        f"d['finished'] = '{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}'; "
        f"p.write_text(json.dumps(d, indent=2))"
        '"',
        "echo 'RENDER_COMPLETE'",
    ])

    wrapper_cmd = "\n".join(lines)

    screen_cmd = [
        "screen", "-dmS", f"render_{name}",
        "bash", "-c", wrapper_cmd,
    ]

    subprocess.run(screen_cmd)
    print(f"Launched in screen session: render_{name}")
    print(f"  Log: {log_path}")
    if publish:
        print(f"  Auto-publish: enabled → studio.tantrafiles.xyz")
    print(f"  Run: python {sys.argv[0]} --status {name}")
    print(f"  Tail: python {sys.argv[0]} --tail {name}")


def show_status(pack_name: str | None = None):
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

        screen_check = subprocess.run(
            ["screen", "-ls"], capture_output=True, text=True, timeout=5
        )
        running = f"render_{name}" in screen_check.stdout

        publish_tag = " PUB" if data.get("publish") else ""
        print(f"{name:35s} {status:12s} {'RUNNING' if running else '':8s} {log_size//1024:>4d}K{publish_tag}")


def tail_log(pack_name: str):
    logs = sorted(LOG_DIR.glob("*.log"))
    if not logs:
        print("No logs found.")
        return
    if pack_name:
        log = LOG_DIR / f"{sanitize(pack_name)}.log"
        if log.exists():
            subprocess.run(["tail", "-f", str(log)])
            return
        for l in logs:
            if pack_name.lower() in l.stem.lower():
                subprocess.run(["tail", "-f", str(l)])
                return
        print(f"No log matching '{pack_name}'")
    else:
        latest = max(logs, key=lambda p: p.stat().st_mtime)
        subprocess.run(["tail", "-f", str(latest)])


def cancel_render(pack_name: str | None = None):
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
    parser = argparse.ArgumentParser(description="Background render + publish runner")
    parser.add_argument("pack", nargs="?", type=str, help="Pack file or name")
    parser.add_argument("--storyboard", action="store_true", help="Fast narrated storyboard")
    parser.add_argument("--production", action="store_true", help="Full production render")
    parser.add_argument("--publish", action="store_true", help="Auto-publish to studio.tantrafiles.xyz")
    parser.add_argument("--slug", type=str, default="", help="Override slug for dashboard URL")
    parser.add_argument("--status", nargs="?", const=True, default=False, help="Show render status")
    parser.add_argument("--tail", nargs="?", const=True, default=False, help="Tail render log")
    parser.add_argument("--cancel", nargs="?", const=True, default=False, help="Cancel running renders")
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
    run_background(args.pack, mode, args.fps, args.width, args.height,
                   args.voice, args.publish, args.slug)


if __name__ == "__main__":
    main()
