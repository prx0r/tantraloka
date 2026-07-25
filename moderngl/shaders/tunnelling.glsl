// tunnelling.glsl — Wavefunction penetrates barrier exponentially
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float cy = 0.44; float bx0 = 0.46; float bx1 = 0.62;
    // Barrier
    vec2 bP = (uv - vec2((bx0+bx1)*0.5, 0.44)) * iResolution;
    float dWall = sdRoundedBox(bP, vec2((bx1-bx0)*0.5, 0.24) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall-2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // Wave with exponential decay through barrier
    float reveal = ease(u);
    for (int i = 0; i < 240; i++) {
        float q = float(i) / 239.0;
        if (q > reveal) break;
        float x = mix(0.10, 0.90, q);
        float amp = 0.085;
        if (x > bx0 && x <= bx1) amp *= exp(-5.8 * (x - bx0) / max(0.001, bx1-bx0));
        else if (x > bx1) amp *= exp(-5.8) * 3.3;
        float y = cy + sin(q * 6.28318 * 8.0 - t * 3.0) * amp;
        float waveGlow = glowSoft(uv, vec2(x, y), 0.003);
        col += vec3(0.749,0.604,0.286) * waveGlow * 0.5;
    }
    // Detection event beyond barrier
    float detect = smoothstep(0.66, 0.90, u);
    if (detect > 0.0) {
        float dx = mix(bx1+0.02, 0.80, detect);
        float dGlow = glowSoft(uv, vec2(dx, cy), 0.02);
        col += vec3(0.749,0.604,0.286) * dGlow * detect * 0.5;
    }
    fragColor = vec4(col, 1.0);
}
