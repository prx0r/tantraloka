// isotope.glsl — H vs D. Audio modulates transmission probability distinction.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    // Barrier
    vec2 bP = (uv - vec2(0.53, 0.44)) * iResolution;
    float dW = sdRoundedBox(bP, vec2(0.06, 0.255) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dW - 2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dW, 2.0));

    float prog = ease(u);
    float audioEnergy = 0.6 + 0.4 * u_audioVolume;

    // Hydrogen (gold)
    float hy = 0.34;
    vec3 hCol = scenePalette(0.1, PA, PB, PC, PD);
    // Wave approach
    for (int i = 0; i < 90; i++) {
        float q = float(i) / 89.0; if (q > prog) break;
        float x = mix(0.25, 0.47, q);
        float y = hy + sin(q * 6.28318 * 3.4 + u_audioBeat * 2.0) * 0.03;
        col += hCol * glowSoft(uv, vec2(x, y), 0.004) * 0.4 * audioEnergy;
    }
    // Transmission
    float hTrans = 0.82 * prog * audioEnergy;
    for (int j = 0; j < int(hTrans * 500.0); j++) {
        float q = float(j) / (hTrans * 500.0);
        float x = 0.62 + q * 0.23 * hTrans;
        col += hCol * glowSoft(uv, vec2(x, hy), 0.004) * 0.35 * audioEnergy;
    }

    // Deuterium (crimson)
    float dy = 0.55;
    vec3 dCol = scenePalette(0.7, PA, PB, PC, PD);
    for (int i = 0; i < 90; i++) {
        float q = float(i) / 89.0; if (q > prog) break;
        float x = mix(0.25, 0.47, q);
        float y = dy + sin(q * 6.28318 * 3.4 + u_audioBeat * 2.0) * 0.03;
        col += dCol * glowSoft(uv, vec2(x, y), 0.004) * 0.4 * audioEnergy;
    }
    float dTrans = 0.30 * prog * audioEnergy;
    for (int j = 0; j < int(dTrans * 500.0); j++) {
        float q = float(j) / (dTrans * 500.0);
        float x = 0.62 + q * 0.23 * dTrans;
        col += dCol * glowSoft(uv, vec2(x, dy), 0.004) * 0.35 * audioEnergy;
    }

    fragColor = vec4(col, 1.0);
}
