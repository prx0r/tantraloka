// =============================================================================
// primitives.glsl — Shared SDF, noise, easing, palette, and drawing utilities
// =============================================================================
// References:
//   - iq's 2D SDF functions: https://iquilezles.org/articles/distfunctions2d/
//   - Ashima's webgl-noise: https://github.com/ashima/webgl-noise
//   - Book of Shaders: https://thebookofshaders.com/
// =============================================================================

#ifndef PRIMITIVES_GLSL
#define PRIMITIVES_GLSL

// ---------------------------------------------------------------------------
// EASING
// ---------------------------------------------------------------------------
float ease(float t) { return 0.5 - 0.5 * cos(3.14159 * t); }
float ease_out(float t) { return 1.0 - pow(1.0 - clamp(t,0.0,1.0), 3.0); }
float pulse(float t, float hz, float phase) {
    return 0.5 + 0.5 * sin(6.28318 * (hz * t + phase));
}

// ---------------------------------------------------------------------------
// 2D SDF PRIMITIVES (iq implementations)
// ---------------------------------------------------------------------------

// Signed distance to a line segment: p is point, a and b are endpoints
float sdSegment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

// Signed distance to an ellipse (non-uniform)
float sdEllipse(vec2 p, vec2 r) {
    float a = r.x, b = r.y;
    float a2 = a*a, b2 = b*b;
    float k0 = length(p / vec2(a, b)) - 1.0;
    float k1 = length(p / vec2(a2, b2)) - 1.0;
    return k0 < 0.0 ? k0 : k1;
}

// Signed distance to a circle
float sdCircle(vec2 p, float r) {
    return length(p) - r;
}

// Signed distance to an arc (iq's sdArc)
float sdArc(vec2 p, vec2 sc, float ra, float rb) {
    // sc = (cos(angle), sin(angle)) of half-arc
    // ra = inner radius, rb = outer radius
    p.x = abs(p.x);
    float q = length(p) - (ra + rb) * 0.5;
    float d = length(p - vec2(clamp(p.x, 0.0, ra * sc.x), ra * sc.y));
    return d * sign(p.y - ra * sc.y);
}

// Signed distance to a rounded rectangle
float sdRoundedBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// Signed distance to a regular polygon (n sides)
float sdPolygon(vec2 p, vec2* v, int n) {
    float d = dot(p - v[0], p - v[0]);
    float s = 1.0;
    for (int i = 0; i < n; i++) {
        vec2 a = v[i];
        vec2 b = v[(i+1) % n];
        vec2 pa = p - a, ba = b - a;
        float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
        d = min(d, length(pa - ba * h));
        vec2 e = a - b;
        s = sign(dot(cross(vec3(e,0.0), vec3(ba,0.0)).xy, p - b));
    }
    return d * s;
}

// ---------------------------------------------------------------------------
// STROKE / FILL HELPERS
// ---------------------------------------------------------------------------
float stroke(float d, float w) {
    return smoothstep(w + 0.5, w - 0.5, abs(d));
}

float fill(float d) {
    return 1.0 - smoothstep(0.0, 0.5, d);
}

// ---------------------------------------------------------------------------
// NOISE (Ashima/webgl-noise based)
// ---------------------------------------------------------------------------
vec3 mod289(vec3 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                        -0.577350269189626, 0.024390243902439);
    vec2 i = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = step(x0.yx, x0.xy);
    vec4 x12 = vec4(i1.xy, 1.0 - i1.xy) + C.xxzz;
    i = mod289(i); vec3 p0 = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
        + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m; m = m*m;
    vec3 x = 2.0 * fract(p0 * C.www) - 1.0;
    vec3 h = abs(x) - 0.5; vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
    vec3 g = vec3(0.0);
    g.x = a0.x * x0.x + h.x * x0.y;
    g.y = a0.y * x12.x + h.y * x12.y;
    g.z = a0.z * x12.z + h.z * x12.w;
    return 130.0 * dot(m, g);
}

// Fractal Brownian Motion — domain-warped for organic textures
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for (int i = 0; i < 4; i++) {
        value += amplitude * snoise(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
        p = p + vec2(1.7, 9.2) * amplitude; // domain warp
    }
    return value * 0.5 + 0.5;
}

// ---------------------------------------------------------------------------
// COSINE PALETTE (iq)
// ---------------------------------------------------------------------------
// https://iquilezles.org/articles/palettes/
vec3 cosinePalette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

// ---------------------------------------------------------------------------
// LERP / MIX (GLSL built-ins: mix, smoothstep already exist)
// ---------------------------------------------------------------------------
vec3 mix3(vec3 a, vec3 b, float t) { return a + (b - a) * clamp(t, 0.0, 1.0); }

// ---------------------------------------------------------------------------
// BACKGROUND FIELD — domain-warped noise + vignette + subtle halo
// ---------------------------------------------------------------------------
vec3 fieldBackground(vec2 uv, vec2 resolution, float t, vec3 baseColor) {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;

    // Domain-warped noise field
    float n = fbm(p * 3.0 + t * 0.05);
    float n2 = fbm(p * 6.0 - t * 0.03 + vec2(1.7, 9.2));

    // Subtle color variation from noise
    vec3 noiseColor = baseColor + vec3(0.02, 0.01, -0.01) * (n - 0.5)
                                 + vec3(-0.01, 0.02, 0.01) * (n2 - 0.5);

    // Vignette
    float vignette = 1.0 - 0.3 * length(p);

    // Subtle edge glow (darker, not lighter — keeps the field feeling natural)
    float edgeGlow = exp(-length(p) * 3.0) * 0.08;

    return noiseColor * vignette + edgeGlow;
}

// ---------------------------------------------------------------------------
// GLOW — additive glow for HDR pipeline
// ---------------------------------------------------------------------------
// Call this BEFORE the bloom pass. Renders soft glowing shapes additively.

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
vec3 chromaticAberration(float d) {
    return vec3(1.0 + d * 0.02, 1.0, 1.0 - d * 0.02);
}

#endif
