float ease(float t) {
    return 0.5 - 0.5 * cos(3.14159265 * t);
}

float smoothstep(float a, float b, float x) {
    float q = clamp((x - a) / (b - a), 0.0, 1.0);
    return q * q * (3.0 - 2.0 * q);
}

float ease_out(float t) {
    return 1.0 - pow(1.0 - clamp(t, 0.0, 1.0), 3.0);
}

float pulse(float t, float hz, float phase) {
    return 0.5 + 0.5 * sin(6.2831853 * (hz * t + phase));
}

float lerp(float a, float b, float t) {
    return a + (b - a) * clamp(t, 0.0, 1.0);
}

vec3 lerp3(vec3 a, vec3 b, float t) {
    return a + (b - a) * clamp(t, 0.0, 1.0);
}
