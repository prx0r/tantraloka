// mass.glsl — Mass comparison across particle types
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
#include "primitives.glsl"
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973, 0.969, 0.953));
    float bx0 = 0.48; float bx1 = 0.60;
    // Barrier
    vec2 bP = (uv - vec2(0.54, 0.44)) * iResolution;
    float dWall = sdRoundedBox(bP, vec2(0.06, 0.255) * iResolution, 8.0);
    col = mix(col, vec3(0.878,0.890,0.898), fill(dWall-2.0));
    col = mix(col, vec3(0.118,0.125,0.141), stroke(dWall, 2.0));
    // Particle rows
    struct Particle { float y; float trans; vec3 color; };
    Particle rows[4];
    rows[0] = Particle(0.38, 1.00, vec3(0.749,0.604,0.286)); // electron
    rows[1] = Particle(0.53, 0.56, vec3(0.263,0.616,0.706)); // proton
    rows[2] = Particle(0.68, 0.27, vec3(0.620,0.224,0.259)); // deuterium
    rows[3] = Particle(0.83, 0.06, vec3(0.337,0.349,0.369)); // heavy atom
    for (int i = 0; i < 4; i++) {
        float py = rows[i].y;
        float pct = rows[i].trans;
        vec3 pCol = rows[i].color;
        float progress = smoothstep(float(i)*0.11, min(1.0,float(i)*0.11+0.58), u);
        float waveX = progress * 0.34 + 0.28;
        // Wave approaching barrier
        for (int j = 0; j < int(62*progress)+1; j++) {
            float q = float(j) / 62.0;
            float x = 0.28 + q * (waveX - 0.28);
            float wy = py + sin(float(j)*0.46 - t*3.0) * 0.02;
            col += pCol * glowSoft(uv, vec2(x,wy), 0.003) * 0.35;
        }
        // Transmission beyond barrier
        float farLen = 0.22 * pct * progress;
        for (int j = 0; j < int(farLen * 200); j++) {
            float q = float(j) / (farLen * 200);
            float x = bx1 + 0.02 + q * farLen;
            col += pCol * glowSoft(uv, vec2(x,py), 0.004) * 0.3;
        }
    }
    fragColor = vec4(col, 1.0);
}
