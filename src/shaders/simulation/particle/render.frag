#version 430 core
in float v_mass;
out vec4 fragColor;

void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (length(coord) > 0.5) discard;
    float intensity = clamp(v_mass / 50.0, 0.2, 1.0);
    fragColor = vec4(intensity, 0.3, 1.0 - intensity, 0.8);
}
