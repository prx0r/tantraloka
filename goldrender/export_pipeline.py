#!/usr/bin/env python3
"""
Tantrāloka Export Pipeline
Package completed renders into distributable ZIPs with catalog.

Usage:
    python export_pipeline.py                              # Export all completed renders
    python export_pipeline.py --tier 1                     # Export Tier 1 only
    python export_pipeline.py --pack fire_not_destroying   # Export specific pack
    python export_pipeline.py --since 2026-07-25           # Export renders after date
    python export_pipeline.py --output /tmp/exports        # Custom output dir
    python export_pipeline.py --no-zip                     # Copy files instead of zipping
    python export_pipeline.py --catalog-only                # Only generate the catalog
"""
import argparse, json, os, shutil, zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS_DIR = ROOT / "exports"
RENDERS_DIR = ROOT / "renders"


def discover_renders(args) -> list[dict]:
    """Find all completed render output directories."""
    renders = []

    # Packs produce output_{slug} dirs
    for outdir in ROOT.glob("output_*"):
        if not outdir.is_dir():
            continue

        mp4s = list(outdir.glob("*.mp4"))
        if not mp4s:
            continue  # No completed render

        # Infer the pack name
        stem = outdir.name.replace("output_", "")
        pack_file = ROOT / f"{stem}_platinum.py"
        if not pack_file.exists():
            pack_file = ROOT / f"{stem}_pack.py"
        if not pack_file.exists():
            pack_file = None

        # Get scene clips
        scenes = sorted((outdir / "scenes").glob("*.mp4")) if (outdir / "scenes").exists() else []

        # Get metadata files
        timeline = outdir / "narration_timeline.json"
        contact = outdir / "contact_sheet.jpg"
        timeline_data = None
        if timeline.exists():
            try:
                timeline_data = json.loads(timeline.read_text())
            except:
                pass

        renders.append({
            "name": stem,
            "output_dir": str(outdir),
            "pack_file": str(pack_file) if pack_file else None,
            "mp4": str(mp4s[0]),
            "scenes": [str(s) for s in scenes],
            "timeline": str(timeline) if timeline.exists() else None,
            "timeline_data": timeline_data,
            "contact_sheet": str(contact) if contact.exists() else None,
            "scene_count": len(scenes),
            "duration": timeline_data.get("runtime_seconds", 0) if timeline_data else 0,
        })

    # Sort by name
    renders.sort(key=lambda r: r["name"])

    # Apply filters
    if args.pack:
        renders = [r for r in renders if args.pack.lower() in r["name"].lower()]
    if args.tier:
        # Estimate tier from position in list
        all_sorted = sorted([r["name"] for r in renders])
        tier_map = {}
        for i, name in enumerate(all_sorted):
            tier = (i // 10) + 1
            tier_map[name] = tier
        renders = [r for r in renders if tier_map.get(r["name"], 99) == args.tier]

    return renders


def export_render(render: dict, output_dir: Path, no_zip: bool = False) -> dict:
    """Package a single render into a ZIP file or directory."""
    name = render["name"]
    export_path = output_dir / name

    if no_zip:
        export_path.mkdir(parents=True, exist_ok=True)
    else:
        export_path = output_dir / f"{name}_pack.zip"

    # Track what we export
    files_written = []

    def add_file(src: str | Path, dest_name: str | None = None):
        src_path = Path(src)
        if not src_path.exists():
            return
        if not src_path.is_file():
            return
        dst = dest_name or src_path.name
        if no_zip:
            shutil.copy2(str(src_path), str(export_path / dst))
        else:
            with zipfile.ZipFile(export_path, "a", zipfile.ZIP_DEFLATED) as zf:
                zf.write(str(src_path), dst)
        files_written.append(dst)
        # Also write to the log
        return dst

    # Main MP4
    add_file(render["mp4"], f"{name}_animation.mp4")

    # Scene clips
    for scene_path in render["scenes"]:
        add_file(scene_path)

    # Timeline
    if render["timeline"]:
        add_file(render["timeline"])

    # Contact sheet
    if render["contact_sheet"]:
        add_file(render["contact_sheet"])

    # Source pack file
    if render["pack_file"]:
        add_file(render["pack_file"], f"{name}_pack.py")

    # Dossier — look in output dir for metadata files
    outdir = Path(render["output_dir"])
    for meta_file in ["AGENT_KNOWLEDGE_DOSSIER.md", "STYLE_EVOLUTION.md", "validation.json", "README.md"]:
        mf = outdir / meta_file
        if mf.exists():
            add_file(mf)

    # Also look in the goldrender root for the dossiers (some packs write them at root level)
    for meta_file in ["AGENT_KNOWLEDGE_DOSSIER.md", "STYLE_EVOLUTION.md"]:
        mf = ROOT / meta_file
        if mf.exists() and meta_file not in files_written:
            # Only add if it matches this pack — heuristic: check content for pack name
            if name.replace("_", " ") in mf.read_text():
                add_file(mf)

    result = {
        "name": name,
        "export_path": str(export_path),
        "files": files_written,
        "size_mb": round(export_path.stat().st_size / (1024 * 1024), 1) if export_path.exists() else 0,
    }

    if no_zip:
        result["size_mb"] = round(
            sum(f.stat().st_size for f in export_path.rglob("*") if f.is_file()) / (1024 * 1024), 1
        )

    return result


def generate_catalog(exported: list[dict], output_dir: Path) -> dict:
    """Generate a master catalog of all exported packs."""
    catalog = {
        "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_packs": len(exported),
        "total_duration_seconds": sum(
            r.get("duration", 0) for r in exported
        ),
        "packs": [],
    }

    for export in exported:
        catalog["packs"].append({
            "name": export["name"],
            "scenes": export.get("scene_count", 0),
            "duration_seconds": export.get("duration", 0),
            "size_mb": export.get("size_mb", 0),
            "path": export.get("export_path", ""),
            "files": export.get("files", []),
        })

    catalog_path = output_dir / "pack_catalog.json"
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"  Catalog: {catalog_path}")
    return catalog


