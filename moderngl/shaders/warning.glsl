// warning.glsl — Do not turn mechanism into magic.
// Left: exact measurable science (MASS · WIDTH · COUPLING → MEASURABLE RATE EFFECT)
// Right: metaphorical overreach shattering (THOUGHT TUNNELS, QUANTUM INTENTION, SPIRITUAL JUMP)
// Audio: left panel glows with voice, right panel shatters on beat
#version 330 core
uniform vec2 iResolution; uniform float u; uniform float t;
uniform float u_audioVolume; uniform float u_audioBeat;
#include "primitives.glsl"
out vec4 fragColor;

const vec3 PA = vec3(0.5,0.5,0.5), PB = vec3(0.5,0.5,0.5), PC = vec3(1.0,1.0,1.0), PD = vec3(0.0,0.33,0.67);

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution;
    vec3 col = fieldBackground(uv, iResolution, t, vec3(0.973,0.969,0.953));

    // ── Left panel: exact mechanism ──
    // Box at (0.25, 0.44)
    vec2 lc = vec2(0.25, 0.44);
    vec2 lP = (uv - lc) * iResolution;
    float dBox = sdRoundedBox(lP, vec2(0.117, 0.086) * iResolution, 22.0);
    
    vec3 mechFill = mix(vec3(0.973,0.969,0.953), vec3(0.263,0.616,0.706), 0.10);
    vec3 mechEdge = vec3(0.263, 0.616, 0.706);
    col = mix(col, mechFill, fill(dBox) * 0.95);
    col = mix(col, mechEdge, stroke(dBox, 2.0) * 0.7);
    
    // Text-like glyph dots simulating "MASS · WIDTH · COUPLING" on top
    float textY = lc.y + 0.035;
    for (int i = 0; i < 18; i++) {
        float tx = lc.x - 0.085 + float(i) * 0.01;
        // Dots form letters — dense clusters per "word", gaps between
        float dotR = 0.0025;
        float dot = glowSoft(uv, vec2(tx, textY), dotR);
        col += mechEdge * dot * (0.5 + 0.4 * u_audioVolume);
    }
    // Lower line: "MEASURABLE RATE EFFECT"
    float textY2 = lc.y - 0.025;
    for (int i = 0; i < 22; i++) {
        float tx = lc.x - 0.090 + float(i) * 0.008;
        float dotR = 0.002;
        float dot = glowSoft(uv, vec2(tx, textY2), dotR);
        vec3 dotCol = scenePalette(0.1 * u_audioBeat, PA, PB, PC, PD);
        col += dotCol * dot * (0.3 + 0.3 * u_audioVolume);
    }
    // Inner glow pulses with voice
    col += mechEdge * glowSoft(uv, lc, 0.04) * u_audioVolume * 0.12;

    // ── Right panel: metaphorical overreach ──
    // Three lines that shatter: THOUGHT TUNNELS, QUANTUM INTENTION, SPIRITUAL JUMP
    float fade = smoothstep(0.35, 0.85, u);
    float shatter = 1.0 - fade;
    
    vec2 rc = vec2(0.75, 0.44);
    vec3 metaCol = vec3(0.620, 0.224, 0.259); // CRIMSON
    
    // Three text lines with increasing shatter
    for (int line = 0; line < 3; line++) {
        float ly = rc.y + 0.06 - float(line) * 0.055;
        float lineFade = shatter + u_audioBeat * (0.3 + float(line) * 0.2);
        if (lineFade < 0.01) continue;
        
        // Fragment the dots on beat — they scatter outward
        for (int i = 0; i < 15; i++) {
            float baseX = rc.x - 0.075 + float(i) * 0.01;
            float scatter = u_audioBeat * (0.005 + float(i) * 0.001);
            float rx = fract(sin(float(i) * 127.1 + float(line) * 311.7) * 43758.5453);
            float ry = fract(sin(float(i) * 269.5 + float(line) * 183.3) * 43758.5453);
            float fx = baseX + scatter * (rx - 0.5);
            float fy = ly + scatter * (ry - 0.5);
            float dot = glowSoft(uv, vec2(fx, fy), 0.003);
            col += metaCol * dot * lineFade * 0.6;
        }
    }
    
    // Crossing line through right panel
    float crossFade = shatter * 0.8;
    if (crossFade > 0.01) {
        for (int i = 0; i < 30; i++) {
            float q = float(i) / 29.0;
            float cx2 = mix(rc.x - 0.1, rc.x + 0.1, q);
            float cy2 = mix(rc.y - 0.08, rc.y + 0.08, q);
            col += metaCol * glowSoft(uv, vec2(cx2, cy2), 0.003) * crossFade * 0.5;
        }
    }

    fragColor = vec4(col, 1.0);
}
