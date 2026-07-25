// psychology.glsl — Change the geometry (force vs support)
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float cx = 0.55, cy = 0.45;
    float wall_x = 0.58;
    // Wall
    vec2 wP = (uv - vec2(wall_x, cy)) * iResolution;
    float dWall = sdRoundedBox(wP, vec2(0.043, 0.255) * iResolution, 12.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall-2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // Person figure approaching wall
    float progress = ease(u);
    float person_x = mix(0.18, wall_x - 0.065, progress);
    // Simple stick figure (ellipses + lines)
    // Head
    float dHead = sdCircle((uv - vec2(person_x, cy - 0.05)) * iResolution, 0.015 * iResolution.x);
    col = mix(col, vec3(0.118,0.125,0.141), fill(dHead));
    // Body
    for (int i = 0; i < 30; i++) {
        float lq = float(i)/29.0;
        float by = mix(cy - 0.035, cy + 0.035, lq);
        col += vec3(0.118,0.125,0.141) * glowSoft(uv, vec2(person_x, by), 0.003) * 0.5;
    }
    fragColor = vec4(col, 1.0);
}
