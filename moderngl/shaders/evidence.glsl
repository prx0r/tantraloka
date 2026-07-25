// evidence.glsl — Multiple converging lines of evidence
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    vec2 center = vec2(0.50, 0.43);
    // Central glow
    float cGlow = glowSoft(uv, center, 0.02);
    col += vec3(0.749,0.604,0.286) * cGlow * 0.5;
    // Evidence terms radiating outward
    struct Term { vec2 offset; vec3 color; };
    Term terms[5];
    terms[0] = Term(vec2(-0.172, -0.132), vec3(0.749,0.604,0.286)); // MASS
    terms[1] = Term(vec2( 0.172, -0.132), vec3(0.263,0.616,0.706)); // DISTANCE
    terms[2] = Term(vec2(-0.180,  0.146), vec3(0.220,0.298,0.486)); // ELECTROSTATICS
    terms[3] = Term(vec2( 0.180,  0.146), vec3(0.282,0.529,0.396)); // PROTEIN MOTION
    terms[4] = Term(vec2( 0.000,  0.250), vec3(0.620,0.224,0.259)); // BARRIER SHAPE
    float reveal = u * 5.0;
    for (int i = 0; i < 5; i++) {
        float q = clamp(reveal - float(i));
        vec2 end = center + terms[i].offset * ease_out(q);
        // Connecting line
        for (int j = 0; j < 50; j++) {
            float lq = float(j) / 49.0 * q;
            vec2 lp = mix(center, end, lq);
            col += terms[i].color * glowSoft(uv, lp, 0.003) * 0.3;
        }
        // Term glow
        float tGlow = glowSoft(uv, end, 0.012);
        col += terms[i].color * tGlow * q * 0.5;
    }
    fragColor = vec4(col, 1.0);
}
