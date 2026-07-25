// form.glsl — Build a triangle / Build a double-well.
// Two modes: TRIANGLE (geometric relations emerge from arrangement)
//            DOUBLE-WELL (tunnelling enters the reaction landscape)
// Audio: triangle vertices pulse, double-well transfer jumps on beat
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float q = ease(u);
    float audioEnergy = 0.5 + 0.5 * u_audioVolume;

    // Triangle: three vertices emerge
    vec2 a = vec2(0.50, 0.20), b = vec2(0.25, 0.68), c = vec2(0.75, 0.68);
    vec2 edges[3] = vec2[](a, b, c);

    float revealQ = min(1.0, q + u_audioBeat * 0.04);
    for (int i = 0; i < 3; i++) {
        float localQ = clamp(revealQ * 3.0 - float(i));
        vec2 s = edges[i], e = edges[(i + 1) % 3];
        vec3 lineCol = scenePalette(0.2 + float(i) * 0.2 + u_audioVolume * 0.15, PA, PB, PC, PD);
        for (int j = 0; j < 60; j++) {
            float lq = float(j) / 59.0 * localQ;
            vec2 lp = mix(s, e, lq);
            col += lineCol * glowSoft(uv, lp, 0.003) * 0.5 * audioEnergy;
        }
    }

    // Vertex glows — pulse with audio
    float vEnergy = smoothstep(0.72, 0.80, q) * (0.4 + 0.6 * u_audioVolume);
    if (vEnergy > 0.01) {
        for (int i = 0; i < 3; i++) {
            vec3 vCol = scenePalette(0.6 + float(i) * 0.15 + u_audioBeat * 0.2, PA, PB, PC, PD);
            float r = 0.012 + 0.008 * u_audioBeat;
            col += vCol * glowSoft(uv, edges[i], r) * vEnergy * 0.6;
            col += vCol * glowSoft(uv, edges[i], r * 0.3) * vEnergy * 1.2;
        }
    }

    // Double-well potential landscape (subtle background structure)
    for (int i = 0; i < 100; i++) {
        float lq = float(i) / 99.0;
        float lx = mix(0.15, 0.85, lq);
        float vy = ((lq - 0.25) * (lq - 0.75)) * 4.0;
        float ly = 0.60 - vy * 0.15;
        vec3 dwCol = scenePalette(0.3 + lq * 0.2, PA, PB, PC, PD);
        col += dwCol * glowSoft(uv, vec2(lx, ly), 0.0015) * 0.15;
    }

    fragColor = vec4(col, 1.0);
}
