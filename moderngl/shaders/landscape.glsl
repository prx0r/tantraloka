// landscape.glsl — Energy landscape. Audio modulates molecule position and enzyme reshaping.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.263,0.416,0.557);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float base_y = 0.66;
    // Peak height modulated by audio — enzyme "flattens" the landscape on beat
    float peak = 0.34 * (1.0 - 0.15 * u_audioBeat);

    // Energy curve
    vec2 prev = vec2(0.0);
    for (int i = 0; i < 220; i++) {
        float q = float(i) / 219.0;
        float x = mix(0.12, 0.88, q);
        float gauss = exp(-pow((q - 0.5) / 0.13, 2.0));
        float y = base_y - peak * gauss;
        if (i > 0) {
            float d = sdSegment(uv, prev, vec2(x, y));
            vec3 lineCol = scenePalette(0.3 + q * 0.3, PA, PB, PC, PD);
            col = mix(col, lineCol, stroke(d * iResolution.x, 3.0) * 0.7);
        }
        prev = vec2(x, y);
    }

    // Molecular state — rolls toward barrier, audio pushes it
    float sq = ease(u) + u_audioBeat * 0.03;
    float sx = mix(0.12, 0.88, sq);
    float sy = base_y - peak * exp(-pow((sq - 0.5) / 0.13, 2.0));
    vec3 stateCol = scenePalette(0.5 + u_audioVolume * 0.3, PA, PB, PC, PD);
    col += stateCol * glowSoft(uv, vec2(sx, sy - 0.015), 0.015) * (0.4 + 0.3 * u_audioVolume);

    // Enzyme reshaping arcs — pulse with beat
    float arcEnergy = 0.3 + 0.5 * u_audioBeat;
    for (int side = -1; side <= 1; side += 2) {
        float gx = 0.50 + float(side) * 0.10;
        for (int j = 0; j < 60; j++) {
            float a = mix(3.49, 5.93, float(j) / 59.0);
            vec2 ap = vec2(gx + cos(a) * 0.08, 0.41 + sin(a) * 0.08);
            vec3 arcCol = scenePalette(0.7 + float(side) * 0.1, PA, PB, PC, PD);
            col += arcCol * glowSoft(uv, ap, 0.004) * arcEnergy;
        }
    }

    fragColor = vec4(col, 1.0);
}
