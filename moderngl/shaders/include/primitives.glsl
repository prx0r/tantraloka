// =============================================================================
// primitives.glsl — Wraps Lygia functions for our pipeline
// =============================================================================
// All core SDF, noise, easing, palette, and drawing functions come from Lygia:
// https://github.com/patriciogonzalezvivo/lygia
//
// This file re-exports them under our naming conventions and adds pipeline-
// specific helpers (fieldBackground, glowSoft, etc.)

#ifndef PRIMITIVES_GLSL
#define PRIMITIVES_GLSL

// --- Lygia includes --------------------------------------------------------

// Math constants
#include "lygia/math/const.glsl"
#include "lygia/math/lerp.glsl"

// SDF primitives (iq implementations, battle-tested)
#include "lygia/sdf/circle.glsl"
#include "lygia/sdf/ellipse.glsl"
#include "lygia/sdf/segment.glsl"
#include "lygia/sdf/boxRounded.glsl"
#include "lygia/sdf/arc.glsl"
#include "lygia/sdf/polygon.glsl"

// Draw helpers
#include "lygia/draw/stroke.glsl"
#include "lygia/draw/fill.glsl"

// Noise
#include "lygia/generative/snoise.glsl"
#include "lygia/generative/fbm.glsl"

// Easing
#include "lygia/animation/easing.glsl"

// Color / Tone mapping
#include "lygia/color/palette/cosine.glsl"
#include "lygia/color/tonemap/aces.glsl"

// Filter (gaussian blur)
#include "lygia/filter/gaussianBlur.glsl"
// (bloom is implemented in Python as multi-pass, using gaussianBlur per pass)

// --- Our naming aliases ----------------------------------------------------

#define ease easeInOutCubic
#define ease_out easeOutCubic
#define lerp lerp

// Map to iq SDF naming
float sdSegment(vec2 p, vec2 a, vec2 b) { return segment(p, a, b); }
float sdCircle(vec2 p, float r) { return circle(p, r); }
float sdEllipse(vec2 p, vec2 r) { return ellipse(p, r); }
float sdRoundedBox(vec2 p, vec2 b, float r) { return boxRounded(p, b, r); }
float sdArc(vec2 p, vec2 sc, float ra, float rb) { return arc(p, sc, ra, rb); }

// Pulse oscillator
float pulse(float t, float hz, float phase) {
    return 0.5 + 0.5 * sin(6.28318 * (hz * t + phase));
}

// Domain-warped FBM (wraps Lygia's fbm with domain warp built in)
float fbmWarped(vec2 p) {
    return fbm(p + fbm(p + fbm(p)));  // triple-warped for organic textures
}

// ---------------------------------------------------------------------------
// BACKGROUND FIELD — domain-warped noise + vignette + edge glow
// ---------------------------------------------------------------------------
vec3 fieldBackground(vec2 uv, vec2 resolution, float t, vec3 baseColor) {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;

    float n = fbmWarped(p * 3.0 + t * 0.05);
    float n2 = fbmWarped(p * 6.0 - t * 0.03 + vec2(1.7, 9.2));

    vec3 noiseColor = baseColor + vec3(0.02, 0.01, -0.01) * (n - 0.5)
                                 + vec3(-0.01, 0.02, 0.01) * (n2 - 0.5);

    float vig = 1.0 - 0.3 * length(p);
    float edgeGlow = exp(-length(p) * 3.0) * 0.08;

    return noiseColor * vig + edgeGlow;
}

// ---------------------------------------------------------------------------
// ADDITIVE GLOW (to be used before bloom pass, NOT alpha blend)
// ---------------------------------------------------------------------------
float glowSoft(vec2 p, vec2 center, float radius) {
    float d = length(p - center);
    return exp(-d * d / (2.0 * radius * radius));
}

float glowLine(vec2 p, vec2 a, vec2 b, float width) {
    float d = sdSegment(p, a, b);
    return exp(-d * d / (2.0 * width * width));
}

// ---------------------------------------------------------------------------
// CHROMATIC ABERRATION (post-process)
// ---------------------------------------------------------------------------
vec3 chromaticAberrationUV(vec2 uv, float intensity) {
    return vec3(uv.x + intensity * 0.5, uv.x, uv.x - intensity * 0.5);
}

#endif
