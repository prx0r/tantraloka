// evolution.glsl — Selection operating across generations
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float y = 0.45; int gens = 7;
    for (int i = 0; i < gens; i++) {
        float q = clamp(u * float(gens) - float(i));
        float x = mix(0.12, 0.88, float(i) / float(gens-1));
        float improvement = float(i) / float(gens-1);
        float gap = mix(0.094, 0.041, improvement);
        // Arc pair (protein-like)
        for (int j = 0; j < 40; j++) {
            float a = mix(3.316, 6.108, float(j)/39.0);
            vec2 ap = vec2(x + cos(a)*0.03, y - 0.06 + sin(a)*0.03);
            col += vec3(0.263,0.616,0.706) * glowSoft(uv, ap, 0.003) * q * 0.4;
        }
        // Gold connecting line
        float lineLen = q;
        for (int j = 0; j < int(lineLen * 30); j++) {
            float lq = float(j) / (lineLen * 30);
            float lx = mix(x - gap*0.5, x + gap*0.5, lq);
            col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(lx, y), 0.003) * q * 0.5;
        }
        // Arrow to next generation
        if (i < gens - 1 && q > 0.5) {
            float nx = mix(0.12, 0.88, float(i+1) / float(gens-1));
            vec2 arrowDir = vec2(nx - x, 0.0);
            for (int j = 0; j < 20; j++) {
                float lq = float(j) / 19.0;
                vec2 ap = vec2(x + 0.038, y + 0.167) + arrowDir * lq * 0.5;
                col += vec3(0.337,0.349,0.369) * glowSoft(uv, ap, 0.002) * 0.3;
            }
        }
    }
    fragColor = vec4(col, 1.0);
}
