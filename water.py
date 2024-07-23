from components.render_window import RenderWindow
from components.water_renderer import WaterRenderer

if __name__ == "__main__":
    window_size = (800, 600)
    vertex_shader_path = "shaders/water/vertex.glsl"
    fragment_shader_path = "shaders/water/fragment.glsl"
    cubemap_folder = "textures/cube/night_sky_egypt/"
    camera_position = (3.2, 3.2, 3.2)  # Camera position
    camera_target = (0, 0.75, 0)  # Camera target
    up_vector = (0, 1, 0)  # Up vector
    fov = 40  # Field of view
    near_plane = 0.1  # Near plane
    far_plane = 100  # Far plane
    light_positions = [(3.0, 3.0, 3.0)]  # Light positions
    light_colors = [(1.0, 1.0, 1.0)]  # Light colors
    light_strengths = [0.8, 0.5]  # Light strengths
    anisotropy = 16.0  # Texture anisotropy
    wave_speed = 0.03  # Wave speed
    wave_amplitude = 0.1  # Wave amplitude

    # Create RenderWindow and initialize OpenGL context
    render_window = RenderWindow(window_size=window_size, title="Water Renderer")

    # Initialize WaterRenderer after OpenGL context is created
    water_renderer = WaterRenderer(
        vertex_shader_path,
        fragment_shader_path,
        cubemap_folder,
        window_size=window_size,
        camera_position=camera_position,
        camera_target=camera_target,
        up_vector=up_vector,
        fov=fov,
        near_plane=near_plane,
        far_plane=far_plane,
        light_positions=light_positions,
        light_colors=light_colors,
        light_strengths=light_strengths,
        anisotropy=anisotropy,
        wave_speed=wave_speed,
        wave_amplitude=wave_amplitude
    )

    render_window.mainloop(water_renderer.render)