def parse_args():
    parser = argparse.ArgumentParser(description="Tantrāloka Export Pipeline")
    parser.add_argument("--pack", type=str, help="Export specific pack (substring match)")
    parser.add_argument("--tier", type=int, help="Export specific tier")
    parser.add_argument("--since", type=str, help="Export renders completed after date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default=str(EXPORTS_DIR), help="Output directory")
    parser.add_argument("--no-zip", action="store_true", help="Copy files instead of zipping")
    parser.add_argument("--catalog-only", action="store_true", help="Only generate the catalog")
    parser.add_argument("--list", action="store_true", help="List discoverable renders and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    renders = discover_renders(args)

    if args.list:
        print(f"{'Pack':40s} {'Scenes':8s} {'Duration':10s} {'Size':8s}")
        print("-" * 70)
        for r in renders:
            size_text = "N/A"
            mp4 = Path(r["mp4"])
            if mp4.exists():
                size_text = f"{mp4.stat().st_size / (1024*1024):.1f} MB"
            dur = r.get("duration", 0)
            dur_text = f"{dur:.0f}s" if dur else "?"
            print(f"{r['name']:40s} {r['scene_count']:<8d} {dur_text:10s} {size_text:8s}")
        print(f"\nTotal: {len(renders)} completed renders")
        return

    if args.catalog_only:
        dummy_exports = [{"name": r["name"], "scene_count": r["scene_count"],
                          "duration": r.get("duration", 0), "size_mb": 0,
                          "export_path": "", "files": []} for r in renders]
        generate_catalog(dummy_exports, output_dir)
        return

    if not renders:
        print("No completed renders found. Run batch_render.py --preview or --full first.")
        return

    print(f"Exporting {len(renders)} packs to {output_dir}")
    print(f"Mode: {'directory copy' if args.no_zip else 'ZIP'}")

    exported = []
    for i, render in enumerate(renders):
        print(f"  [{i+1}/{len(renders)}] {render['name']}...", end=" ", flush=True)
        result = export_render(render, output_dir, args.no_zip)
        exported.append(result)
        print(f"({result['size_mb']:.1f} MB, {len(result['files'])} files)")

    # Generate catalog
    catalog = generate_catalog(exported, output_dir)

    # Summary
    total_size = sum(e.get("size_mb", 0) for e in exported)
    total_dur = catalog["total_duration_seconds"]
    print(f"\n{'='*50}")
    print(f"  Exported: {len(exported)} packs")
    print(f"  Total size: {total_size:.1f} MB")
    print(f"  Total runtime: {total_dur:.0f}s ({total_dur/60:.1f}m)")
    print(f"  Output: {output_dir}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
