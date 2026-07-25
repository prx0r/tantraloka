# Agent Task: Port PIL Scene Renderer to moderngl/GLSL

## Context

We have a video-generation pipeline of 71 "packs," each a sequence of scenes.
Each scene is a Python function with signature `vis_name(im, u, t, p)` where:
- `im` — a PIL RGBA Image being drawn into
- `u` — animation progress, 0.0 to 1.0, for this scene
- `t` — global timeline position
- `p` — a params/context object (palette, seed, etc.)

Scenes are built from exactly 7 primitives:
1. `draw.line()`
2. `draw.ellipse()`
3. `draw.arc()`
4. `draw.rounded_rectangle()`
5. `draw.polygon()`
6. `draw.text()`
7. `alpha_composite()` + `GaussianBlur()` — used for all glow/soft-light effects

Supporting helpers exist for glow (`glow_circle`, `glow_line`), easing (`ease`,
`smoothstep`, `lerp`), color mixing (`mix`), a noise-textured background
(`field()`), text sealing (`seal()`), and scattered point layouts
(`event_field()`). Full reference source is attached/pasted below this prompt.

The current renderer is CPU-bound, uses alpha-blended (not additive) glow, has
no anti-aliasing, and looks flat/cheap compared to what GPU shaders can do.
We are moving the render backend to GLSL fragment shaders run via `moderngl`,
executed headless on a rented GPU box, rendering a PNG sequence per scene that
gets assembled with ffmpeg exactly as today.

## Your job

Port this pipeline to moderngl + GLSL **without changing the creative/authored
content** — same compositions, same color palettes, same scene beats and
timing. This is a rendering backend swap, not a redesign. If a design choice
is ambiguous, default to matching the existing PIL output as closely as
possible, then flag it for review rather than improvising a new look.

## Required architecture

1. **Headless render harness first.** Before porting any scene, build:
   - A moderngl context created headless (EGL, no window) — verify it runs
     on the target GPU box, not just locally.
   - A framebuffer object at the target resolution + supersampling factor
     (render at 2x, downsample with a box filter or built-in mipmapping when
     copying out — this is our anti-aliasing strategy, since GLSL primitives
     have hard edges by default).
   - A per-scene render loop: for each frame, set uniforms (`u_time`, `u_seed`,
     `u_resolution`, palette colors as `vec3` uniforms), render, read pixels,
     write PNG. Confirm this loop works end-to-end with a trivial shader
     (solid color fade) before touching real scene content.
   - Confirm output PNG sequence feeds into our existing ffmpeg assembly step
     unchanged.

2. **Primitive → GLSL mapping.** Implement each of the 7 primitives as
   reusable GLSL functions (a shared "primitives.glsl" include, not
   copy-pasted per scene):
   - Lines → signed-distance-to-segment function, stroked with smoothstep
     for anti-aliased edges (see "Book of Shaders" / iquilez 2D SDF
     functions for the standard formula — don't invent this from scratch,
     use the canonical `sdSegment` implementation).
   - Ellipses/circles → SDF ellipse function.
   - Arcs → SDF arc function (iq's `sdArc`).
   - Rounded rectangles → SDF rounded-box function (iq's `sdRoundedBox`).
   - Polygons → either SDF polygon (fixed vertex count, fine for our
     symbol shapes) or rasterize as a triangle-fan mesh if vertex count
     varies per call — pick whichever is simpler given actual polygon use
     in the source; flag which one you used and why.
   - Text → render text to a signed-distance-field atlas up front (see
     `moderngl`-compatible SDF font tooling, or pre-bake an MSDF atlas with
     `msdfgen`), then sample it in-shader. Do not attempt to rasterize text
     glyphs as raw geometry.
   - `alpha_composite` + `GaussianBlur` (our glow) → replace with **additive**
     compositing, not blended: render glow sources to an offscreen HDR
     buffer, apply a real two-pass Gaussian blur (horizontal then vertical
     shader pass, not a naive O(n²) blur), then add the result on top of
     the base image in linear color space (`result = base + bloom * intensity`,
     clamped/tonemapped on output). This additive step is the single biggest
     visual upgrade over the current PIL version — do not skip it or
     approximate it with blended compositing.

3. **Noise field background (`field()` equivalent).** Port the numpy Perlin/
   simplex-ish noise + radial halo to a GLSL noise function (standard 2D
   value/simplex noise — use a known-good implementation, e.g. Inigo
   Quilez's or Ashima's `webgl-noise`, not a from-scratch one) evaluated
   per-pixel in the fragment shader. This should be visually equivalent to
   the current `field()` output, just computed on GPU instead of via numpy.

4. **Easing / mixing helpers.** `lerp`, `mix`, `smoothstep`, `ease` all have
   direct GLSL built-in or one-line equivalents — port these as trivial
   GLSL utility functions in the shared include file.

5. **Scene porting order.** Port one scene fully first as a proof of concept
   (`vis_now_slice` is a good candidate — it uses circles, a glow rectangle,
   and text, a good cross-section of primitives). Render it, place it side
   by side with the current PIL output at the same `u` values, and confirm:
   - Composition matches (same positions, same relative scale)
   - Color matches (same palette, same alpha/opacity behavior)
   - The glow looks visibly better (additive, soft, no hard blur edge)
   Do not proceed to the remaining scenes until this comparison is confirmed.

6. **Per-scene parameters.** Each scene currently reads scattered constants
   (radius, seed, alpha, blur amount) hardcoded in pixels. When porting,
   express these as fractions of `u_resolution` rather than fixed pixel
   values, so output is resolution-independent going forward.

## Constraints

- Do not change any scene's narrative timing, text content, or color
  palette. This is a backend port, not a rewrite of content.
- Do not introduce 3D — this stays a 2D/screen-space shader pipeline.
- Do not silently invent noise/SDF math — use documented, standard
  formulas (Book of Shaders, iquilez's SDF functions, Ashima's noise) and
  cite which one you used in code comments.
- Confirm the headless render harness actually works on the target rented
  GPU environment (not just locally) before porting more than one scene —
  flag any driver/EGL/headless-context issues immediately rather than
  working around them silently.
- Keep the primitive functions in a shared include file used by all scene
  shaders — no copy-pasted SDF math per scene.

## Deliverables

1. `render_harness.py` — moderngl headless setup, uniform-passing, PNG
   sequence output, wired to existing ffmpeg assembly.
2. `primitives.glsl` — shared SDF/noise/easing function library.
3. One fully ported scene shader + side-by-side comparison output
   (old PNG vs new PNG at matching `u` values) for review.
4. A short written note on any place where GLSL output necessarily
   differs from the PIL original (e.g. anti-aliasing quality, blur
   softness) and why.

## Reference material to consult while implementing (do not skip)

- "The Book of Shaders" — for SDF fundamentals, noise, and fragment
  shader basics generally.
- Inigo Quilez's 2D distance function article — canonical SDF formulas
  for segments, arcs, rounded boxes, polygons.
- Ashima Arts' `webgl-noise` — canonical GLSL simplex/Perlin noise
  implementations.
- `moderngl` GitHub repo `examples/` folder — for headless context setup
  patterns in Python.
