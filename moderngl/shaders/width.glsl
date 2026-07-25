// width.glsl — Probability falls exponentially. Audio controls barrier breath + glow.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));
    float cy = 0.44;

    // Barrier width animated + audio modulates breath
    float widthPhase = ease(u);
    float bw = mix(0.08, 0.30, widthPhase) + u_audioVolume * 0.01;
    float x0 = 0.50 - bw * 0.5, x1 = 0.50 + bw * 0.5;

    vec2 bP = (uv - vec2(0.50, cy)) * iResolution;
    float dW = sdRoundedBox(bP, vec2(bw * 0.5, 0.25) * iResolution, 10.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dW - 2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dW, 2.0));

    // Incident wave
    float prob = exp(-5.4 * bw / 0.30);
    float waveEnergy = 0.3 + 0.2 * u_audioVolume;
    for (int i = 0; i < 120; i++) {
        float q = float(i) / 119.0;
        float x = mix(0.10, x0, q);
        float y = cy + sin(q * 6.28318 * 4.5 - t * 2.0) * 0.075;
        vec3 wc = scenePalette(0.2 + q * 0.1, PA, PB, PC, PD);
        col += wc * glowSoft(uv, vec2(x, y), 0.003) * waveEnergy;
    }

    // Decay inside
    for (int i = 0; i < 90; i++) {
        float q = float(i) / 89.0;
        float x = mix(x0, x1, q);
        float amp = 0.075 * exp(-5.0 * q);
        float y = cy + sin(q * 6.28318 * 2.0 - t * 2.0) * amp;
        vec3 wc = scenePalette(0.3 + q * 0.2, PA, PB, PC, PD);
        col += wc * glowSoft(uv, vec2(x, y), 0.003) * waveEnergy * 0.8;
    }

    // Output probability — pulses with beat
    float pulseRadius = 0.02 + 0.04 * prob + 0.01 * u_audioBeat;
    col += scenePalette(0.6 + prob * 0.4, PA, PB, PC, PD) * glowSoft(uv, vec2(0.78, cy), pulseRadius) * (0.2 + 0.6 * prob);

    fragColor = vec4(col, 1.0);
}
