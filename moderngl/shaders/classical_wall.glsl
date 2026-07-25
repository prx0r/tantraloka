// classical_wall.glsl — A proton reaches a classical barrier
// Audio-reactive: proton pulse = voice rhythm, spark intensity = onset strength
#version 330 core

uniform vec2 iResolution;
uniform float u;
uniform float t;
uniform float u_audioVolume;  // 0-1 RMS energy envelope
uniform float u_audioBeat;    // 0-1 onset/beat likelihood

#include "primitives.glsl"

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec2 p = vec2(uv.x, uv.y);

    // Background — audio subtly modulates noise field energy
    vec3 bg = vec3(0.973, 0.969, 0.953);
    vec3 col = fieldBackground(uv, iResolution, t + u_audioVolume * 0.3, bg);

    // Wall
    float cy = 0.45;
    float wall_x = 0.56;
    float wall_w = 0.12;
    float wall_top = 0.18;
    float wall_bottom = 0.69;
    float wall_cx = wall_x;
    float wall_cy = (wall_top + wall_bottom) * 0.5;
    vec2 wall_half = vec2(wall_w * 0.5, (wall_bottom - wall_top) * 0.5);
    vec2 wall_p = (p - vec2(wall_cx, wall_cy)) * iResolution;
    vec2 wall_b = wall_half * iResolution;
    float wall_r = 12.0;
    float dWall = sdRoundedBox(wall_p, wall_b, wall_r);

    vec3 WALL_FILL = vec3(0.878, 0.890, 0.898);
    vec3 WALL_OUTLINE = vec3(0.118, 0.125, 0.141);
    col = mix(col, WALL_FILL, fill(dWall - 2.0));
    col = mix(col, WALL_OUTLINE, stroke(dWall, 2.0));

    // Proton — pulse amplitude follows voice volume
    float stopX = wall_x - wall_w * 0.5 - 0.02;
    float approach = ease(min(1.0, u * 1.3));
    float proton_x = mix(0.12, stopX, approach);
    float proton_y = cy;

    // Proton radius pulses with audio volume + beat
    float pulseRadius = 0.025 + 0.015 * u_audioVolume + 0.010 * u_audioBeat;
    float protonGlow = glowSoft(p, vec2(proton_x, proton_y), pulseRadius);
    col += vec3(0.749, 0.604, 0.286) * protonGlow * (0.5 + 0.5 * u_audioVolume);

    // Impact sparks — intensity follows onset strength
    float impact = smoothstep(0.65, 0.82, u);
    float sparkIntensity = impact * (0.5 + 0.5 * u_audioBeat);
    if (sparkIntensity > 0.01) {
        for (int i = 0; i < 5; i++) {
            float angle = -0.8 + float(i) * 0.4;
            vec2 sparkDir = vec2(cos(angle), sin(angle));
            vec2 sparkPos = vec2(proton_x, proton_y) + sparkDir * 0.04 * sparkIntensity;
            float spark = glowSoft(p, sparkPos, 0.008);
            col += vec3(0.620, 0.224, 0.259) * spark * sparkIntensity * 0.7;
        }
    }

    // Wall outline pulses with beat
    col += vec3(0.749, 0.604, 0.286) * stroke(dWall, 3.0) * u_audioBeat * 0.15;

    fragColor = vec4(col, 1.0);
}
