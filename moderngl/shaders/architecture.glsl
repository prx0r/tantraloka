// architecture.glsl — Body acts through truths it cannot state
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    // Four example domains
    struct Example { float x; vec3 color; };
    Example ex[4];
    ex[0] = Example(0.20, vec3(0.263,0.616,0.706)); // BIRD
    ex[1] = Example(0.40, vec3(0.263,0.616,0.706)); // CELL
    ex[2] = Example(0.60, vec3(0.263,0.616,0.706)); // EMBRYO
    ex[3] = Example(0.80, vec3(0.263,0.616,0.706)); // ENZYME
    float reveal = u * 4.0;
    for (int i = 0; i < 4; i++) {
        float q = clamp(reveal - float(i));
        float x = ex[i].x;
        float radius = 0.042 * ease_out(q);
        // Circle
        float dCirc = sdCircle((uv - vec2(x, 0.42)) * iResolution, radius * iResolution);
        col = mix(col, mix(vec3(0.973,0.969,0.953), ex[i].color, 0.14), fill(dCirc) * q);
        col = mix(col, ex[i].color, stroke(dCirc, 2.0) * q * 0.7);
    }
    fragColor = vec4(col, 1.0);
}
