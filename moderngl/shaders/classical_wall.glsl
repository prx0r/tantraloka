// classical_wall.glsl
// A proton reaches a classical barrier. Audio modulates pulse, spark, glow.
#version 330 core

uniform vec2 iResolution;
uniform float u;
uniform float t;
uniform float u_audioVolume;
uniform float u_audioBeat;

#include "primitives.glsl"

out vec4 fragColor;

// Cosine palette for this scene: warm golds, cool silvers, ink blacks
const vec3 PAL_A = vec3(0.5, 0.5, 0.5);
const vec3 PAL_B = vec3(0.5, 0.5, 0.5);
const vec3 PAL_C = vec3(1.0, 1.0, 1.0);
const vec3 PAL_D = vec3(0.0, 0.33, 0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec2 p = uv;

    // --- Background ---
    vec3 bg = vec3(0.973, 0.969, 0.953);
    vec3 col = fieldBackground(uv, iResolution, t, bg);

    // --- Wall (classical barrier) ---
    float cy = 0.45;
    float wall_cx = 0.56;
    float wall_hw = 0.06;
    float wall_top = 0.18, wall_bot = 0.69;

    vec2 wallP = (p - vec2(wall_cx, (wall_top + wall_bot) * 0.5)) * iResolution;
    vec2 wallB = vec2(wall_hw, (wall_bot - wall_top) * 0.5) * iResolution;
    float dWall = sdRoundedBox(wallP, wallB, 12.0);

    vec3 wallFill = vec3(0.878, 0.890, 0.898);
    vec3 wallEdge = vec3(0.118, 0.125, 0.141);
    col = mix(col, wallFill, fill(dWall - 2.0));
    col = mix(col, wallEdge, stroke(dWall, 2.0) * 0.7);

    // Wall edge pulses with audio beat
    col += scenePalette(u_audioBeat * 0.5, PAL_A, PAL_B, PAL_C, PAL_D) * stroke(dWall, 3.0) * u_audioBeat * 0.12;

    // --- Proton ---
    float stopX = wall_cx - wall_hw - 0.02;
    float approach = ease(min(1.0, u * 1.3));
    float px = mix(0.12, stopX, approach);
    float py = cy;

    // Proton radius pulses with voice + beat
    float radius = 0.025 + 0.012 * u_audioVolume + 0.008 * u_audioBeat;
    float intensity = 0.5 + 0.4 * u_audioVolume + 0.2 * u_audioBeat;

    // Core glow (additive — feeds bloom)
    vec3 gold = scenePalette(u * 0.1 + u_audioVolume * 0.3, PAL_A, PAL_B, PAL_C, PAL_D);
    col += gold * glowSoft(p, vec2(px, py), radius) * intensity * 0.7;

    // Tight core
    col += gold * glowSoft(p, vec2(px, py), radius * 0.3) * intensity * 1.2;

    // --- Impact sparks on word onsets ---
    float impact = smoothstep(0.65, 0.82, u);
    float sparkEnergy = impact * (0.4 + 0.6 * u_audioBeat);
    if (sparkEnergy > 0.01) {
        for (int i = 0; i < 6; i++) {
            float a = -0.9 + float(i) * 0.36 + u_audioBeat * 0.5;
            vec2 dir = vec2(cos(a), sin(a));
            float dist = 0.035 + 0.02 * u_audioVolume;
            vec2 sp = vec2(px, py) + dir * dist * sparkEnergy;
            vec3 sparkCol = scenePalette(0.7 + sparkEnergy * 0.3, PAL_A, PAL_B, PAL_C, PAL_D);
            col += sparkCol * glowSoft(p, sp, 0.006 + 0.004 * u_audioVolume) * sparkEnergy * 0.9;
        }
    }

    fragColor = vec4(col, 1.0);
}
