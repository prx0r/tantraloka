// isotope.glsl — Hydrogen vs Deuterium kinetic isotope effect
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    // Barrier
    vec2 bP = (uv - vec2(0.53, 0.44)) * iResolution;
    float dWall = sdRoundedBox(bP, vec2(0.06, 0.255) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall-2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // H row
    float prog = ease(u);
    float h_y = 0.34;
    for (int i = 0; i < 90; i++) {
        float q = float(i) / 89.0;
        if (q > prog) break;
        float x = mix(0.25, 0.47, q);
        float y = h_y + sin(q * 6.28318 * 3.4) * 0.03;
        col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x,y), 0.004) * 0.5;
    }
    float h_trans = 0.82 * prog;
    for (int j = 0; j < int(h_trans * 500); j++) {
        float q = float(j) / (h_trans * 500);
        float x = 0.62 + q * 0.23 * h_trans;
        col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x, h_y), 0.004) * 0.4;
    }
    // D row
    float d_y = 0.55;
    for (int i = 0; i < 90; i++) {
        float q = float(i) / 89.0;
        if (q > prog) break;
        float x = mix(0.25, 0.47, q);
        float y = d_y + sin(q * 6.28318 * 3.4) * 0.03;
        col += vec3(0.620,0.224,0.259) * glowSoft(uv, vec2(x,y), 0.004) * 0.5;
    }
    float d_trans = 0.3 * prog;
    for (int j = 0; j < int(d_trans * 500); j++) {
        float q = float(j) / (d_trans * 500);
        float x = 0.62 + q * 0.23 * d_trans;
        col += vec3(0.620,0.224,0.259) * glowSoft(uv, vec2(x, d_y), 0.004) * 0.4;
    }
    fragColor = vec4(col, 1.0);
}
