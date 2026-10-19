#version 430 core

uniform sampler2D u_grid;

uniform ivec2 u_grid_size;
uniform vec2 u_view_size;
uniform vec2 u_camera;

uniform float u_zoom;
uniform float u_cell_size;

uniform vec4 u_background;
uniform vec4 u_active_color;
uniform vec4 u_grid_line_color;
uniform vec4 u_outline_color;
uniform bool u_show_grid;

out vec4 frag_color;

void main() {
    vec2 screen_pos = gl_FragCoord.xy;
    vec2 world_pos = u_camera
        + (screen_pos - u_view_size * 0.5) / u_zoom;
    vec2 grid_pos = world_pos / u_cell_size;
    ivec2 cell = ivec2(floor(grid_pos));

    if (
        cell.x < 0 ||
        cell.y < 0 ||
        cell.x >= u_grid_size.x ||
        cell.y >= u_grid_size.y
    ) {
        frag_color = u_background;
        return;
    }

    vec2 uv = (vec2(cell) + 0.5) / vec2(u_grid_size);
    float concentration = clamp(texture(u_grid, uv).g, 0.0, 1.0);
    float intensity = smoothstep(0.01, 0.9, concentration);
    frag_color = mix(u_background, u_active_color, intensity);

    float cell_pixels = u_cell_size * u_zoom;
    if (u_show_grid && cell_pixels >= 4.0) {
        vec2 local_pos = fract(grid_pos) * cell_pixels;
        float edge_distance = min(
            min(local_pos.x, cell_pixels - local_pos.x),
            min(local_pos.y, cell_pixels - local_pos.y)
        );

        if (edge_distance < 1.0) {
            frag_color = u_grid_line_color;
        }
    }

    float boundary_distance = min(
        min(grid_pos.x, float(u_grid_size.x) - grid_pos.x),
        min(grid_pos.y, float(u_grid_size.y) - grid_pos.y)
    ) * cell_pixels;
    if (boundary_distance <= 0.5) {
        frag_color = u_outline_color;
    }
}
