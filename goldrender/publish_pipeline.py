#!/usr/bin/env python3
"""
Publish — upload rendered packs to blog-video-assets R2 and register on studio.tantrafiles.xyz.

Usage:
    # Publish a rendered pack (uploads + registers)
    python publish_pipeline.py output_life_crosses/

    # Publish with specific slug and essay
    python publish_pipeline.py output_life_crosses/ --slug life-crosses-barriers --essay "01_life_crosses_barriers.md"

    # Publish narrated version
    python publish_pipeline.py output_life_crosses/ --narrated

    # Just upload to R2 without registering on dashboard
    python publish_pipeline.py output_life_crosses/ --upload-only

    # Just register on dashboard without uploading
    python publish_pipeline.py output_life_crosses/ --register-only

    # List what's published
    python publish_pipeline.py --list

    # List published packs on studio
    python publish_pipeline.py --list-remote
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Load .env from project root
dotenv = ROOT.parent / ".env"
if dotenv.exists():
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v.strip().strip("\"'"))

DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8766")

# R2 config (blog-video-assets — served by studio.tantrafiles.xyz)
R2_ENDPOINT = os.environ.get("R2_ENDPOINT", "https://954612afb5a97bb15dddcdc70176813d.r2.cloudflarestorage.com")
R2_BUCKET = os.environ.get("R2_BUCKET", "blog-video-assets")
R2_PREFIX = "renders"


def r2_client():
    """Get boto3 S3 client for R2."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY", ""),
        aws_secret_access_key=os.environ.get("R2_SECRET_KEY", ""),
    )


def upload_to_r2(local_path: Path, r2_key: str) -> bool:
    """Upload a file to R2, returning success."""
    s3 = r2_client()
    content_type_map = {
        ".mp4": "video/mp4",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".json": "application/json",
        ".wav": "audio/wav",
        ".md": "text/markdown",
        ".py": "text/x-python",
    }
    ext = local_path.suffix.lower()
    content_type = content_type_map.get(ext, "application/octet-stream")

    try:
        s3.upload_file(
            str(local_path), R2_BUCKET, r2_key,
            ExtraArgs={"ContentType": content_type, "CacheControl": "public, max-age=86400"},
        )
        return True
    except Exception as e:
        print(f"  Upload failed: {e}", file=sys.stderr)
        return False


def upload_pack(output_dir: Path, slug: str, narrated: bool = False) -> dict:
    """Upload render files to R2. Returns dict of uploaded keys."""
    uploaded = {}

    # Main MP4
    # Find the best MP4 to publish
    candidates = [
        "life_crosses_barriers_narrated.mp4",
        "life_crosses_barriers_storyboard.mp4",
        "life_crosses_barriers.mp4",
        "final.mp4",
        "output.mp4",
    ]
    mp4 = None
    for name in candidates:
        candidate = output_dir / name
        if candidate.exists():
            mp4 = candidate
            break
    if not mp4:
        print(f"No MP4 found in {output_dir}")
        return uploaded

    r2_key = f"{R2_PREFIX}/{slug}/{mp4.name}"
    if upload_to_r2(mp4, r2_key):
        uploaded["mp4"] = r2_key
        print(f"  Uploaded: {r2_key}")

    # Narration timeline
    tl = output_dir / "narration_timeline.json"
    if tl.exists():
        r2_key = f"{R2_PREFIX}/{slug}/narration_timeline.json"
        if upload_to_r2(tl, r2_key):
            uploaded["timeline"] = r2_key
            print(f"  Uploaded: {r2_key}")

    # Contact sheet
    cs = output_dir / "contact_sheet.jpg"
    if cs.exists():
        r2_key = f"{R2_PREFIX}/{slug}/contact_sheet.jpg"
        if upload_to_r2(cs, r2_key):
            uploaded["contact_sheet"] = r2_key
            print(f"  Uploaded: {r2_key}")

    # Narrated full audio
    wav = output_dir / "narration" / "narration_full.wav"
    if wav.exists():
        r2_key = f"{R2_PREFIX}/{slug}/narration_full.wav"
        if upload_to_r2(wav, r2_key):
            uploaded["audio"] = r2_key
            print(f"  Uploaded: {r2_key}")

    # Per-scene narrated clips
    narrated_scenes = output_dir / "scenes_narrated"
    if narrated_scenes.exists():
        scene_keys = []
        for clip in sorted(narrated_scenes.glob("*.mp4")):
            r2_key = f"{R2_PREFIX}/{slug}/scenes/{clip.name}"
            if upload_to_r2(clip, r2_key):
                scene_keys.append(r2_key)
        if scene_keys:
            uploaded["scenes"] = scene_keys
            print(f"  Uploaded {len(scene_keys)} scene clips")

    return uploaded


def register_on_dashboard(
    slug: str,
    title: str,
    mp4_path: str,
    essay: str = "",
    duration: float = 0,
    shots: list[dict] | None = None,
) -> dict | None:
    """Register a video in the studio.tantrafiles.xyz dashboard."""
    import urllib.request

    mp4_url = f"/api/r2/{mp4_path}" if not mp4_path.startswith("/") else mp4_path

    payload = {
        "id": slug,
        "title": title,
        "essay": essay,
        "channel": "Tantra Files",
        "mp4_path": mp4_url,
        "duration": duration,
        "shots": shots or [],
        "status": "review",
    }

    try:
        req = urllib.request.Request(
            f"{DASHBOARD_URL}/api/final/videos",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        print(f"  Registered: {result.get('id')} (status: {result.get('status')})")
        return result
    except Exception as e:
        print(f"  Registration failed: {e}", file=sys.stderr)
        return None


def list_published() -> list[dict]:
    """List what's in the R2 bucket under renders/."""
    s3 = r2_client()
    try:
        resp = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"{R2_PREFIX}/", Delimiter="/")
        packs = []
        for prefix in resp.get("CommonPrefixes", []):
            pack_dir = prefix["Prefix"].replace(f"{R2_PREFIX}/", "").rstrip("/")
            packs.append({"slug": pack_dir, "r2_prefix": prefix["Prefix"]})
        return packs
    except Exception as e:
        print(f"List failed: {e}")
        return []


