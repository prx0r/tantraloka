// form.glsl — Triangle / double-well. Audio pulses vertices and emergence.
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
    vec2 a = vec2(0.50, 0.20), b = vec2(0.25, 0.68), c = vec2(0.75, 0.68);
    vec2 edges[3] = vec2[](a, b, c);

    // Triangle edges — audio speeds up reveal
    float revealQ = min(1.0, q + u_audioBeat * 0.05);
    for (int i = 0; i < 3; i++) {
        float localQ = clamp(revealQ * 3.0 - float(i));
        vec2 s = edges[i], e = edges[(i + 1) % 3];
        vec3 lineCol = scenePalette(0.2 + float(i) * 0.2, PA, PB, PC, PD);
        for (int j = 0; j < 60; j++) {
            float lq = float(j) / 59.0 * localQ;
            vec2 lp = mix(s, e, lq);
            col += lineCol * glowSoft(uv, lp, 0.003) * 0.5;
        }
    }

    // Vertex glows — pulse with audio
    float vertexEnergy = smoothstep(0.72, 0.80, q) * (0.5 + 0.5 * u_audioVolume);
    if (vertexEnergy > 0.01) {
        for (int i = 0; i < 3; i++) {
            vec3 vCol = scenePalette(0.6 + float(i) * 0.15 + u_audioBeat * 0.2, PA, PB, PC, PD);
            float pulseR = 0.012 + 0.008 * u_audioBeat;
            col += vCol * glowSoft(uv, edges[i], pulseR) * vertexEnergy * 0.6;
            col += vCol * glowSoft(uv, edges[i], pulseR * 0.3) * vertexEnergy * 1.2;
        }
    }

    fragColor = vec4(col, 1.0);
}
