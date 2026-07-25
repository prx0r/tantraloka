// rates.glsl — Structure selects possibility (rate bars)
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    int rows = 8;
    float reveal = u * float(rows);
    for (int i = 0; i < rows; i++) {
        float q = clamp(reveal - float(i));
        float y = 0.20 + float(i) * 0.075;
        float width = mix(0.05, 0.43, exp(-float(i) * 0.48)) * q;
        vec3 barColor = mix(vec3(0.620,0.224,0.259), vec3(0.282,0.529,0.396), float(i)/float(rows-1));
        for (int j = 0; j < int(width * 200); j++) {
            float lq = float(j) / (width * 200);
            float x = 0.30 + lq * width;
            col += barColor * glowSoft(uv, vec2(x, y), 0.005) * 0.5;
        }
    }
    fragColor = vec4(col, 1.0);
}
