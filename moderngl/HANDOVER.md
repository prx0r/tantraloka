# Agent Handover — Tantrāloka GPU Render Pipeline

## Current State (July 25 2026)

### What's Done

**GLSL Shaders (17 visual modes, life_crosses_barriers pack)**
All ported from PIL to GLSL fragment shaders. Each is a single `.glsl` file using Lygia SDF primitives. Structurally correct but **untested on GPU** — no GPU available on this server. The shaders compile syntactically but may have visual bugs when first rendered on a GPU box. Specifically:
- Domain-warped noise in `fieldBackground()` may look different from PIL version
- Additive glow colors may need intensity tuning
- All text rendering is commented out (no SDF font atlas yet)

**Audio Analysis**
- `renderer/audio_analysis.py` loads a WAV, runs librosa for per-frame volume/onset/centroid
- Loudness normalization (EBU R128 via pyloudnorm) added to ensure consistent `u_audioVolume` across voices
- Example: life_crosses narration (277.8s) → 6667 frames of features extracted

**Audio-Reactive Shaders**
- `classical_wall.glsl` wired with `u_audioVolume` and `u_audioBeat`
- Proton pulse radius = voice volume, sparks = onset strength, wall outline pulses with beat
- Other 16 shaders NOT yet wired — they accept the uniforms but don't use them

**Overnight PIL Render**
- 11 packs rendered to MP4 (~433MB total)
- These are draft-quality (8fps, Ken Burns zoompan, alpha-blend glow)
- Output at `/mnt/HC_Volume_106427611/goldrender/rendered_platinum/`

**Infrastructure**
- Lygia submodule at `moderngl/lygia/` (battle-tested SDF/noise/color shader library)
- Render harness at `moderngl/render_harness.py` (EGL context, HDR framebuffer, include resolver)
- Audio analysis at `moderngl/renderer/audio_analysis.py`

### What Needs Doing (Priority Order)

1. **Rent GPU box** (vast.ai, any NVIDIA card, ~$0.20-0.40/hr)
   - `NVIDIA_DRIVER_CAPABILITIES=all` required for EGL to see the GPU
   - Test EGL first: `python -c "import moderngl; ctx = moderngl.create_context(standalone=True, backend='egl'); print(ctx.info['GL_RENDERER'])"`
   - If it prints "llvmpipe" instead of GPU name, fix EGL ICD loading first

2. **Test shaders** — render classical_wall at u=0.72, compare side-by-side with PIL output at same u
   - If composition/color matches → port remaining 16 shaders' audio-reactive uniforms
   - If not → debug per-shader (likely noise or glow intensity values)

3. **Port remaining packs** — each of the 11 rendered packs has unique visual modes that need `.glsl` files:
   - `god_looks_through_your_face` (49 scenes, 14 visuals — mirror, face, theophanic)
   - `fire_not_destroying` (45 scenes, 13 visuals — alchemical, crucible, nigredo)
   - `voice_inside_chest` (40 scenes — enteric brain, serotonin)
   - Plus 8 more medium packs

4. **Wire audio-up the 16 remaining shaders** — each needs:
   - `uniform float u_audioVolume;`
   - `uniform float u_audioBeat;`
   - Pulse/grow/glow modulation from audio (sample pattern from classical_wall)

5. **Add film grain + chromatic aberration** post-pass to render harness

6. **SDF font atlas** for text rendering (msdfgen or similar)

### Voice/TTS Pipeline (for tomorrow)

**Target voice profile** for Tantrāloka content:
- Deep, warm, authoritative but not pompous
- Neutral-to-British accent handles Sanskrit terms gracefully
- Think: David Attenborough / Stephen Fry gravitas

**Edge TTS voices worth testing:**
| Voice | Vibe | Best For |
|-------|------|----------|
| en-GB-RyanNeural | Warm, articulate, technical | Current default — good for scientific content |
| en-GB-SoniaNeural | Mature, authoritative, warm | Philosophical passages |
| en-US-DavisNeural | Deep, calm, authoritative | Quantum mechanics, biology |
| en-GB-AdrianNeural | Youthful, articulate | Accessible explanations |
| en-GB-AlfieNeural | Warm, distinctive | Narration with character |
| en-IE-EmilyNeural | Lilt, musical, warm | Poetic/philosophical sections |

**For a truly bespoke voice (Qwen3-TTS Voice Clone):**
- Record 5-15s of a speaker you like
- Provide exact transcript of that clip
- Pad reference with 0.5s silence: `ffmpeg -i ref.wav -af "apad=pad_dur=0.5" ref_padded.wav`
- Save the WAV + transcript → that pair IS the voice profile (no model to export)
- `pip install git+https://github.com/QwenLM/Qwen3-TTS.git` on GPU box
- Call directly from Python (no server needed for batch):
```python
model.generate_voice_clone(
    text="<essay text>",
    ref_audio="assets/voice/narrator_ref.wav",
    ref_text=open("assets/voice/narrator_ref.txt").read().strip(),
)
```

**Online test (no install):** https://huggingface.co/spaces/Qwen/Qwen3-TTS-Clone-Demo

### Are The GLSL Shaders The Best They Can Be?

**No**, but they're structurally correct. Here's what's still missing:

| Feature | Status | Impact |
|---------|--------|--------|
| Additive bloom (HDR multi-pass) | Framework exists in render_harness, not wired per-shader | High — makes glow look filmic |
| Domain-warped fbm | Implemented but untuned | Medium — noise may look different from PIL |
| Cosine palettes | In primitives.glsl, not used by any shader | Medium — smooth color animation |
| ACES tonemap | In includes, not wired in render pipeline | Medium — prevents bloom clipping |
| Text rendering (SDF font atlas) | Not implemented | Low for visuals, high for readability |
| Audio-reactive uniforms | Only in classical_wall | High — makes every scene breathe |
| Chromatic aberration + grain | Not implemented | Low — final polish |
| 2x SSAA (supersampling) | In engine.py but untested | Medium — anti-aliasing |

The shaders will look **significantly better than PIL** even without these (additive glow alone is the big upgrade), but full production quality needs the bloom pipeline wired and cosine palettes activated.

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     GPU BOX (vast.ai)                       │
│                                                             │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐   │
│  │ Qwen3-TTS │──▶│ audio_      │──▶│ render_harness.py │   │
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

### Files to Know

| File | Purpose |
|------|---------|
| `moderngl/render_harness.py` | Main entry point. Discovers packs, renders with GLSL, assembles MP4. |
| `moderngl/shaders/` | 17 `.glsl` scene shaders |
| `moderngl/shaders/include/primitives.glsl` | Shared functions wrapping Lygia |
| `moderngl/renderer/audio_analysis.py` | Librosa per-frame feature extraction |
| `moderngl/renderer/engine.py` | EGL context, HDR framebuffer, bloom (skeleton) |
| `moderngl/lygia/` | Git submodule — SDF/noise/color library |
| `goldrender/render_all_platinum.py` | PIL delivery-mode renderer (CPU, overnight runs) |
| `goldrender/publish_pipeline.py` | R2 upload + dashboard registration |
| `goldrender/*_platinum.py` | Pack source files (scene definitions + PIL render functions) |
