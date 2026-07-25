// enzyme.glsl — Breathing pocket. Audio modulates gap breathing and wave bridging.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float cx = 0.50, cy = 0.44;
    float breathe = 0.5 + 0.5 * sin(t * 1.2 + u_audioBeat * 3.0);
    float closing = smoothstep(0.15, 0.72, u);
    float gap = mix(0.184, 0.061, closing) + breathe * 0.009;
    // Audio pushes the gap narrower on beat
    gap -= u_audioBeat * 0.005;

    // Protein lobes
    vec3 lobeFill = vec3(0.769, 0.886, 0.906);
    vec3 lobeEdge = vec3(0.263, 0.616, 0.706);

    for (int side = -1; side <= 1; side += 2) {
        vec2 lp = (uv - vec2(cx + float(side) * (gap * 0.5 + 0.145), cy)) * iResolution;
        float dl = length(lp) - 120.0;
        col = mix(col, lobeFill, fill(dl) * 0.9);
        col = mix(col, lobeEdge, stroke(dl, 3.0) * 0.8);
    }

    // Donor/acceptor glow points
    vec2 donor = vec2(cx - gap * 0.5, cy);
    vec2 acceptor = vec2(cx + gap * 0.5, cy);

    vec3 donorCol = scenePalette(0.2 + u_audioVolume * 0.3, PA, PB, PC, PD);
    vec3 acceptorCol = scenePalette(0.6 + u_audioBeat * 0.2, PA, PB, PC, PD);

    col += donorCol * glowSoft(uv, donor, 0.015) * (0.4 + 0.3 * u_audioVolume);
    col += acceptorCol * glowSoft(uv, acceptor, 0.015) * (0.4 + 0.3 * u_audioBeat);

    // Quantum bridge — appears when gap narrows, pulses with audio
    float bridgeEnergy = smoothstep(0.14, 0.06, gap) * (0.5 + 0.5 * u_audioVolume);
    if (bridgeEnergy > 0.01) {
        for (int i = 0; i < 110; i++) {
            float q = float(i) / 109.0;
            float x = mix(donor.x, acceptor.x, q);
            float amp = 0.014 * sin(3.14159 * q);
            float y = cy + sin(q * 6.28318 * 4.0 - t * 4.0 + u_audioBeat * 3.0) * amp;
            vec3 bridgeCol = scenePalette(0.4 + q * 0.3, PA, PB, PC, PD);
            col += bridgeCol * glowSoft(uv, vec2(x, y), 0.004) * bridgeEnergy;
        }
    }

    fragColor = vec4(col, 1.0);
}
