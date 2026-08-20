#version 430 core
layout(location = 0) in vec4 in_pos_mass;
out float v_mass;
uniform mat4 u_view_proj;

void main() {
    gl_Position = u_view_proj * vec4(in_pos_mass.xyz, 1.0);
    float distance = gl_Position.w;
    gl_PointSize = clamp((in_pos_mass.w * 8.0) / distance, 2.0, 20.0); 
    v_mass = in_pos_mass.w;
}
