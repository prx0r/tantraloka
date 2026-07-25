// mass.glsl — Mass comparison. Audio modulates transmission energy per particle.
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
    vec2 bP = (uv - vec2(0.54, 0.44)) * iResolution;
    float dW = sdRoundedBox(bP, vec2(0.06, 0.255) * iResolution, 8.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dW - 2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dW, 2.0));

    // Particle rows: electron, proton, deuterium, heavy atom
    float ys[4] = float[](0.38, 0.53, 0.68, 0.83);
    float trans[4] = float[](1.00, 0.56, 0.27, 0.06);
    vec3 pals[4];
    pals[0] = scenePalette(0.0, PA, PB, PC, PD);
    pals[1] = scenePalette(0.25, PA, PB, PC, PD);
    pals[2] = scenePalette(0.5, PA, PB, PC, PD);
    pals[3] = scenePalette(0.75, PA, PB, PC, PD);

    float audioEnergy = 0.5 + 0.5 * u_audioVolume;

    for (int i = 0; i < 4; i++) {
        float py = ys[i];
        float pct = trans[i];
        vec3 pCol = pals[i];

        float progress = smoothstep(float(i) * 0.11, min(1.0, float(i) * 0.11 + 0.58), u);

        // Wave approaching
        float waveLen = progress * 0.34;
        for (int j = 0; j < int(62.0 * progress) + 1; j++) {
            float q = float(j) / 62.0;
            float x = 0.28 + q * waveLen;
            float wy = py + sin(float(j) * 0.46 - t * 3.0 + u_audioBeat * 2.0) * 0.02;
            col += pCol * glowSoft(uv, vec2(x, wy), 0.003) * 0.35 * audioEnergy;
        }

        // Transmission — stronger with audio
        float farLen = 0.22 * pct * progress * (0.8 + 0.4 * u_audioVolume);
        for (int j = 0; j < int(farLen * 200.0); j++) {
            float q = float(j) / (farLen * 200.0);
            float x = 0.62 + q * farLen;
            col += pCol * glowSoft(uv, vec2(x, py), 0.004) * 0.3 * audioEnergy;
        }
    }

    fragColor = vec4(col, 1.0);
}
