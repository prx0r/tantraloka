// width.glsl — Probability collapses exponentially with barrier width
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float cy = 0.44;
    float widthPhase = ease(u);
    float barrierWidth = mix(0.08, 0.30, widthPhase);
    float x0 = 0.50 - barrierWidth * 0.5;
    float x1 = 0.50 + barrierWidth * 0.5;
    // Barrier
    vec2 bP = (uv - vec2(0.50, cy)) * iResolution;
    float dWall = sdRoundedBox(bP, vec2(barrierWidth * 0.5, 0.25) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall-2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // Incident wave (left of barrier)
    float prob = exp(-5.4 * barrierWidth / 0.30);
    for (int i = 0; i < 120; i++) {
        float q = float(i) / 119.0;
        float x = mix(0.10, x0, q);
        float y = cy + sin(q * 6.28318 * 4.5 - t * 2.0) * 0.075;
        col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x,y), 0.003) * 0.4;
    }
    // Decay inside barrier
    for (int i = 0; i < 90; i++) {
        float q = float(i) / 89.0;
        float x = mix(x0, x1, q);
        float amp = 0.075 * exp(-5.0 * q);
        float y = cy + sin(q * 6.28318 * 2.0 - t * 2.0) * amp;
        col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x,y), 0.003) * 0.4;
    }
    // Output probability glow
    float outGlow = glowSoft(uv, vec2(0.78, cy), 0.02 + 0.04 * prob);
    col += vec3(0.749,0.604,0.286) * outGlow * (0.2 + 0.6 * prob);
    fragColor = vec4(col, 1.0);
}
