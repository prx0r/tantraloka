// =============================================================================
// primitives.glsl — Lygia-wrapped pipeline core with bloom helper uniforms
// =============================================================================
#ifndef PRIMITIVES_GLSL
#define PRIMITIVES_GLSL

#include "lygia/math/const.glsl"
#include "lygia/math/lerp.glsl"
#include "lygia/sdf/circle.glsl"
#include "lygia/sdf/ellipse.glsl"
#include "lygia/sdf/segment.glsl"
#include "lygia/sdf/boxRounded.glsl"
#include "lygia/sdf/arc.glsl"
#include "lygia/sdf/polygon.glsl"
#include "lygia/draw/stroke.glsl"
#include "lygia/draw/fill.glsl"
#include "lygia/generative/snoise.glsl"
#include "lygia/generative/fbm.glsl"
#include "lygia/animation/easing.glsl"
#include "lygia/color/palette/cosine.glsl"
#include "lygia/color/tonemap/aces.glsl"
#include "lygia/filter/gaussianBlur.glsl"

// Our naming aliases
#define ease easeInOutCubic
#define ease_out easeOutCubic
#define lerp lerp

float sdSegment(vec2 p, vec2 a, vec2 b) { return segment(p, a, b); }
float sdCircle(vec2 p, float r) { return circle(p, r); }
float sdEllipse(vec2 p, vec2 r) { return ellipse(p, r); }
float sdRoundedBox(vec2 p, vec2 b, float r) { return boxRounded(p, b, r); }
float sdArc(vec2 p, vec2 sc, float ra, float rb) { return arc(p, sc, ra, rb); }

float pulse(float t, float hz, float phase) {
    return 0.5 + 0.5 * sin(6.28318 * (hz * t + phase));
}

// Domain-warped FBM for organic texture
float fbmWarped(vec2 p) {
    return fbm(p + fbm(p + fbm(p)));
}

// Background: noise field + vignette
vec3 fieldBackground(vec2 uv, vec2 resolution, float t, vec3 baseColor) {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;
    float n = fbmWarped(p * 3.0 + t * 0.05);
    float n2 = fbmWarped(p * 6.0 - t * 0.03 + vec2(1.7, 9.2));
    vec3 noiseColor = baseColor + vec3(0.02, 0.01, -0.01) * (n - 0.5)
                                 + vec3(-0.01, 0.02, 0.01) * (n2 - 0.5);
    float vig = 1.0 - 0.3 * length(p);
    return noiseColor * vig;
}

// Additive glow helper — output in LINEAR space for bloom to work correctly
// These values accumulate additively, NOT via alpha blend
float glowSoft(vec2 p, vec2 center, float radius) {
    float d = length(p - center);
    return exp(-d * d / (2.0 * radius * radius));
}

float glowLine(vec2 p, vec2 a, vec2 b, float width) {
    float d = sdSegment(p, a, b);
    return exp(-d * d / (2.0 * width * width));
}

// Cosine palette from a single float — maps scene progress to evolving color
// Each pack defines its own a,b,c,d constants
vec3 scenePalette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return cosinePalette(t, a, b, c, d);
}

// Helper: apply audio modulation to a scalar
float audioMod(float value, float audioVolume, float audioBeat, float volumeSensitivity, float beatSensitivity) {
    return value * (1.0 + volumeSensitivity * (audioVolume - 0.5) + beatSensitivity * audioBeat);
}

#endif
