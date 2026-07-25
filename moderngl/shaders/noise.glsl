// noise.glsl — Noise organizes. Audio drives the convergence.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    // Convergence driven by both u and audio
    float organize = smoothstep(0.25, 0.85, u) + u_audioBeat * 0.1;
    organize = min(1.0, organize);
    float audioEnergy = 0.5 + 0.5 * u_audioVolume;

    // Scattering noise → organized wave
    for (int i = 0; i < 120; i++) {
        float seed = float(i) * 0.618;
        float rx = fract(seed + 0.1);
        float ry = fract(seed * 1.7 + 0.3);
        float x = mix(0.10, 0.90, rx);
        float targetY = 0.44 + sin(x * 6.28318 * 3.0 + u_audioBeat * 2.0) * 0.04;
        float yy = mix(ry * 0.6, targetY, organize);
        vec3 ptCol = scenePalette(rx + u_audioVolume * 0.2, PA, PB, PC, PD);
        col += ptCol * glowSoft(uv, vec2(x, yy), 0.004) * 0.35 * audioEnergy;
    }

    // Emergent wave
    if (organize > 0.35) {
        vec3 waveCol = scenePalette(0.5 + u_audioBeat * 0.2, PA, PB, PC, PD);
        float waveEnergy = organize * audioEnergy;
        for (int i = 0; i < 120; i++) {
            float q = float(i) / 119.0 * organize;
            float x = 0.12 + q * 0.76;
            float y = 0.44 + sin(q * 6.28318 * 3.0 + u_audioBeat * 3.0) * 0.04;
            col += waveCol * glowSoft(uv, vec2(x, y), 0.003) * waveEnergy * 0.4;
        }
    }

    fragColor = vec4(col, 1.0);
}
