// architecture.glsl — 4 circles emerge. Audio paces emergence.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float xs[4] = float[](0.20, 0.40, 0.60, 0.80);
    float reveal = u * 4.0 + u_audioBeat * 0.5;
    float audioEnergy = 0.5 + 0.5 * u_audioVolume;

    for (int i = 0; i < 4; i++) {
        float q = clamp(reveal - float(i));
        float x = xs[i];
        float r = 0.042 * ease_out(q);

        float dCirc = sdCircle((uv - vec2(x, 0.42)) * iResolution, r * iResolution);
        vec3 circCol = scenePalette(0.15 + float(i) * 0.2 + u_audioVolume * 0.1, PA, PB, PC, PD);
        col = mix(col, mix(vec3(0.973,0.969,0.953), circCol, 0.14), fill(dCirc) * q);
        col = mix(col, circCol, stroke(dCirc, 2.0) * q * 0.7);

        // Inner glow pulses with audio
        if (q > 0.5) {
            col += circCol * glowSoft(uv, vec2(x, 0.42), r * 0.5) * (0.2 + 0.3 * u_audioBeat);
        }
    }

    fragColor = vec4(col, 1.0);
}
