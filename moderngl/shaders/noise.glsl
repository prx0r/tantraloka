// noise.glsl — Control without purity.
// Scattering noise points converge into an organized wave.
// The energy of disorder becomes structured through repetition, not force.
// Audio: convergence accelerates with voice, emergent wave pulses with beat.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    // Convergence driven by both narrative progress and audio
    float organize = smoothstep(0.25, 0.85, u) + u_audioBeat * 0.08 + u_audioVolume * 0.05;
    organize = min(1.0, organize);
    float audioEnergy = 0.4 + 0.6 * u_audioVolume;

    // Scattering noise points → they find their place in the wave
    for (int i = 0; i < 120; i++) {
        float seed = float(i) * 0.618034; // golden ratio for even distribution
        float rx = fract(seed + 0.1);
        float ry = fract(seed * 1.7 + 0.3);

        float x = mix(0.10, 0.90, rx);
        float targetY = 0.44 + sin(x * 6.28318 * 3.0 + u_audioBeat * 2.0 + t * 0.5) * 0.04;

        // Scatter before convergence — the noise spreads when audio is quiet
        float scatter = 1.0 - organize + u_audioVolume * 0.1;
        float yy = mix(ry * 0.5 + 0.2, targetY, organize)
                   + scatter * (fract(sin(float(i) * 43758.5453 + t)) - 0.5) * 0.05;

        vec3 ptCol = scenePalette(rx * 0.5 + u_audioVolume * 0.2 + float(i) * 0.001,
                                   PA, PB, PC, PD);

        // Point size: larger when converging, dim when scattered
        float ptR = 0.003 + 0.003 * organize + 0.002 * u_audioBeat;
        float ptBright = 0.2 + 0.3 * organize + 0.2 * u_audioVolume;
        col += ptCol * glowSoft(uv, vec2(x, yy), ptR) * ptBright;
    }

    // Emergent wave — the structure that noise becomes
    if (organize > 0.3) {
        vec3 waveCol = scenePalette(0.5 + u_audioBeat * 0.2, PA, PB, PC, PD);
        float waveEnergy = organize * audioEnergy;

        for (int i = 0; i < 120; i++) {
            float wq = float(i) / 119.0 * organize;
            float wx = 0.12 + wq * 0.76;
            float wy = 0.44 + sin(wq * 6.28318 * 3.0 + u_audioBeat * 3.0 + t * 0.5) * 0.04;
            col += waveCol * glowSoft(uv, vec2(wx, wy), 0.003) * waveEnergy * 0.5;

            // Wave core — brighter on beat
            if (u_audioBeat > 0.5) {
                col += waveCol * glowSoft(uv, vec2(wx, wy), 0.0015) * u_audioBeat * 0.3;
            }
        }
    }

    fragColor = vec4(col, 1.0);
}
