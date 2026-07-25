// warning.glsl — Don't turn mechanism into magic
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    // Left panel: exact mechanism
    vec2 lP = (uv - vec2(0.25, 0.44)) * iResolution;
    float dBox = sdRoundedBox(lP, vec2(0.117, 0.086) * iResolution, 22.0);
    col = mix(col, mix(vec3(0.973,0.969,0.953), vec3(0.263,0.616,0.706), 0.10), fill(dBox) * 0.95);
    col = mix(col, vec3(0.263,0.616,0.706), stroke(dBox, 2.0) * 0.7);
    // Right panel: metaphorical overreach (fading out)
    float fade = smoothstep(0.35, 0.85, u);
    vec2 rP = (uv - vec2(0.75, 0.44)) * iResolution;
    float dBox2 = sdRoundedBox(rP, vec2(0.105, 0.086) * iResolution, 22.0);
    col = mix(col, vec3(0.620,0.224,0.259) * (1.0 - fade), stroke(dBox2, 3.0) * (1.0 - fade) * 0.8);
    fragColor = vec4(col, 1.0);
}
