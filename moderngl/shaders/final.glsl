// final.glsl — Synthesis. Audio completes the crossing.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float cy = 0.43;

    // Barrier
    vec2 bP = (uv - vec2(0.515, cy)) * iResolution;
    float dWall = sdRoundedBox(bP, vec2(0.065, 0.255) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall - 2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));

    // Enzyme chamber — forms faster on beat
    float chamber = smoothstep(0.05, 0.55, u) + u_audioBeat * 0.1;
    chamber = min(1.0, chamber);
    if (chamber > 0.01) {
        vec3 chamberCol = scenePalette(0.3 + u_audioVolume * 0.2, PA, PB, PC, PD);
        for (int i = 0; i < 80; i++) {
            float a = mix(3.316, 6.108, float(i) / 79.0);
            vec2 ap = vec2(0.515 + cos(a) * 0.18, cy + sin(a) * 0.18);
            col += chamberCol * glowSoft(uv, ap, 0.004) * chamber * 0.3;
        }
    }

    // Gold probability filament — audio pushes it across
    float cross = smoothstep(0.40, 0.93, u) + u_audioBeat * 0.1;
    cross = min(1.0, cross);
    float audioEnergy = 0.5 + 0.5 * u_audioVolume;

    if (cross > 0.01) {
        vec3 goldCol = scenePalette(0.5 + u_audioVolume * 0.3, PA, PB, PC, PD);
        for (int i = 0; i < 180; i++) {
            float q = float(i) / 179.0 * cross;
            float x = mix(0.12, 0.88, q);
            float inBarrier = (x > 0.45 && x < 0.58) ? 1.0 : 0.0;
            float amp = inBarrier > 0.5 ? 0.028 * exp(-5.0 * (x - 0.45) / 0.13) : 0.028;
            amp *= audioEnergy;
            float y = cy + sin(q * 6.28318 * 7.0 - t * 2.5 + u_audioBeat * 3.0) * amp;
            col += goldCol * glowSoft(uv, vec2(x, y), 0.004) * 0.5;
        }
    }

    // Green emergence — brightens with audio
    if (cross > 0.86) {
        vec3 emergeCol = scenePalette(0.8 + u_audioBeat * 0.2, PA, PB, PC, PD);
        float emergeR = 0.02 + 0.015 * u_audioVolume;
        col += emergeCol * glowSoft(uv, vec2(0.82, cy), emergeR) * 0.5;
        col += emergeCol * glowSoft(uv, vec2(0.82, cy), emergeR * 0.3) * 0.8;
    }

    fragColor = vec4(col, 1.0);
}
