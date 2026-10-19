#version 430 core

uniform sampler2D u_velocity;
uniform sampler2D u_dye;
uniform sampler2D u_obstacles;
uniform ivec2 u_grid_size;
uniform vec2 u_view_size;
uniform vec2 u_camera;
uniform float u_zoom;
uniform float u_cell_size;
uniform vec4 u_background;
uniform vec4 u_cool_color;
uniform vec4 u_mid_color;
uniform vec4 u_warm_color;
uniform vec4 u_hot_color;
uniform vec4 u_outline_color;

out vec4 frag_color;

void main() {
    vec2 screen_pos = gl_FragCoord.xy;
    vec2 world_pos = u_camera
        + (screen_pos - u_view_size * 0.5) / u_zoom;
    vec2 grid_pos = world_pos / u_cell_size;
    ivec2 cell = ivec2(floor(grid_pos));
    if (
        cell.x < 0 || cell.y < 0
        || cell.x >= u_grid_size.x || cell.y >= u_grid_size.y
    ) {
        frag_color = u_background;
        return;
    }

    vec2 uv = (vec2(cell) + 0.5) / vec2(u_grid_size);
    if (texelFetch(u_obstacles, cell, 0).r > 0.5) {
        frag_color = u_background;
    } else {
        vec2 velocity = texture(u_velocity, uv).rg;
        float dye = clamp(texture(u_dye, uv).r, 0.0, 1.0);
        float activity = clamp(dye * 0.72 + length(velocity) * 0.11, 0.0, 1.0);
        vec3 color = mix(
            u_cool_color.rgb,
            u_mid_color.rgb,
            smoothstep(0.02, 0.48, activity)
        );
        color = mix(
            color,
            u_warm_color.rgb,
            smoothstep(0.42, 0.78, activity)
        );
        color = mix(
            color,
            u_hot_color.rgb,
            smoothstep(0.78, 1.0, activity)
        );
        frag_color = vec4(color, 1.0);
    }
    float cell_pixels = u_cell_size * u_zoom;
    float boundary_distance = min(
        min(grid_pos.x, float(u_grid_size.x) - grid_pos.x),
        min(grid_pos.y, float(u_grid_size.y) - grid_pos.y)
    ) * cell_pixels;
    if (boundary_distance <= 0.5) {
        frag_color = u_outline_color;
    }
}
