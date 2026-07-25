# Agent Onboarding — Tantrāloka GPU Render Pipeline

## Quick Start

```bash
git clone --recurse-submodules https://github.com/prx0r/tantraloka.git
cd tantraloka/moderngl
pip install moderngl numpy pillow librosa scipy pyloudnorm
```

## What This Project Does

71 "platinum packs" — each is a Python file defining 4–164 scenes of procedural animation. Each scene has:
- `visual`: a named visual mode (e.g. "tunnelling", "classical_wall", "enzyme")
- `narration`: spoken text for the scene
- `duration`: length in seconds
- `params`: optional mode parameters

The original renderer uses PIL (CPU, slow, flat-looking). We're migrating to **GLSL fragment shaders on GPU** via ModernGL — same scene data, same composition, but rendered in real-time with HDR bloom, additive glow, ACES tonemap, and audio reactivity.

## Stack Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GPU BOX (vast.ai)                       │
│                                                             │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐   │
│  │ Qwen3-TTS │──▶│ audio_       │──▶│ render_harness.py │   │
│  │ (voice    │   │ analysis.py │   │ (EGL + GLSL)      │   │
│  │ clone)    │   │ (librosa)   │   │                    │   │
│  └──────────┘   └──────────────┘   │  shaders/*.glsl    │   │
│                                    │  lygia/ (submodule)│   │
│  ┌──────────┐                      │  audio_features    │   │
│  │ essay.md │─────────────────────▶│  per-frame uniforms│   │
│  └──────────┘                      └────────┬──────────┘   │
│                                            │              │
│                                            ▼              │
│                                     ┌──────────┐          │
│                                     │ ffmpeg    │          │
│                                     │ → MP4     │          │
│                                     └──────────┘          │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │ publish_pipeline │──▶ studio.tantrafiles.xyz
                     │ (R2 upload +     │
                     │  dashboard reg)  │
                     └──────────────────┘
```

## Key Files

| File | What it does |
|------|-------------|
| `moderngl/render_harness.py` | **Main entry point.** Discovers packs, renders with GLSL, assembles MP4. |
| `moderngl/shaders/*.glsl` | **17 scene shaders.** One per visual mode. Fragment shaders with `u`, `t`, `u_audioVolume`, `u_audioBeat`. |
| `moderngl/shaders/include/primitives.glsl` | Shared helpers wrapping Lygia. `fieldBackground()`, `glowSoft()`, `scenePalette()`, `audioMod()`. |
| `moderngl/shaders/composite.glsl` | Final pass: bloom + ACES tonemap + chromatic aberration + film grain. |
| `moderngl/shaders/include/` | Lygia submodule + ACES, easing, bloom includes. |
| `moderngl/lygia/` | Git submodule — 3.4k★ shader library, all SDF/noise/easing/color functions. |
| `moderngl/renderer/audio_analysis.py` | librosa per-frame feature extraction. Outputs `u_audioVolume`, `u_audioBeat`, `u_audioOnset`. |
| `moderngl/renderer/text_overlay.py` | Post-render text compositing for sparse labels. |
| `moderngl/renderer/engine.py` | EGL context, HDR framebuffer, bloom FBOs. Skeleton — more work needed. |
| `moderngl/PORT.md` | Full migration spec: SDF primitives, bloom pipeline, audio integration. |
| `moderngl/portnotes.md` | Running notes on architecture decisions and what's been done. |
| `moderngl/HANDOVER.md` | Previous session handover. |
| `moderngl/SCENE_MAPPING.md` | Maps every GLSL shader to its PIL original and scene titles. |
| `goldrender/render_all_platinum.py` | **PIL delivery-mode renderer.** CPU, 8fps, Ken Burns zoompan. For overnight draft batches. |
| `goldrender/publish_pipeline.py` | Uploads rendered MP4s to R2 + registers on studio.tantrafiles.xyz dashboard. |
| `goldrender/*_platinum.py` | Pack source files — scene definitions + PIL render functions. |

## GLSL Uniform Contract

Every scene shader receives:

| Uniform | Type | Range | Description |
|---------|------|-------|-------------|
| `u` | float | 0→1 | Per-scene animation progress |
| `t` | float | seconds | Elapsed time within scene |
| `iResolution` | vec2 | pixels | Framebuffer dimensions |
| `u_audioVolume` | float | 0→1 | RMS energy envelope (smoothed) |
| `u_audioBeat` | float | 0→1 | Onset strength / beat likelihood |

From `primitives.glsl`:
- `fieldBackground(uv, iResolution, t, baseColor)` — domain-warped noise + vignette
- `glowSoft(p, center, radius)` — additive gaussian glow
- `glowLine(p, a, b, width)` — additive line glow
- `scenePalette(t, a, b, c, d)` — cosine color palette (iq)
- `sdCircle`, `sdSegment`, `sdRoundedBox`, `sdArc`, `sdEllipse` — SDF primitives from Lygia
- `ease(t)` → `easeInOutCubic`, `ease_out(t)` → `easeOutCubic`
- `fill(d)`, `stroke(d, w)` — SDF fill/stroke helpers

## Priority To-Do

### 1. Rent GPU box (vast.ai)
- NVIDIA card, RTX 3060+ ($0.20-0.40/hr)
- **Set `NVIDIA_DRIVER_CAPABILITIES=all`** in environment
- EGL sanity check first:
  ```bash
  python -c "import moderngl; ctx = moderngl.create_context(standalone=True, backend='egl'); print(ctx.info['GL_RENDERER'])"
  ```
  If it prints "llvmpipe" instead of GPU name, fix EGL ICD loading first (common vast.ai issue — see PORT.md for fixes).

### 2. Test one shader end-to-end
```bash
python render_harness.py --pack life_crosses_barriers --preview --width 1280 --height 720
```
Compare output side-by-side with PIL preview at same `u` values. If composition/color doesn't match, tune per-shader (noise intensity, glow brightness, palette phases).

### 3. Debug render pipeline
The bloom pipeline skeleton exists but isn't fully wired on GPU. The multi-pass bloom (bright extract → downsample → blur → upsample → add) needs framebuffer ping-pong implemented in `engine.py`. Currently falls back to numpy bloom which is slow.

### 4. Port remaining packs to GLSL
Each of the 11 rendered packs has unique visual modes. Priority:
1. `god_looks_through_your_face` (49 scenes, 14 visuals — mirror, face, theophanic)
2. `fire_not_destroying` (45 scenes, 13 visuals — alchemical, crucible, nigredo)
3. `voice_inside_chest` (40 scenes — enteric brain, serotonin)
4. Remaining 8 medium packs

Pattern for porting: read the PIL visual function, identify the 7 primitives used, rewrite as SDF + additive glow in GLSL.

### 5. Wire full bloom + ACES tonemap
`composite.glsl` exists but isn't wired in the render loop. The pipeline should be:
```
scene shader → HDR framebuffer → bright pass → gaussian blur (horizontal + vertical) →
upsample → add back to HDR → ACES tonemap → chromatic aberration → film grain → sRGB output
```

### 6. Audio analysis integration
`audio_analysis.py` works (tested on life_crosses narration — 277.8s → 6667 frames). It's not wired into the render loop yet. The render harness needs to:
1. Check for `narration_full.wav` in the output dir
2. Run `audio_analysis.py` on it (or load cached features)
3. Pass per-frame values as uniforms

## Voice Pipeline (Qwen3-TTS)

### Setup on GPU box
```bash
pip install git+https://github.com/QwenLM/Qwen3-TTS.git
```

### Voice profile (no training needed)
1. Record 5-15s of a speaker you like
2. Provide exact transcript of that clip
3. Pad reference with 0.5s silence: `ffmpeg -i ref.wav -af "apad=pad_dur=0.5" ref_padded.wav`
4. That WAV + transcript IS the voice profile — no model to export
5. Use at render time:
```python
from qwen_tts import Qwen3TTSModel
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0", dtype=torch.bfloat16,
)
wavs, sr = model.generate_voice_clone(
    text="<scene narration text>",
    ref_audio="assets/voice/narrator_ref.wav",
    ref_text=open("assets/voice/narrator_ref.txt").read().strip(),
)
```

### Online test (no install)
https://huggingface.co/spaces/Qwen/Qwen3-TTS-Clone-Demo

### Important
- Qwen3-TTS and ModernGL both want VRAM. Run TTS first, then **unload the model** before starting the render: `del model; torch.cuda.empty_cache()`
- Otherwise you'll get OOM errors that look like shader bugs but aren't.

## GLSL Reference Library

The entire SDF/noise/easing/color library comes from Lygia (submodule at `moderngl/lygia/`). Before writing any custom GLSL math, check if Lygia has it:

| Category | Key Lygia files |
|----------|----------------|
| SDF | `lygia/sdf/circle.glsl`, `segment.glsl`, `boxRounded.glsl`, `arc.glsl`, `ellipse.glsl` |
| Draw | `lygia/draw/stroke.glsl`, `fill.glsl` |
| Noise | `lygia/generative/snoise.glsl`, `fbm.glsl` |
| Easing | `lygia/animation/easing.glsl` |
| Color | `lygia/color/palette/cosine.glsl`, `lygia/color/tonemap/aces.glsl` |
| Filter | `lygia/filter/gaussianBlur.glsl` |

Additional GLSL references:
- iq's 2D distance functions: https://iquilezles.org/articles/distfunctions2d/
- Book of Shaders: https://thebookofshaders.com/
- Generative Gestaltung (design reference): https://generative-gestaltung.de/2/

## Common Pitfalls

1. **EGL fails on vast.ai** — Always `NVIDIA_DRIVER_CAPABILITIES=all`. If it still fails, install `libegl1-mesa-dev` and check ICD loaders.
2. **OOM when running TTS + render** — Unload TTS model before starting render. They share VRAM.
3. **"llvmpipe" instead of GPU** — The EGL ICD path is wrong. Fix: `export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json`
4. **Text is missing** — Text labels are composited by `text_overlay.py` after GPU render. If labels don't appear, check `scene_labels` dict in `render_harness.py`.
5. **Bloom looks wrong** — The bloom pipeline is numpy fallback, not GPU. Full GPU multi-pass bloom isn't wired yet.
6. **Colors don't match PIL** — Fixed semantic colors (GOLD=CYAN semantic) are replaced by dynamic cosine palettes. This is intentional — the GLSL versions are more abstract and atmospheric. If you need exact color matching, revert to fixed palettes.
7. **Audio features don't load** — `audio_analysis.py` requires `librosa` and `pyloudnorm`. Install with `pip install librosa scipy pyloudnorm`.

## Session Norms

- Each visual mode is a single `.glsl` file. All 17 pack modes from `life_crosses_barriers` are done. New packs need new shaders.
- All shaders receive the 5 standard uniforms. Don't add custom uniforms per-shader — use the existing contract.
- The render pipeline is `render_harness.py`. Don't modify the shaders to work around pipeline bugs — fix the pipeline.
- Audio is always pre-analyzed (never real-time). Per-frame features are looked up by frame index.
- Text is always post-composited (never in-shader). Glyph rendering in GLSL is an anti-pattern for this project.
- Cosine palettes are preferred over fixed colors. Each pack defines its own palette constants.
- Additive glow always, never alpha blend. This is the single most important visual rule.
