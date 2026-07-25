// psychology.glsl — Change the geometry.
// Two modes shown sequentially: FORCE (arrows push into wall) → GEOMETRY (supports redirect path)
// Audio: footstep on beat, arrows pulse with voice intensity, supports glow with onset
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    float cy = 0.45;
    float wall_x = 0.58;

    // ── Wall ──
    vec2 wP = (uv - vec2(wall_x, cy)) * iResolution;
    float dWall = sdRoundedBox(wP, vec2(0.043, 0.255) * iResolution, 12.0);
    vec3 wallFill = vec3(0.878, 0.890, 0.898);
    vec3 wallEdge = vec3(0.118, 0.125, 0.141);
    col = mix(col, wallFill, fill(dWall - 2.0));
    col = mix(col, wallEdge, stroke(dWall, 2.0));
    // Wall shudders on impact
    float impact = smoothstep(0.45, 0.55, u) * u_audioBeat;
    col += wallEdge * stroke(dWall, 3.0) * impact * 0.15;

    // ── Phase 1: FORCE (u 0.0 - 0.5) ──
    // Figure pushes against wall, arrows show repeated force
    float forcePhase = min(1.0, u * 2.0);
    float px = mix(0.18, wall_x - 0.065, ease(forcePhase));
    
    // Figure glow
    vec3 figCol = scenePalette(0.6 + u_audioVolume * 0.2, PA, PB, PC, PD);
    float figEnergy = 0.4 + 0.4 * u_audioVolume;

    // Head
    float dHead = sdCircle((uv - vec2(px, cy - 0.05)) * iResolution, 0.015 * iResolution.x);
    col = mix(col, figCol, fill(dHead));
    col += figCol * glowSoft(uv, vec2(px, cy - 0.05), 0.012) * 0.3;

    // Body line
    for (int i = 0; i < 30; i++) {
        float lq = float(i) / 29.0;
        float by = mix(cy - 0.035, cy + 0.035, lq);
        col += figCol * glowSoft(uv, vec2(px, by), 0.003) * figEnergy;
    }

    // Force arrows (5 crimson arrows pushing left-to-right)
    float arrowPhase = smoothstep(0.1, 0.5, u);
    float arrowEnergy = arrowPhase * (0.5 + 0.5 * u_audioBeat);
    if (arrowEnergy > 0.01) {
        vec3 arrowCol = vec3(0.620, 0.224, 0.259); // CRIMSON
        for (int i = 0; i < 5; i++) {
            float ax = px - 0.06 - float(i) * 0.025 - u_audioVolume * 0.01;
            float ay = cy + (float(i) - 2.0) * 0.015;
            for (int j = 0; j < 15; j++) {
                float lq = float(j) / 14.0;
                float aPush = lq * arrowEnergy;
                vec2 ap = vec2(ax + aPush * 0.025, ay);
                col += arrowCol * glowSoft(uv, ap, 0.003) * arrowEnergy * 0.5;
            }
            // Arrowhead
            float aTip = ax + 0.025 * arrowEnergy;
            col += arrowCol * glowSoft(uv, vec2(aTip, ay), 0.005) * arrowEnergy * 0.8;
        }
    }

    // ── Phase 2: GEOMETRY (u 0.5 - 1.0) ──
    // Path redirects around wall via support structures
    float geomPhase = smoothstep(0.5, 1.0, u);
    if (geomPhase > 0.01) {
        vec3 geomCol = scenePalette(0.2 + u_audioVolume * 0.2, PA, PB, PC, PD);
        
        // Curved path around wall
        float pathEnergy = geomPhase * (0.5 + 0.5 * u_audioBeat);
        for (int i = 0; i < 50; i++) {
            float q = float(i) / 49.0 * geomPhase;
            float cx2 = mix(px, 0.85, q);
            float cy2 = mix(cy, 0.20, sin(q * 3.14159) * 0.8);
            // Path widens with audio
            float pathW = 0.003 + 0.002 * u_audioVolume;
            col += geomCol * glowSoft(uv, vec2(cx2, cy2), pathW) * pathEnergy * 0.7;
        }

        // Support nodes (3 gold dots at inflection points)
        float supports[3] = float[](0.30, 0.48, 0.73);
        float suppYs[3] = float[](cy + 0.05, 0.23, 0.24);
        for (int i = 0; i < 3; i++) {
            float sPhase = smoothstep(0.5 + float(i) * 0.1, 0.7 + float(i) * 0.1, u);
            if (sPhase > 0.01) {
                vec3 suppCol = scenePalette(0.7 + float(i) * 0.1 + u_audioBeat * 0.1, PA, PB, PC, PD);
                float sR = 0.007 + 0.004 * u_audioBeat;
                col += suppCol * glowSoft(uv, vec2(supports[i], suppYs[i]), sR) * sPhase * 0.8;
                col += suppCol * glowSoft(uv, vec2(supports[i], suppYs[i]), sR * 0.3) * sPhase * 1.2;
            }
        }
    }

    // Footstep indicator on strong beats
    if (u_audioBeat > 0.6) {
        float stepX = px + 0.015 * u_audioVolume;
        col += figCol * glowSoft(uv, vec2(stepX, cy + 0.055), 0.005) * u_audioBeat * 0.5;
    }

    fragColor = vec4(col, 1.0);
}
