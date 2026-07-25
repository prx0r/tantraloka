// composite.glsl — Final post-processing: bloom composite + ACES tonemap + chromatic aberration
// This is applied as the last render pass before writing pixels.
#version 330 core

uniform sampler2D hdrScene;      // main HDR render
uniform sampler2D bloomBuffer;   // blurred bright pass (or 0 if no bloom)
uniform vec2 texelSize;
uniform float bloomIntensity;
uniform float aberrationStrength;

#include "primitives.glsl"

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy * texelSize;

    // Sample HDR scene
    vec3 color = texture(hdrScene, uv).rgb;

    // Add bloom if available
    vec3 bloom = texture(bloomBuffer, uv).rgb;
    color += bloom * bloomIntensity;

    // Chromatic aberration
    float ab = aberrationStrength * texelSize.x;
    color.r = texture(hdrScene, uv + vec2(ab, 0.0)).r;
    color.b = texture(hdrScene, uv - vec2(ab, 0.0)).b;

    // ACES filmic tonemap
    color = acesFilmic(color);

    // Subtle film grain
    float grain = snoise(uv * iResolution * 4.0 + u_time * 0.1) * 0.02;
    color += grain;

    fragColor = vec4(color, 1.0);
}
