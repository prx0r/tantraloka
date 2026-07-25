// tunnelling.glsl — Wavefunction penetrates barrier. Audio modulates wave energy and detection.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));
    float cy = 0.44, bx0 = 0.46, bx1 = 0.62;

    vec2 bP = (uv - vec2(0.54, cy)) * iResolution;
    float dW = sdRoundedBox(bP, vec2(0.08, 0.24) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dW - 2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dW, 2.0) * 0.7);

    // Wave — amplitude modulated by audio volume
    float waveAmp = 0.085 * (0.7 + 0.3 * u_audioVolume);
    float reveal = ease(u);
    for (int i = 0; i < 240; i++) {
        float q = float(i) / 239.0; if (q > reveal) break;
        float x = mix(0.10, 0.90, q);
        float amp = waveAmp;
        if (x > bx0 && x <= bx1) amp *= exp(-5.8 * (x - bx0) / max(0.001, bx1 - bx0));
        else if (x > bx1) amp *= exp(-5.8) * 3.3;
        float y = cy + sin(q * 6.28318 * 8.0 - t * 3.0 + u_audioBeat * 2.0) * amp;
        vec3 waveCol = scenePalette(0.1 + q * 0.3 + u_audioBeat * 0.2, PA, PB, PC, PD);
        col += waveCol * glowSoft(uv, vec2(x, y), 0.003) * (0.3 + 0.2 * u_audioVolume);
    }

    // Detection flash synced with audio onset
    float detect = smoothstep(0.66, 0.90, u);
    float detectAmp = detect * (0.5 + 0.5 * u_audioBeat);
    if (detectAmp > 0.01) {
        float dx = mix(bx1 + 0.02, 0.80, detect);
        vec3 detCol = scenePalette(0.8 + detectAmp * 0.2, PA, PB, PC, PD);
        col += detCol * glowSoft(uv, vec2(dx, cy), 0.015 + 0.01 * u_audioBeat) * detectAmp * 0.6;
        col += detCol * glowSoft(uv, vec2(dx, cy), 0.005) * detectAmp * 1.2;
    }

    fragColor = vec4(col, 1.0);
}
