// warning.glsl — Exact mechanism vs metaphor. Audio fades the overreach.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    // Left panel: exact mechanism — stable, grows with audio
    vec2 lP = (uv - vec2(0.25, 0.44)) * iResolution;
    float dBox = sdRoundedBox(lP, vec2(0.117, 0.086) * iResolution, 22.0);
    vec3 mechCol = scenePalette(0.3 + u_audioVolume * 0.2, PA, PB, PC, PD);
    col = mix(col, mix(vec3(0.973,0.969,0.953), mechCol, 0.10), fill(dBox) * 0.95);
    col = mix(col, mechCol, stroke(dBox, 2.0) * 0.7);
    // Inner glow pulses with audio
    col += mechCol * glowSoft(uv, vec2(0.25, 0.44), 0.04) * u_audioVolume * 0.15;

    // Right panel: metaphorical overreach — fades on audio, shatters on beat
    float fade = smoothstep(0.35, 0.85, u) + u_audioBeat * 0.3;
    fade = min(1.0, fade);
    vec2 rP = (uv - vec2(0.75, 0.44)) * iResolution;
    float dBox2 = sdRoundedBox(rP, vec2(0.105, 0.086) * iResolution, 22.0);
    vec3 metaCol = vec3(0.620, 0.224, 0.259);
    // Shatter effect on beat
    float shatter = 1.0 - fade + u_audioBeat * 0.2;
    col = mix(col, metaCol * shatter, stroke(dBox2, 3.0) * shatter * 0.8);

    fragColor = vec4(col, 1.0);
}
