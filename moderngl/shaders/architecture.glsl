// architecture.glsl — The body acts through truths it cannot state.
// Four domains: BIRD (spin chemistry), CELL (voltage), EMBRYO (geometry), ENZYME (tunnelling)
// Each circle has unique visual character matching its domain.
// Audio: emergence pace follows voice, inner life pulses with beat.
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

// Each domain gets its own palette feel
const vec3 PA0 = vec3(0.5,0.5,0.5), PB0 = vec3(0.5,0.5,0.5), PC0 = vec3(1.0,1.0,1.0), PD0 = vec3(0.0,0.33,0.67); // BIRD
const vec3 PA1 = vec3(0.5,0.5,0.5), PB1 = vec3(0.5,0.5,0.5), PC1 = vec3(1.0,1.0,0.5), PD1 = vec3(0.33,0.0,0.0); // CELL
const vec3 PA2 = vec3(0.5,0.5,0.5), PB2 = vec3(0.5,0.5,0.5), PC2 = vec3(0.5,1.0,1.0), PD2 = vec3(0.0,0.33,0.67); // EMBRYO
const vec3 PA3 = vec3(0.5,0.5,0.5), PB3 = vec3(0.5,0.5,0.5), PC3 = vec3(1.0,0.5,0.5), PD3 = vec3(0.0,0.67,0.33); // ENZYME

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    struct Domain { float x; vec3 a,b,c,d; char label[20]; char sub[30]; };
    // Labels as glyph-dot patterns per domain (visual shorthand since text is SDF-only)
    float xs[4] = float[](0.20, 0.40, 0.60, 0.80);
    vec3 palA[4] = vec3[](PA0, PA1, PA2, PA3);
    vec3 palB[4] = vec3[](PB0, PB1, PB2, PB3);
    vec3 palC[4] = vec3[](PC0, PC1, PC2, PC3);
    vec3 palD[4] = vec3[](PD0, PD1, PD2, PD3);

    float reveal = u * 4.0 + u_audioBeat * 0.4;
    float audioEnergy = 0.5 + 0.5 * u_audioVolume;

    for (int i = 0; i < 4; i++) {
        float q = clamp(reveal - float(i));
        float x = xs[i];
        float r = 0.042 * ease_out(q);
        vec2 center = vec2(x, 0.42);

        // Circle outline
        float dCirc = sdCircle((uv - center) * iResolution, r * iResolution);
        vec3 circCol = scenePalette(0.15 + float(i) * 0.2 + u_audioVolume * 0.1,
                                     palA[i], palB[i], palC[i], palD[i]);
        col = mix(col, mix(vec3(0.973,0.969,0.953), circCol, 0.14), fill(dCirc) * q);
        col = mix(col, circCol, stroke(dCirc, 2.0) * q * 0.7);

        // Domain-specific inner life
        if (q > 0.3) {
            // BIRD: magnetic field lines (spin chemistry)
            if (i == 0) {
                for (int j = 0; j < 12; j++) {
                    float a = float(j) * 0.5236 + t * 0.5;
                    float innerR = r * 0.5 + 0.005 * sin(a * 3.0 + u_audioBeat * 4.0);
                    vec2 fp = center + vec2(cos(a), sin(a)) * innerR;
                    col += circCol * glowSoft(uv, fp, 0.004) * (0.2 + 0.3 * u_audioVolume);
                }
            }
            // CELL: voltage ring
            else if (i == 1) {
                float vR = r * (0.4 + 0.2 * pulse(t, 1.0, 0.0));
                col += circCol * glowSoft(uv, center, vR) * (0.15 + 0.2 * u_audioBeat);
            }
            // EMBRYO: geometry lattice
            else if (i == 2) {
                for (int j = 0; j < 6; j++) {
                    float a = float(j) * 1.047 + t * 0.3;
                    vec2 gp = center + vec2(cos(a), sin(a)) * r * 0.5;
                    vec2 gp2 = center + vec2(cos(a + 0.5236), sin(a + 0.5236)) * r * 0.5;
                    for (int k = 0; k < 10; k++) {
                        float lq = float(k) / 9.0;
                        vec2 lp = mix(gp, gp2, lq);
                        col += circCol * glowSoft(uv, lp, 0.002) * 0.2;
                    }
                }
            }
            // ENZYME: tunnelling dot
            else if (i == 3) {
                float tR = r * 0.3 + 0.003 * u_audioBeat;
                col += circCol * glowSoft(uv, center + vec2(0.01, 0.0), tR) * (0.3 + 0.4 * u_audioBeat);
                col += circCol * glowSoft(uv, center - vec2(0.01, 0.0), tR) * (0.2 + 0.2 * u_audioVolume);
            }
        }
    }

    fragColor = vec4(col, 1.0);
}
