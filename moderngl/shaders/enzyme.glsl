// enzyme.glsl — Enzyme pocket breathing, narrowing the gap
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float cx = 0.50, cy = 0.44;
    float breathe = 0.5 + 0.5 * sin(t * 1.2);
    float closing = smoothstep(0.15, 0.72, u);
    float gap = mix(0.184, 0.061, closing) + breathe * 0.009;
    // Protein lobes (polygons approximated as SDF rounded composite shapes)
    // Left lobe
    vec2 lP = (uv - vec2(cx - gap*0.5 - 0.145, cy)) * iResolution;
    float dLobe = length(lP) - 120.0;
    col = mix(col, vec3(0.769,0.886,0.906), fill(dLobe) * 0.9);
    col = mix(col, vec3(0.263,0.616,0.706), stroke(dLobe, 3.0) * 0.8);
    // Right lobe
    vec2 rP = (uv - vec2(cx + gap*0.5 + 0.145, cy)) * iResolution;
    float dRobe = length(rP) - 120.0;
    col = mix(col, vec3(0.769,0.886,0.906), fill(dRobe) * 0.9);
    col = mix(col, vec3(0.263,0.616,0.706), stroke(dRobe, 3.0) * 0.8);
    // Donor and acceptor glow points
    vec2 donor = vec2(cx - gap*0.5, cy);
    vec2 acceptor = vec2(cx + gap*0.5, cy);
    float dGlow = glowSoft(uv, donor, 0.015);
    float aGlow = glowSoft(uv, acceptor, 0.015);
    col += vec3(0.749,0.604,0.286) * dGlow * 0.6;
    col += vec3(0.282,0.529,0.396) * aGlow * 0.6;
    // Quantum wave bridging the gap when narrow
    if (gap < 0.14) {
        float overlap = smoothstep(0.14, 0.06, gap);
        for (int i = 0; i < 110; i++) {
            float q = float(i) / 109.0;
            float x = mix(donor.x, acceptor.x, q);
            float amp = 0.014 * sin(3.14159 * q);
            float y = cy + sin(q * 6.28318 * 4.0 - t * 4.0) * amp;
            col += vec3(0.749,0.604,0.286) * glowSoft(uv, vec2(x,y), 0.004) * (0.4 + 0.3 * overlap);
        }
    }
    fragColor = vec4(col, 1.0);
}
