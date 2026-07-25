// final.glsl — Life crosses barriers it cannot climb (synthesis)
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float cy = 0.43;
    // Barrier
    vec2 bP = (uv - vec2(0.515, cy)) * iResolution;
    float dWall = sdRoundedBox(bP, vec2(0.065, 0.255) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall-2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // Enzyme chamber forming around wall (arcs)
    float chamber = smoothstep(0.05, 0.55, u);
    if (chamber > 0.0) {
        float a_start = 3.316;
        for (int i = 0; i < 80; i++) {
            float a = mix(a_start, 6.108, float(i)/79.0);
            vec2 ap = vec2(0.515 + cos(a)*0.18, cy + sin(a)*0.18);
            col += vec3(0.263,0.616,0.706) * glowSoft(uv, ap, 0.004) * chamber * 0.3;
        }
    }
    // Gold probability filament crossing barrier
    float cross = smoothstep(0.40, 0.93, u);
    if (cross > 0.0) {
        for (int i = 0; i < 180; i++) {
            float q = float(i) / 179.0 * cross;
            float x = mix(0.12, 0.88, q);
            float inBarrier = (x > 0.45 && x < 0.58) ? 1.0 : 0.0;
            float amp = inBarrier > 0.5 ? 0.028 * exp(-5.0 * (x - 0.45) / 0.13) : 0.028;
            float y = cy + sin(q * 6.28318 * 7.0 - t * 2.5) * amp;
            col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x, y), 0.004) * 0.5;
        }
    }
    // Green emergence beyond barrier
    if (cross > 0.86) {
        float eGlow = glowSoft(uv, vec2(0.82, cy), 0.02);
        col += vec3(0.282,0.529,0.396) * eGlow * 0.5;
    }
    fragColor = vec4(col, 1.0);
}
