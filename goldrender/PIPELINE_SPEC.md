# Tantrāloka Production Pipeline — Full Spec

## Overview
End-to-end pipeline from raw essays to finished visual packs.

```
essays/                          Source essays
  └─ expansion-essays/*.md
       │
       ▼
goldrender/                      Pack generators
  ├─ *_platinum.py               (30 existing packs)
  └─ batch_render.py             Render orchestrator
       │
       ▼
goldrender/renders/              Rendered output
  ├─ output_*/*.mp4              Per-pack MP4
  ├─ output_*/scenes/*.mp4       Individual scene clips
  ├─ output_*/narration_timeline.json
  ├─ output_*/contact_sheet.jpg
  ├─ batch_manifest.json         Batch render report
  └─ render.log                  Continuous log
       │
       ▼
exports/                         Final distribution
  ├─ tantraloka_platinum_packs.zip
  ├─ pack_catalog.json
  └─ README.md
```

## Pipeline Stages

### Stage 0: Essay Inventory
**Input:** `expansion-essays/*.md`
**Output:** `essaylist.md` (ranked, with visual potential)

Already done — 62 essays in `expansion-essays/`, ranked in `essaylist.md`.

### Stage 1: Pack Generator
**Input:** Essay `.md` + README visual motifs
**Output:** `goldrender/*_platinum.py`

The pack generator is currently manual (write code per essay). Future state could use an LLM agent to generate the `_platinum.py` from the essay text and visual motif README.

**State:** 30 packs exist (Tiers 1-3). ~30 remaining from Tiers 3-4 + the ~60 R2 bucket essays.

### Stage 2: Batch Render
**Input:** `goldrender/*_platinum.py`
**Output:** `renders/output_*/` with MP4, timeline, contact sheet

The `batch_render.py` engine handles this. Two modes:
- `--preview` (4 stills per pack, ~10 min for 30 packs)
- `--full` (all frames → MP4, ~hours to days depending on pack size)

**Scaling notes:**
- 30 packs × avg 15 scenes × 6s × 10fps = 27000 frames total
- At ~0.3s per frame render = ~2.25 hours for full render
- Preview mode: ~10 minutes for all 30 packs

### Stage 3: Quality Control
**Input:** `renders/output_*/` with MP4 + contact sheet + timeline
**Output:** QC report per pack

Checks:
1. **Contact sheet review** — Do the 4 still frames tell a visual story?
2. **Timeline review** — Does the narration align with the visuals?
3. **Continuity check** — Does the continuity object persist across scenes?
4. **Still frame test** — Does each frame at u=0.72 work as a standalone image?
5. **No-narration test** — Would a viewer understand the concept without hearing the words?

### Stage 4: Export
**Input:** Approved renders from Stage 3
**Output:** Zipped distribution packs

```bash
python export_pipeline.py \
  --source goldrender/renders/ \
  --include *_platinum \
  --output exports/tantraloka_platinum_packs.zip
```

Each export includes:
- Full MP4
- Scene clips
- Narration timeline JSON
- Contact sheet
- Source `.py` file

### Stage 5: Publishing
**Input:** Exported ZIPs
**Output:** R2 bucket, GitHub release, blog integration

The factory MCP server (`blog/factory/cloudflare/src/mcp-server.py`) already handles R2 uploads. The pipeline can push exports to:
- `s3://sanskritree/renders/` (we already have credentials for this bucket)
- `s3://tantraloka-site/releases/` (if that bucket exists)

## Architecture Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   essays/    │────▶│  *_platinum.py   │────▶│ batch_render.py │
│  *.md        │     │  pack generator  │     │  --full/--prev  │
└──────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                                                       ▼
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  R2 / GitHub │◀────│  export_pipeline │◀────│  renders/       │
│  publishing  │     │  .py             │     │  MP4 + timeline  │
└──────────────┘     └──────────────────┘     └─────────────────┘
```

## Pipeline CLI

```bash
# Stage 1: Generate a new pack from essay
python generate_pack.py \
  --essay expansion-essays/05_god_looks_through_your_face.md \
  --visual-motif mirror-field \
  --output goldrender/god_looks_through_your_face_platinum.py

# Stage 2: Render all packs (preview)
python batch_render.py --preview --tier 1

# Stage 2: Full render of selected packs
python batch_render.py --full --pack fire_not_destroying

# Stage 3: QC review
python qc_review.py --renders renders/ --output qc_report.json

# Stage 4: Export
python export_pipeline.py \
  --include life_crosses_barriers,god_looks,fire_not_destroying \
  --format zip \
  --output exports/

# Stage 5: Publish to R2
python publish_pipeline.py \
  --source exports/ \
  --bucket sanskritree \
  --prefix renders/
```

## File Manifest Per Export

Each exported pack ZIP contains:
```
{pack_name}.zip
├── {pack_name}_animation.mp4      # Full film
├── scenes/
│   ├── scene_001.mp4
│   ├── scene_002.mp4
│   └── ...
├── narration_timeline.json        # Per-scene timing + narration
├── contact_sheet.jpg              # 4-column grid
├── render_pack.py                 # Source generator
├── AGENT_KNOWLEDGE_DOSSIER.md     # Creative brief
├── STYLE_EVOLUTION.md             # Visual differentiation notes
├── PRODUCTION_BLUEPRINT.md        # Technical specs
└── README.md                      # Usage instructions
```

## What We Have Now vs What's Needed

| Stage | Status | Notes |
|---|---|---|
| Stage 0: Essay inventory | ✅ Done | 62 essays in `expansion-essays/`, ranked in `essaylist.md` |
| Stage 1: Pack generator | ⏳ Partial | 30 packs done, ~30-60 more to write |
| Stage 2: Batch render | ✅ Done | `batch_render.py` working, tested with `--list` |
| Stage 3: QC | ❌ Not built | Need `qc_review.py` |
| Stage 4: Export | ❌ Not built | Need `export_pipeline.py` |
| Stage 5: Publishing | ❌ Not built | Need `publish_pipeline.py` (or use R2 via `aws s3 cp`) |

## Priorities

1. **Immediate:** Write remaining 30 packs (Tier 3-4 essays)
2. **Short-term:** Build `export_pipeline.py` to package renders
3. **Medium-term:** Run a full `--preview` batch render of all 30 packs
4. **Long-term:** QC review + publish to R2/GitHub
