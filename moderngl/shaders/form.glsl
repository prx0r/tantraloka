// form.glsl — Triangle / Double-well potential
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float q = ease(u);
    // Triangle: three vertices
    vec2 a = vec2(0.50, 0.20);
    vec2 b = vec2(0.25, 0.68);
    vec2 c = vec2(0.75, 0.68);
    // Draw triangle edges
    vec2 edges[3] = vec2[](a, b, c);
    for (int i = 0; i < 3; i++) {
        float localQ = clamp(q * 3.0 - float(i));
        vec2 s = edges[i];
        vec2 e = edges[(i+1) % 3];
        vec2 mid = mix(s, e, localQ);
        for (int j = 0; j < 60; j++) {
            float lq = float(j) / 59.0 * localQ;
            vec2 lp = mix(s, e, lq);
            col += vec3(0.118,0.125,0.141) * glowSoft(uv, lp, 0.003) * 0.5;
        }
    }
    // Corner glows
    if (q > 0.72) {
        for (int i = 0; i < 3; i++) {
            col += vec3(0.749,0.604,0.286) * glowSoft(uv, edges[i], 0.012) * 0.5;
        }
    }
    fragColor = vec4(col, 1.0);
}
