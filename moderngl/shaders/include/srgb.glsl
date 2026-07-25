vec3 linear_to_srgb(vec3 c) {
    bvec3 lo = lessThanEqual(c, vec3(0.0031308));
    vec3 hi = 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055;
    vec3 lo2 = c * 12.92;
    return mix(hi, lo2, lo);
}

vec3 srgb_to_linear(vec3 c) {
    bvec3 lo = lessThanEqual(c, vec3(0.04045));
    vec3 hi = pow((c + 0.055) / 1.055, vec3(2.4));
    vec3 lo2 = c / 12.92;
    return mix(hi, lo2, lo);
}
