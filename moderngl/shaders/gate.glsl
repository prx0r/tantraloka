// gate.glsl — Proton relay. Audio pushes the relay along the chain.
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

    // Membrane layers
    vec3 membCol = vec3(0.769, 0.886, 0.906);
    vec3 membEdge = vec3(0.263, 0.616, 0.706);
    for (int layer = 0; layer < 2; layer++) {
        float ry = layer == 0 ? 0.24 : 0.66;
        for (int i = 0; i < 22; i++) {
            float x = mix(0.12, 0.88, float(i) / 21.0);
            col += membCol * glowSoft(uv, vec2(x, ry), 0.008) * 0.5;
            col = mix(col, membEdge, stroke(sdCircle((uv - vec2(x, ry)) * iResolution, 8.0), 2.0) * 0.5);
        }
    }

    // Water chain nodes
    vec2 nodes[10];
    float audioEnergy = 0.6 + 0.4 * u_audioVolume;
    for (int i = 0; i < 10; i++) {
        float nx = mix(0.22, 0.78, float(i) / 9.0);
        float ny = y + sin(float(i) * 0.9) * 0.025;
        nodes[i] = vec2(nx, ny);
        vec3 nodeCol = scenePalette(0.1 + float(i) * 0.08, PA, PB, PC, PD);
        col += nodeCol * glowSoft(uv, nodes[i], 0.01) * 0.4;
        col = mix(col, vec3(0.220, 0.298, 0.486), stroke(sdCircle((uv - nodes[i]) * iResolution, 11.0), 2.0) * 0.6);
    }

    // Relay — audio pushes the proton faster
    float relayQ = ease(u) + u_audioBeat * 0.08;
    int idx = int(min(9.0, relayQ * 9.0));
    if (relayQ > 0.0) {
        vec3 relayCol = scenePalette(0.5 + u_audioVolume * 0.3, PA, PB, PC, PD);
        for (int i = 0; i < 9; i++) {
            if (relayQ > float(i) / 9.0) {
                for (int j = 0; j < 20; j++) {
                    float lq = float(j) / 19.0;
                    vec2 lp = mix(nodes[i], nodes[i + 1], lq);
                    col += relayCol * glowSoft(uv, lp, 0.004) * 0.5 * audioEnergy;
                }
            }
        }
        // Proton pulse on beat
        col += relayCol * glowSoft(uv, nodes[idx], 0.015) * (0.4 + 0.3 * u_audioVolume);
        col += relayCol * glowSoft(uv, nodes[idx], 0.006) * (0.5 + 0.5 * u_audioBeat);
    }

    fragColor = vec4(col, 1.0);
}
