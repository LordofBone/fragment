from components.render_window import RenderWindow
from components.water_renderer import WaterRenderer

if __name__ == "__main__":
    window_size = (800, 600)
    vertex_shader_path = "shaders/water/vertex.glsl"
    fragment_shader_path = "shaders/water/fragment.glsl"
    cubemap_folder = "textures/cube/night_sky_egypt/"
    water_width = 500.0  # Width of the water surface
    water_height = 500.0  # Height of the water surface
    auto_camera = True  # Enable auto camera calculation
    height_factor = 0.8  # Height factor for camera calculation
    distance_factor = 0.5  # Distance factor for camera calculation

    # Initial camera parameters (will be updated if auto_camera is enabled)
    camera_position = (3.2, 3.2, 3.2)
    camera_target = (0, 0, 0)  # Center of the water surface
    up_vector = (0, 1, 0)  # Up vector
    fov = 40  # Field of view
    near_plane = 0.1  # Near plane
    far_plane = 5000  # Far plane
    light_positions = [(30.0, 30.0, 30.0)]  # Light positions
    light_colors = [(1.0, 1.0, 1.0)]  # Light colors
    light_strengths = [0.8]  # Light strengths
    anisotropy = 16.0  # Texture anisotropy
    wave_speed = 10.0  # Wave speed
    wave_amplitude = 0.1  # Wave amplitude
    randomness = 0.8  # Randomness factor
    tex_coord_frequency = 100.0  # Texture coordinate frequency
    tex_coord_amplitude = 0.1  # Texture coordinate amplitude

    # Create RenderWindow and initialize OpenGL context
    render_window = RenderWindow(window_size=window_size, title="Water Renderer")

    # Initialize WaterRenderer after OpenGL context is created
    water_renderer = WaterRenderer(
        vertex_shader_path,
        fragment_shader_path,
        cubemap_folder,
        width=water_width,
        height=water_height,
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
        wave_amplitude=wave_amplitude,
        randomness=randomness,
        tex_coord_frequency=tex_coord_frequency,
        tex_coord_amplitude=tex_coord_amplitude,
        auto_camera=auto_camera,
        height_factor=height_factor,
        distance_factor=distance_factor
    )

    render_window.mainloop(water_renderer.render)
