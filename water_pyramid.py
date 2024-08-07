from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/night_sky_egypt/",
        camera_positions=[
            (10.0, 10.0, 10.0),  # Initial position
            (6.0, 6.0, 6.0),  # Zoom in
            (4.0, 4.0, 10.0),  # Rotate around
            (0.0, 6.0, 6.0),  # Rotate around
            (4.0, 10.0, 4.0),  # Rotate around
            (6.0, 6.0, 6.0),  # Zoom out to origin
            (10.0, 10.0, 10.0),  # Back to initial
        ],
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.1,
        far_plane=5000,
        light_positions=[(50.0, 20.0, 30.0)],
        light_colors=[(1.0, 1.0, 1.0)],
        light_strengths=[0.8],
        anisotropy=16.0,
        auto_camera=True,
        move_speed=0.2,
        loop=True,
        msaa_level=8,
        culling=True,
        texture_lod_bias=0.8,
        env_map_lod_bias=1.5,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the stretched pyramid model
    stretched_pyramid_config = base_config.add_model(
        obj_path="models/pyramid.obj",
        texture_paths={
            'diffuse': 'textures/diffuse/crystal.png',
            'normal': 'textures/normal/crystal.png',
            'displacement': 'textures/displacement/crystal.png'
        },
        shader_names=('standard', 'embm'),
    )

    # Define the configuration for the rotating pyramid model
    rotating_pyramid_config = base_config.add_model(
        obj_path="models/pyramid.obj",
        texture_paths={
            'diffuse': 'textures/diffuse/crystal.png',
            'normal': 'textures/normal/crystal.png',
            'displacement': 'textures/displacement/crystal.png'
        },
        shader_names=('standard', 'normal_mapping'),  # Pass vertex and fragment shader names as a tuple
        rotation_speed=2000.0,
    )

    # Define the configuration for the water surface
    water_config = base_config.add_surface(
        shader_names=('standard', 'water'),  # Pass vertex and fragment shader names as a tuple
        wave_speed=6.0,
        wave_amplitude=0.8,
        randomness=600.0,
        tex_coord_frequency=400.0,
        tex_coord_amplitude=0.010,
        width=50.0,
        height=50.0,
    )

    # Add the renderers to the instance
    instance.add_renderer('model', **stretched_pyramid_config)
    instance.add_renderer('model', **rotating_pyramid_config)
    instance.add_renderer('surface', **water_config)

    # Example transformations
    instance.scene_construct.translate_renderer(0, (-3, -3, 0))  # Translate first model
    instance.scene_construct.rotate_renderer(0, 45, (0, 1, 0))  # Rotate first model
    instance.scene_construct.scale_renderer(0, (1, 2, 1))  # Scale first model

    instance.scene_construct.translate_renderer(1, (2, 0, 0))  # Translate second model
    instance.scene_construct.scale_renderer(1, (1, 2, 1))  # Scale second model
    instance.scene_construct.set_auto_rotation(1, True)  # Enable auto-rotation for second model

    # Run the rendering instance
    instance.run()
