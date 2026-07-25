# Batch Render Engine — Design Spec

## Purpose
Render all platinum packs in sequence with resume, logging, and progress tracking.

## Requirements
- Discover all `*_platinum.py` renderers in `goldrender/`
- Run each with `--preview` (4 stills) or full render
- Optionally limit render to N packs, specific packs by name, or tier
- Track rendered/remaining/time per pack
- Resume on interruption (each pack is already resume-safe)
- Log per-pack to `renders/render.log`
- Generate a batch manifest after completion

## Design

```
┌─────────────────────────────────────────────┐
│                  batch_render.py             │
├─────────────────────────────────────────────┤
│  CLI:                                        │
│    --list        List all discoverable packs │
│    --preview     Render 4 stills per pack    │
│    --no-render   Dry-run (validate only)     │
│    --pack "name"  Single pack                │
│    --tier N       Render specific tier       │
│    --until N      Render first N packs       │
│    --parallel M   Run M workers (future)     │
│    --output DIR   Output directory root      │
│    --fps FPS      Override frame rate        │
│    --width/--height  Override resolution     │
├─────────────────────────────────────────────┤
│  Flow:                                       │
│  1. Discover all *_platinum.py               │
│  2. Filter by --pack / --tier / --until      │
│  3. For each pack:                           │
│     a. Run subprocess with --preview/full    │
│     b. Log start, progress, end, status      │
│     c. Write per-pack render record          │
│  4. Generate batch report:                   │
│     - total packs, rendered, failed          │
│     - total runtime                          │
│     - disk usage                             │
│     - per-pack breakdown                     │
└─────────────────────────────────────────────┘
```

## File Structure

```
goldrender/
├── batch_render.py            ← The engine
├── renders/                   ← All output lives here
│   ├── render.log             ← Continuous log
│   ├── batch_manifest.json    ← Batch completion report
│   └── *_platinum/            ← Per-pack output dirs
├── *_platinum.py              ← Pack renderers
└── *_pack.py                  ← Legacy (goldrender) packs
```

## Batch Manifest Format

```json
{
  "batch_id": "2026-07-25-060000",
  "started": "2026-07-25T06:00:00Z",
  "completed": "2026-07-25T08:30:00Z",
  "total_elapsed_seconds": 9000,
  "config": {"fps": 10, "width": 1280, "height": 720, "mode": "preview"},
  "packs_total": 30,
  "packs_rendered": 30,
  "packs_failed": 0,
  "total_disk_mb": 0,
  "packs": [
    {
      "name": "life_crosses_barriers_platinum",
      "status": "done",
      "started": "2026-07-25T06:00:00Z",
      "completed": "2026-07-25T06:05:00Z",
      "elapsed_seconds": 300,
      "error": null,
      "output_dir": "renders/life_crosses_barriers_platinum/",
      "mp4": "renders/life_crosses_barriers_platinum/life_crosses_barriers.mp4",
      "disk_mb": 45.2
    }
  ]
}
```

## Resume Safety

Each pack is individually resume-safe (skips existing frames and MP4s). The batch engine can be killed and re-run; completed packs are detected by the presence of `output_*/life_crosses_barriers.mp4` (or equivalent) and skipped.

The render engine itself should:
1. Write a `.lock` file per pack when starting
2. Remove `.lock` on completion
3. Skip packs with `.lock` from a previous interrupted run (require `--force` to re-run)

## Resource Management

- Check available disk before starting each pack (skip if < 1GB free)
- Log disk usage after each pack
- Suggest --preview mode for large packs (>20 scenes)
- Warn if estimated render time > 30 minutes

## Implementation Plan

Write `batch_render.py` as a single file (150-200 lines) that:
1. Scans `goldrender/` for `*_platinum.py`
2. Imports `json`, `subprocess`, `time`, `pathlib`, `argparse`
3. Runs each pack via `subprocess.Popen` with piped output
4. Parses stdout for progress lines
5. Writes manifest at end

No worker pool initially — sequential execution is fine. Parallel execution can be added later via multiprocessing.
