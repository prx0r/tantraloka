// psychology.glsl — Change the geometry. Audio steps the figure forward.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float cx = 0.55, cy = 0.45;
    float wall_x = 0.58;

    // Wall
    vec2 wP = (uv - vec2(wall_x, cy)) * iResolution;
    float dWall = sdRoundedBox(wP, vec2(0.043, 0.255) * iResolution, 12.0);
    vec3 wallCol = scenePalette(0.2 + u_audioBeat * 0.1, PA, PB, PC, PD);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall - 2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // Wall pulses with beat
    col += wallCol * stroke(dWall, 3.0) * u_audioBeat * 0.1;

    // Figure — audio pushes forward
    float progress = ease(u) + u_audioBeat * 0.05;
    progress = min(1.0, progress);
    float px = mix(0.18, wall_x - 0.065, progress);

    // Figure glow
    vec3 figureCol = scenePalette(0.6 + u_audioVolume * 0.2, PA, PB, PC, PD);

    // Head
    float dHead = sdCircle((uv - vec2(px, cy - 0.05)) * iResolution, 0.015 * iResolution.x);
    col = mix(col, figureCol, fill(dHead));
    col += figureCol * glowSoft(uv, vec2(px, cy - 0.05), 0.012) * 0.3;

    // Body line — pulses with audio
    float bodyEnergy = 0.3 + 0.3 * u_audioVolume;
    for (int i = 0; i < 30; i++) {
        float lq = float(i) / 29.0;
        float by = mix(cy - 0.035, cy + 0.035, lq);
        col += figureCol * glowSoft(uv, vec2(px, by), 0.003) * bodyEnergy;
    }

    // Step indicator on beat
    if (u_audioBeat > 0.5) {
        float stepX = px + 0.02;
        col += figureCol * glowSoft(uv, vec2(stepX, cy + 0.06), 0.006) * u_audioBeat * 0.4;
    }

    fragColor = vec4(col, 1.0);
}
