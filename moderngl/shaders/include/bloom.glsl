// HDR bloom: extract brights, downsample, blur, upsample, add
// Applied as multi-pass post-processing in Python.
// This shader does the bright-pass extraction and blur.

uniform sampler2D hdrBuffer;
uniform vec2 texelSize;

// Gaussian blur weights (7-tap)
const float w[7] = float[](
    0.000489, 0.007972, 0.062539, 0.235206, 0.062539, 0.007972, 0.000489
);

vec4 gaussianBlur(sampler2D tex, vec2 uv, vec2 dir) {
    vec4 col = vec4(0.0);
    for (int i = -3; i <= 3; i++) {
        float weight = w[i + 3];
        vec2 offset = vec2(float(i)) * texelSize * dir;
        col += texture(tex, uv + offset) * weight;
    }
    return col;
}

vec3 extractBrights(vec3 color, float threshold) {
    float lum = dot(color, vec3(0.2126, 0.7152, 0.0722));
    float amount = max(0.0, lum - threshold) / max(lum, 0.0001);
    return color * amount;
}
