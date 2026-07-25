// gate.glsl — Proton relay and gating
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float y = 0.45;
    // Membrane layers
    for (int layer = 0; layer < 2; layer++) {
        float row_y = layer == 0 ? 0.24 : 0.66;
        for (int i = 0; i < 22; i++) {
            float x = mix(0.12, 0.88, float(i) / 21.0);
            col += vec3(0.769,0.886,0.906) * glowSoft(uv, vec2(x, row_y), 0.008) * 0.5;
            col = mix(col, vec3(0.263,0.616,0.706), stroke(sdCircle((uv-vec2(x,row_y))*iResolution, 8.0), 2.0) * 0.5);
        }
    }
    // Water chain nodes
    vec2 nodes[10];
    for (int i = 0; i < 10; i++) {
        nodes[i] = vec2(mix(0.22, 0.78, float(i)/9.0), y + sin(float(i)*0.9)*0.025);
        col += vec3(0.973,0.969,0.953) * glowSoft(uv, nodes[i], 0.012) * 0.8;
        col = mix(col, vec3(0.220,0.298,0.486), stroke(sdCircle((uv-nodes[i])*iResolution, 11.0), 2.0) * 0.6);
    }
    // Proton relay along chain
    float q = ease(u);
    int idx = int(min(9.0, q * 9.0));
    if (q > 0.0) {
        for (int i = 0; i < 9; i++) {
            if (q > float(i)/9.0) {
                vec2 a = nodes[i];
                vec2 b = nodes[i+1];
                for (int j = 0; j < 20; j++) {
                    float lq = float(j)/19.0;
                    vec2 lp = mix(a, b, lq);
                    col += vec3(0.749,0.604,0.286) * glowSoft(uv, lp, 0.004) * 0.5;
                }
            }
        }
    }
    col += vec3(0.749,0.604,0.286) * glowSoft(uv, nodes[idx], 0.015) * 0.6;
    fragColor = vec4(col, 1.0);
}
