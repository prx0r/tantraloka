// landscape.glsl — Energy landscape (solution vs enzyme)
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float base_y = 0.66; float peak = 0.34;
    // Energy landscape curve
    vec2 prevP = vec2(0.0);
    for (int i = 0; i < 220; i++) {
        float q = float(i) / 219.0;
        float x = mix(0.12, 0.88, q);
        float gauss = exp(-pow((q-0.5)/0.13, 2.0));
        float y = base_y - peak * gauss;
        if (i > 0) {
            float d = sdSegment(uv, prevP, vec2(x, y));
            col = mix(col, vec3(0.118,0.125,0.141), stroke(d * iResolution.x, 3.0) * 0.7);
        }
        prevP = vec2(x, y);
    }
    // Molecular state rolling toward barrier
    float state_q = ease(u);
    float state_x = mix(0.12, 0.88, state_q);
    float state_y = base_y - peak * exp(-pow((state_q-0.5)/0.13, 2.0));
    float stateGlow = glowSoft(uv, vec2(state_x, state_y - 0.015), 0.015);
    col += vec3(0.263,0.616,0.706) * stateGlow * 0.6;
    // Enzyme "arms" reshaping landscape
    // (simple arc indicators)
    if (peak < 0.30) {
        for (int side = -1; side <= 1; side += 2) {
            float gx = 0.50 + float(side) * 0.10;
            for (int j = 0; j < 60; j++) {
                float a = mix(3.49, 5.93, float(j)/59.0);
                vec2 ap = vec2(gx + cos(a)*0.08, 0.41 + sin(a)*0.08);
                col += vec3(0.749,0.604,0.286) * glowSoft(uv, ap, 0.004) * 0.3;
            }
        }
    }
    fragColor = vec4(col, 1.0);
}
