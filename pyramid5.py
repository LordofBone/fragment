from components.model_renderer import ModelRenderer
from components.render_window import RenderWindow

if __name__ == "__main__":
    window_size = (800, 600)
    obj_path = "models/pyramid.obj"
    vertex_shader_path = "shaders/embm/vertex.glsl"
    fragment_shader_path = "shaders/embm/fragment.glsl"
    texture_paths = {
        'diffuse': 'textures/diffuse/crystal.png',
        'normal': 'textures/normals/crystal.png',
        'height': 'textures/height/crystal.png'
    }
    cubemap_folder = 'textures/cube/night_sky_egypt/'
    lod_level = 7.5  # Default level of detail
    camera_position = (3.2, 3.2, 3.2)  # Camera position (initial)
    camera_target = (0, 0.75, 0)  # Camera target
    up_vector = (0, 1, 0)  # Up vector
    fov = 40  # Field of view (zoomed in)
    near_plane = 0.1  # Near plane
    far_plane = 100  # Far plane
    light_positions = [(3.0, 3.0, 3.0)]  # Light positions
    light_colors = [(1.0, 1.0, 1.0)]  # Light colors
    light_strengths = [0.8, 0.5]  # Light strengths
    anisotropy = 16.0  # Texture anisotropy
    rotation_speed = 2000.0  # Model rotation speed
    rotation_axis = (0, 3, 0)  # Model rotation axis
    apply_tone_mapping = False  # Apply tone mapping
    apply_gamma_correction = False  # Apply gamma correction
    model_width = 10.0  # Width of the model
    model_height = 10.0  # Height of the model
    auto_camera = False  # Enable auto camera calculation
    height_factor = 1.5  # Height factor for camera calculation
    distance_factor = 2.0  # Distance factor for camera calculation
    msaa_level = 8  # MSAA level (e.g., 2, 4, 8)

    # Create RenderWindow and initialize OpenGL context
    render_window = RenderWindow(window_size=window_size, title="Model Renderer", msaa_level=msaa_level)

    # Initialize ModelRenderer after OpenGL context is created
    model_renderer = ModelRenderer(
        obj_path=obj_path,
        vertex_shader_path=vertex_shader_path,
        fragment_shader_path=fragment_shader_path,
        texture_paths=texture_paths,
        cubemap_folder=cubemap_folder,
        window_size=window_size,
        lod_level=lod_level,
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
        rotation_speed=rotation_speed,
        rotation_axis=rotation_axis,
        apply_tone_mapping=apply_tone_mapping,
        apply_gamma_correction=apply_gamma_correction,
        width=model_width,
        height=model_height,
        auto_camera=auto_camera,
        height_factor=height_factor,
        distance_factor=distance_factor
    )

    render_window.mainloop(model_renderer.render)