def list_dashboard() -> list[dict]:
    """List videos registered on the dashboard."""
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"{DASHBOARD_URL}/api/final/videos", timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        print(f"Dashboard list failed: {e}")
        return []


def load_timeline(output_dir: Path) -> tuple[dict | None, float, list]:
    """Load timeline from output directory."""
    tl = output_dir / "narration_timeline.json"
    if not tl.exists():
        return None, 0, []

    data = json.loads(tl.read_text())
    scenes = data.get("scenes", [])
    duration = sum(
        s.get("duration", s.get("end_seconds", 0) - s.get("start_seconds", 0))
        for s in scenes
    )
    return data, duration, scenes


def slugify(name: str) -> str:
    """Convert a pack name or path to a URL-safe slug."""
    name = Path(name).stem.replace("_platinum", "").replace("output_", "")
    name = name.replace(" ", "-").lower()
    name = re.sub(r"[^a-z0-9-]", "", name)
    return name


def infer_title(output_dir: Path) -> str:
    """Infer a human-readable title from the timeline or directory name."""
    tl = output_dir / "narration_timeline.json"
    if tl.exists():
        try:
            data = json.loads(tl.read_text())
            return data.get("title", output_dir.name.replace("output_", "").replace("_", " "))
        except:
            pass
    return output_dir.name.replace("output_", "").replace("_", " ")


def parse_args():
    parser = argparse.ArgumentParser(description="Publish rendered packs to studio.tantrafiles.xyz")
    parser.add_argument("output_dir", nargs="?", type=str, help="Pack output directory")
    parser.add_argument("--slug", type=str, help="Override slug for R2 path and dashboard ID")
    parser.add_argument("--essay", type=str, default="", help="Source essay filename")
    parser.add_argument("--narrated", action="store_true", help="Publish narrated version")
    parser.add_argument("--upload-only", action="store_true", help="Only upload to R2")
    parser.add_argument("--register-only", action="store_true", help="Only register on dashboard")
    parser.add_argument("--list", action="store_true", help="List published on R2")
    parser.add_argument("--list-remote", action="store_true", help="List registered on dashboard")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list:
        packs = list_published()
        print(f"Published on R2 ({R2_BUCKET}/{R2_PREFIX}/):")
        for p in packs:
            print(f"  {p['slug']}")
        return

    if args.list_remote:
        videos = list_dashboard()
        print(f"Registered on studio.tantrafiles.xyz ({len(videos)} videos):")
        for v in videos:
            status = v.get("status", "?")
            print(f"  {v['id']:30s} {v.get('title',''):40s} [{status}]")
        return

    if not args.output_dir:
        print("Specify an output directory or use --list/--list-remote")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        sys.exit(1)

    # Determine slug
    slug = args.slug or slugify(output_dir.name)
    title = infer_title(output_dir)
    timeline_data, duration, scenes = load_timeline(output_dir)

    # Build per-shot listing for dashboard registration
    shots = []
    for i, s in enumerate(scenes, 1):
        shots.append({
            "id": f"scene_{i:03d}",
            "label": s.get("title", s.get("scene_id", f"Scene {i}")),
            "duration": s.get("duration", s.get("end_seconds", 0) - s.get("start_seconds", 0)),
            "status": "pending",
        })

    print(f"Publishing: {title}")
    print(f"  Slug: {slug}")
    print(f"  Duration: {duration:.1f}s ({duration/60:.1f}m)")
    print(f"  Scenes: {len(scenes)}")

    # Upload to R2
    if not args.register_only:
        print("  Uploading to R2...")
        uploaded = upload_pack(output_dir, slug, args.narrated)
        if not uploaded.get("mp4"):
            print("  No MP4 uploaded — aborting registration")
            return
        mp4_path = uploaded["mp4"]
    else:
        # Infer mp4 path from slug
        mp4_name = "life_crosses_barriers_narrated.mp4" if args.narrated else "life_crosses_barriers.mp4"
        mp4_path = f"{R2_PREFIX}/{slug}/{mp4_name}"

    # Register on dashboard
    if not args.upload_only:
        print("  Registering on studio dashboard...")
        result = register_on_dashboard(
            slug=slug,
            title=title,
            mp4_path=mp4_path,
            essay=args.essay,
            duration=duration,
            shots=shots,
        )

        if result:
            r2_path = result.get("mp4_path", "").replace("/api/r2/", "")
            print(f"\n  View at studio.tantrafiles.xyz (select '{slug}' in Final tab)")
            print(f"  Or direct video URL: http://localhost:8766/api/r2/{r2_path}")
            if "RENDER_COMPLETE" in os.environ:
                print(f"  Tunnel URL: https://studio.tantrafiles.xyz/api/r2/{r2_path}")
        else:
            print("\n  Upload succeeded but dashboard registration failed.")
            print(f"  Video available at R2: {mp4_path}")


if __name__ == "__main__":
    main()
