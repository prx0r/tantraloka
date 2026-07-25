// noise.glsl — Control without purity (noise organizing into structure)
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float organize = smoothstep(0.25, 0.85, u);
    // Scattering noise points that converge to a wave
    for (int i = 0; i < 120; i++) {
        float seed = float(i) * 0.618; // golden ratio step
        float rx = fract(seed + 0.1);
        float ry = fract(seed * 1.7 + 0.3);
        float x = mix(0.10, 0.90, rx);
        float targetY = 0.44 + sin(x * 6.28318 * 3.0) * 0.04;
        float yy = mix(ry * 0.6, targetY, organize);
        vec3 ptCol = (i % 5 == 0) ? vec3(0.749,0.604,0.286) : vec3(0.263,0.616,0.706);
        col += ptCol * glowSoft(uv, vec2(x, yy), 0.004) * 0.4;
    }
    // Emergent wave path
    if (organize > 0.35) {
        for (int i = 0; i < 120; i++) {
            float q = float(i) / 119.0 * organize;
            float x = 0.12 + q * 0.76;
            float y = 0.44 + sin(q * 6.28318 * 3.0) * 0.04;
            col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x, y), 0.003) * 0.4;
        }
    }
    fragColor = vec4(col, 1.0);
}
