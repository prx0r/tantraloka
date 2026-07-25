# ModernGL GPU Render Pipeline

## Architecture
PIL pack → scene data (narration, timing, visual params) → GLSL fragment shaders → GPU render → HDR frames → ffmpeg MP4

## Structure
```
moderngl/
├── shaders/              # GLSL fragment shaders (*.glsl)
│   ├── include/          # Shared GLSL modules
│   │   ├── srgb.glsl         # Linear/sRGB conversion
│   │   ├── bloom.glsl        # HDR bloom pipeline
│   │   ├── easing.glsl       # ease(), smoothstep(), pulse()
│   │   ├── palette.glsl      # Color mixing, lerp
│   │   └── noise.glsl        # GPU noise functions
│   ├── classical_wall.glsl   # ported from visual_classical_wall()
│   ├── tunnelling.glsl       # ported from visual_tunnelling()
│   ├── enzyme_pocket.glsl    # ported from visual_enzyme_pocket()
│   └── ...                   # one per visual mode across all packs
├── renderer/
│   ├── engine.py         # ModernGL context, framebuffer, render loop
│   ├── pack_loader.py    # Load python pack, extract scenes, map to shaders
│   └── bloom.py          # Post-processing: downsample → blur → upsample → add
├── packs/                # Symlinked/copied *_platinum.py packs
├── output/               # Rendered MP4s
└── render_all.py         # CLI: discover packs, render each with GPU
```

## Key Differences from PIL

| PIL (current) | GLSL (new) |
|--------------|------------|
| 8-bit per channel, sRGB | fp32 per channel, linear |
| Alpha blend glow (muddy) | Additive bloom (bright) |
| `draw.line(points)` | Fullscreen fragment shader — math per pixel |
| `draw.ellipse()` | `length(uv - center) < radius` |
| `GaussianBlur` expensive on CPU | Single texture sample on GPU |
| Sequential frame CPU render | Parallel pixel GPU render |

## GLSL Scene Template
```glsl
#version 330 core

// Scene data (set by Python)
uniform float u;              // 0.0 → 1.0 scene progress
uniform float t;              // elapsed seconds
uniform vec2 iResolution;     // pixel dimensions
uniform vec4 iPalette[8];      // color palette (rgba)

// Include shared modules
#include "srgb.glsl"
#include "easing.glsl"
#include "bloom.glsl"

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    
    // Scene math goes here
    float wave = sin(uv.x * 3.14159 * 8.0 - t * 3.0);
    
    // Output in linear space (bloom pass handles tone mapping)
    fragColor = vec4(wave, 0.0, 0.0, 1.0);
}
```

## Converting a PIL Scene to GLSL

PIL `visual_tunnelling()` → `shaders/tunnelling.glsl`:

```glsl
#version 330 core

uniform float u;
uniform float t;
uniform vec2 iResolution;

// Palette: INK, GOLD, SILVER, PALE_SILVER
const vec3 INK = vec3(0.118, 0.125, 0.141);
const vec3 GOLD = vec3(0.749, 0.604, 0.286);
const vec3 SILVER = vec3(0.706, 0.729, 0.753);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    
    // Barrier wall (was draw.rounded_rectangle)
    float barrier = step(0.46, uv.x) - step(0.62, uv.x);
    
    // Wave with exponential decay through barrier (was wavefunction_points)
    float wave = sin(uv.x * 3.14159 * 8.0 - t * 3.0);
    float decay = exp(-5.8 * max(0.0, uv.x - 0.46) / 0.16);
    float amp = wave * 0.08 * decay;
    
    // Glow (additive, not alpha blend)
    float glow = exp(-pow(length(uv - vec2(uv.x, 0.44 + amp)), 2.0) * 800.0);
    
    // Composite
    vec3 col = vec3(1.0); // white background
    col = mix(col, INK, barrier * 0.5);
    col += GOLD * glow * 0.6;  // ADDITIVE glow
    
    fragColor = vec4(col, 1.0);
}
```

## HDR Bloom Pipeline
The biggest visual upgrade. Applied as post-processing to every frame:

```
1. Render scene → HDR framebuffer (fp32, linear)
2. Extract bright pass: threshold > 1.0
3. Downsample 4x → 2x → 1x (gaussian pyramids)
4. Blur each mip level
5. Upsample and add back to original
6. Tone map to sRGB 8-bit
```

This is what makes it look like film instead of PIL.

## Usage on GPU Box
```bash
pip install moderngl numpy pillow
python renderer/render_all.py --pack life_crosses_barriers --fps 24 --width 1920 --height 1080
python renderer/render_all.py --all --output /mnt/output
```
