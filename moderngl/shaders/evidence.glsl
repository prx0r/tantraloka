// evidence.glsl — Multiple lines converge. Audio modulates radiating energy.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    vec2 center = vec2(0.50, 0.43);

    // Central hub — pulses with audio
    vec3 hubCol = scenePalette(0.3 + u_audioBeat * 0.2, PA, PB, PC, PD);
    col += hubCol * glowSoft(uv, center, 0.02) * (0.3 + 0.3 * u_audioVolume);
    col += hubCol * glowSoft(uv, center, 0.008) * (0.5 + 0.4 * u_audioBeat);

    // Radiating evidence terms
    vec2 offs[5] = vec2[](vec2(-0.172, -0.132), vec2(0.172, -0.132),
        vec2(-0.180, 0.146), vec2(0.180, 0.146), vec2(0.000, 0.250));

    float reveal = u * 5.0;
    float audioEnergy = 0.6 + 0.4 * u_audioVolume;

    for (int i = 0; i < 5; i++) {
        float q = clamp(reveal - float(i));
        vec2 end = center + offs[i] * ease_out(q);

        // Radial connecting line — each term has unique palette phase
        vec3 lineCol = scenePalette(0.2 + float(i) * 0.15 + u_audioBeat * 0.1, PA, PB, PC, PD);
        for (int j = 0; j < 50; j++) {
            float lq = float(j) / 49.0 * q;
            vec2 lp = mix(center, end, lq);
            col += lineCol * glowSoft(uv, lp, 0.003) * 0.25 * audioEnergy;
        }

        // Term glow — brightens on beat
        col += lineCol * glowSoft(uv, end, 0.012) * q * 0.4 * audioEnergy;
        col += lineCol * glowSoft(uv, end, 0.005) * q * 0.8 * (0.5 + 0.5 * u_audioBeat);
    }

    fragColor = vec4(col, 1.0);
}
