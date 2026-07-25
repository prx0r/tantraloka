// classical_wall.glsl — A proton reaches a classical barrier
#version 330 core

uniform vec2 iResolution;
uniform float u;
uniform float t;

#include "primitives.glsl"

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec2 p = vec2(uv.x, uv.y);  // 0..1 normalized coords
    
    // Background
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    
    // Wall parameters (fractions of resolution)
    float cy = 0.45;
    float wall_x = 0.56;
    float wall_w = 0.12;
    float wall_top = 0.18;
    float wall_bottom = 0.69;
    float wall_cx = wall_x;
    float wall_cy = (wall_top + wall_bottom) * 0.5;
    vec2 wall_half = vec2(wall_w * 0.5, (wall_bottom - wall_top) * 0.5);
    
    // Wall SDF (rounded rectangle)
    vec2 wall_p = (p - vec2(wall_cx, wall_cy)) * iResolution;
    vec2 wall_b = wall_half * iResolution;
    float wall_r = 12.0;
    float dWall = sdRoundedBox(wall_p, wall_b, wall_r);
    
    // Draw wall
    vec3 WALL_FILL = vec3(0.878, 0.890, 0.898); // PALE_SILVER
    vec3 WALL_OUTLINE = vec3(0.118, 0.125, 0.141); // INK
    col = mix(col, WALL_FILL, fill(dWall - 2.0));
    col = mix(col, WALL_OUTLINE, stroke(dWall, 2.0));
    
    // Proton movement
    float proton_x = 0.12;
    float proton_y = cy;
    
    // Check mode via uniform or default to "stop"
    // Default behavior: stop at wall
    float stopX = wall_x - wall_w * 0.5 - 0.02;
    float approach = ease(min(1.0, u * 1.3));
    proton_x = mix(0.12, stopX, approach);
    
    // Proton glow (additive)
    float protonGlow = glowSoft(p, vec2(proton_x, proton_y), 0.025);
    col += vec3(0.749, 0.604, 0.286) * protonGlow * 0.6; // GOLD additive
    
    // Impact sparks at wall
    float impact = smoothstep(0.65, 0.82, u);
    if (impact > 0.0) {
        for (int i = 0; i < 5; i++) {
            float angle = -0.8 + float(i) * 0.4;
            vec2 sparkDir = vec2(cos(angle), sin(angle));
            vec2 sparkPos = vec2(proton_x, proton_y) + sparkDir * 0.04 * impact;
            float spark = glowSoft(p, sparkPos, 0.008);
            col += vec3(0.620, 0.224, 0.259) * spark * impact * 0.7; // CRIMSON additive
        }
    }
    
    fragColor = vec4(col, 1.0);
}
