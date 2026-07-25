// =============================================================================
// bloom.glsl — HDR bloom pipeline (bright pass, blur, composite)
// =============================================================================
// Applied as multi-pass post-processing. This file contains the shared
// functions used by each bloom pass.

#ifndef BLOOM_GLSL
#define BLOOM_GLSL

uniform sampler2D hdrBuffer;
uniform vec2 texelSize;
uniform float bloomIntensity;
uniform float bloomThreshold;

// ---------------------------------------------------------------------------
// Bright-pass extraction
// ---------------------------------------------------------------------------
vec3 extractBrights(vec3 color) {
    float lum = dot(color, vec3(0.2126, 0.7152, 0.0722));
    float amount = max(0.0, lum - bloomThreshold) / max(lum, 0.0001);
    return color * amount;
}

// ---------------------------------------------------------------------------
// Gaussian blur (7-tap separable)
// ---------------------------------------------------------------------------
const float gaussWeights[7] = float[](
    0.006569, 0.055519, 0.202200, 0.329180, 0.202200, 0.055519, 0.006569
);

vec4 gaussianBlur(sampler2D tex, vec2 uv, vec2 dir) {
    vec4 col = vec4(0.0);
    for (int i = -3; i <= 3; i++) {
        vec2 offset = vec2(float(i)) * texelSize * dir;
        col += texture(tex, uv + offset) * gaussWeights[i + 3];
    }
    return col;
}

#endif
