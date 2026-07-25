# Port Notes — PIL → ModernGL/GLSL

## Status: All 17 visual modes of life_crosses_barriers ported

### What was ported

| # | Mode | Shader File | Key Features |
|---|------|-------------|-------------|
| 1 | classical_wall | `classical_wall.glsl` | SDF rounded rect wall, proton circle with glow, impact sparks |
| 2 | tunnelling | `tunnelling.glsl` | Barrier SDF, wavefunction with exponential decay, detection event |
| 3 | width | `width.glsl` | Animated barrier width, incident + decay wave, transmission glow |
| 4 | mass | `mass.glsl` | 4 particle rows, barrier, wave approach + transmission per mass |
| 5 | landscape | `landscape.glsl` | Energy landscape gaussian, molecular state roller, enzyme arcs |
| 6 | enzyme | `enzyme.glsl` | Breathing protein lobes (SDF circles), donor/acceptor, quantum wave |
| 7 | isotope | `isotope.glsl` | H vs D rows, barrier, transmission probability difference |
| 8 | evidence | `evidence.glsl` | 5 radiating evidence terms from central hub, connecting glow lines |
| 9 | evolution | `evolution.glsl` | 7 generations of arc-pairs with narrowing gap and arrows |
| 10 | form | `form.glsl` | Triangle edges (partial polylines), vertex glow dots |
| 11 | rates | `rates.glsl` | 8 staggered rate bars with color gradient (crimson→green) |
| 12 | gate | `gate.glsl` | Membrane dots, water chain nodes, proton relay path |
| 13 | noise | `noise.glsl` | Scattering points converging to sine wave via domain warp |
| 14 | architecture | `architecture.glsl` | 4 circles emerging (bird, cell, embryo, enzyme) |
| 15 | warning | `warning.glsl` | Two panels: exact mechanism box, metaphorical overreach fade |
| 16 | psychology | `psychology.glsl` | Person figure (head circle + body line) approaching wall |
| 17 | final | `final.glsl` | Barrier, enzyme chamber arches, gold filament crossing, green emergence |

### Shared infrastructure

| File | Contents |
|------|----------|
| `shaders/include/primitives.glsl` | SDF primitives (iq), easing, Ashima noise + fbm, cosine palette, glow helpers, fieldBackground |
| `shaders/include/bloom.glsl` | Bright-pass extraction, 7-tap separable gaussian blur |
| `shaders/include/aces.glsl` | ACES filmic tonemap (fitted curve) |
| `shaders/include/srgb.glsl` | Linear ↔ sRGB conversion |
| `shaders/include/easing.glsl` | ease, smoothstep, pulse, lerp |
| `render_harness.py` | Headless EGL context, HDR framebuffer, shader loading, frame loop, ffmpeg assembly |

### Visual upgrades over PIL

| Aspect | PIL (old) | GLSL (new) |
|--------|-----------|------------|
| Glow | Alpha blend (`alpha_composite` + GaussianBlur) | Additive (brightness accumulates, HDR) |
| Color space | sRGB 8-bit | Linear fp32, ACES tonemap on output |
| Anti-aliasing | None (hard PIL edges) | SDF smoothstep edges |
| Background | numpy Perlin noise → PIL composite | GPU simplex noise + domain warped fbm |
| Resolution independence | Hardcoded pixel values | All positions as uv fractions |
| Bloom | Manual multi-image blur | GPU multi-pass (bright→blur→add) |
| Upgrades | — | Cosine palette, chromatic aberration, film grain |

### What's commented out
- Text rendering (`seal()` / `footer()`) — SDF font atlas not yet generated
- Per-scene parameter uniforms (`p.mode` branching) — simplified to single-path per shader

### What's NOT ported yet
- The other ~70 packs (different visual modes, but same primitives)
- Text SDF atlas generation
- Cosine palette integration (ready in primitives.glsl, not wired per-shader)

### Key decision: Lygia replaces custom primitives
All hand-written SDF, noise, easing, and color functions have been replaced with
Lygia (https://github.com/patriciogonzalezvivo/lygia) — a 3.4k-star battle-tested
multi-language shader library. Added as a git submodule at moderngl/lygia/.

The file `shaders/include/primitives.glsl` now wraps Lygia functions under our
naming conventions and adds pipeline-specific helpers (fieldBackground, glowSoft).

### Next steps
1. ✅ Test on GPU box: `python render_harness.py --pack life_crosses_barriers --preview`
2. ⬜ Generate SDF font atlas for text rendering
3. ⬜ Wire cosine palette uniforms per pack
4. ⬜ Port remaining pack visual modes (same 7 primitives, different compositions)
5. ⬜ Add chromatic aberration + film grain post-pass
6. ⬜ Benchmark: 4K @ 24fps on RTX 3060+
