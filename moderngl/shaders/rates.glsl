// rates.glsl — Structure selects. Audio heightens the rate bars.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.620,0.224,0.259);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    int rows = 8;
    float reveal = u * float(rows);
    float audioEnergy = 0.6 + 0.4 * u_audioVolume;

    for (int i = 0; i < rows; i++) {
        float q = clamp(reveal - float(i));
        float y = 0.20 + float(i) * 0.075;
        // Width modulated by audio — bars grow with sound
        float width = mix(0.05, 0.43, exp(-float(i) * 0.48)) * q * audioEnergy;

        vec3 barCol = scenePalette(float(i) / float(rows - 1) + u_audioBeat * 0.1, PA, PB, PC, PD);
        for (int j = 0; j < int(width * 200.0); j++) {
            float lq = float(j) / (width * 200.0);
            float x = 0.30 + lq * width;
            col += barCol * glowSoft(uv, vec2(x, y), 0.005) * 0.5;
        }
        // Bar tip glows on beat
        if (width > 0.01) {
            float tipX = 0.30 + width;
            col += barCol * glowSoft(uv, vec2(tipX, y), 0.008) * (0.3 + 0.5 * u_audioBeat);
        }
    }

    fragColor = vec4(col, 1.0);
}
