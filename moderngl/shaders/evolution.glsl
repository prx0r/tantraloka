// evolution.glsl — Generations narrow. Audio paces the generational gap closing.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float y = 0.45;
    int gens = 7;
    float audioEnergy = 0.6 + 0.4 * u_audioVolume;

    for (int i = 0; i < gens; i++) {
        float q = clamp(u * float(gens) - float(i));
        float x = mix(0.12, 0.88, float(i) / float(gens - 1));
        float improvement = float(i) / float(gens - 1);
        // Gap narrows with evolution, pulses with audio
        float gap = mix(0.094, 0.041, improvement) - u_audioBeat * 0.005;

        // Arc pair
        vec3 arcCol = scenePalette(0.3 + float(i) * 0.08, PA, PB, PC, PD);
        float arcEnergy = q * (0.3 + 0.2 * audioEnergy);
        for (int j = 0; j < 40; j++) {
            float a = mix(3.316, 6.108, float(j) / 39.0);
            vec2 ap = vec2(x + cos(a) * 0.03, y - 0.06 + sin(a) * 0.03);
            col += arcCol * glowSoft(uv, ap, 0.003) * arcEnergy;
        }

        // Gold connecting line — stronger with audio
        float lineLen = q * audioEnergy;
        for (int j = 0; j < int(lineLen * 30.0); j++) {
            float lq = float(j) / (lineLen * 30.0);
            float lx = mix(x - gap * 0.5, x + gap * 0.5, lq);
            vec3 gold = scenePalette(0.5 + improvement * 0.2, PA, PB, PC, PD);
            col += gold * glowSoft(uv, vec2(lx, y), 0.003) * q * 0.4;
        }

        // Arrow pulses on beat
        if (i < gens - 1 && q > 0.5) {
            float arrowAmp = 0.3 + 0.5 * u_audioBeat;
            float nx = mix(0.12, 0.88, float(i + 1) / float(gens - 1));
            for (int j = 0; j < 20; j++) {
                float lq = float(j) / 19.0;
                vec2 ap = vec2(x + 0.038, y + 0.167) + vec2(nx - x, 0.0) * lq * 0.5;
                col += vec3(0.337, 0.349, 0.369) * glowSoft(uv, ap, 0.002) * arrowAmp;
            }
        }
    }

    fragColor = vec4(col, 1.0);
}
