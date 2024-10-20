from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/night_sky_egypt/",
        camera_positions=[
            (10.0, 10.0, 10.0, -30.0, 0.0),  # Initial position
            (6.0, 6.0, 6.0, -30.0, 0.0),  # Zoom in
            (4.0, 4.0, 10.0, -20.0, 15.0),  # Rotate around
            (0.0, 6.0, 6.0, -15.0, 15.0),  # Rotate around
            (4.0, 10.0, 4.0, -15.0, 15.0),  # Rotate around
            (6.0, 6.0, 6.0, -15.0, 15.0),  # Zoom out to origin
            (10.0, 10.0, 10.0, -30.0, 15.0),  # Back to initial
        ],
        lens_rotations=[0.0],
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.2,
        far_plane=5000,
        lights=[
            {"position": (50.0, 20.0, 30.0), "color": (1.0, 1.0, 1.0), "strength": 0.8},
        ],
        anisotropy=16.0,
        auto_camera=True,
        move_speed=0.1,
        loop=True,
        msaa_level=8,
        culling=True,
        texture_lod_bias=0.8,
        env_map_lod_bias=1.5,
        phong_shading=True,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the stretched pyramid model
    stretched_pyramid_config = base_config.add_model(
        obj_path="models/pyramid.obj",
        texture_paths={
            "diffuse": "textures/diffuse/crystal.png",
            "normal": "textures/normal/crystal.png",
            "displacement": "textures/displacement/crystal.png",
        },
        shader_names={
            "vertex": "standard",
            "fragment": "stealth",
        },
        opacity=0.0,
        distortion_strength=0.2,
        reflection_strength=0.0,
        planar_camera=True,
        planar_resolution=(1024, 1024),
        planar_fov=30,
        planar_camera_position_rotation=(3.0, 6.0, 0.0, 0.0, 0.0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        screen_facing_planar_texture=True,
    )

    # Define the configuration for the opaque pyramid model
    opaque_pyramid_config = base_config.add_model(
        obj_path="models/pyramid.obj",
        cubemap_folder="textures/cube/mountain_lake/",
        texture_paths={
            "diffuse": "textures/diffuse/metal_1.png",
            "normal": "textures/normal/metal_1.png",
            "displacement": "textures/displacement/metal_1.png",
        },
        shader_names={
            "vertex": "standard",
            "fragment": "stealth",
        },
        opacity=0.5,
        distortion_strength=0.2,
        reflection_strength=0.4,
        planar_camera=True,
        planar_resolution=(1024, 1024),
        planar_fov=30,
        planar_camera_position_rotation=(3.0, 6.0, 0.0, 0.0, 0.0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        screen_facing_planar_texture=True,
    )

    # Define the configuration for the rotating pyramid model
    rotating_pyramid_config = base_config.add_model(
        obj_path="models/pyramid.obj",
        texture_paths={
            "diffuse": "textures/diffuse/crystal.png",
            "normal": "textures/normal/crystal.png",
            "displacement": "textures/displacement/crystal.png",
        },
        shader_names={
            "vertex": "standard",
            "fragment": "embm",
        },
        rotation_speed=2000.0,
    )

    # Define the configuration for the water surface
    water_config = base_config.add_surface(
        shader_names={
            "vertex": "standard",
            "fragment": "water",
        },
        wave_speed=6.0,
        wave_amplitude=0.8,
        randomness=600.0,
        tex_coord_frequency=400.0,
        tex_coord_amplitude=0.010,
        width=50.0,
        height=50.0,
        phong_shading=False,
    )

    # Add a skybox renderer
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )
    instance.add_renderer("skybox", "skybox", **skybox_config)

    # Add the renderers to the instance
    instance.add_renderer("water_surface", "surface", **water_config)
    instance.add_renderer("model_stretched", "model", **stretched_pyramid_config)
    instance.add_renderer("model_rotating", "model", **rotating_pyramid_config)
    instance.add_renderer("model_opaque", "model", **opaque_pyramid_config)

    # Example transformations
    instance.scene_construct.translate_renderer("model_rotating", (0, 0, -3))  # Translate first model
    instance.scene_construct.rotate_renderer("model_rotating", 45, (0, 1, 0))  # Rotate first model
    instance.scene_construct.scale_renderer("model_rotating", (1.5, 2.5, 1.5))  # Scale first model
    instance.scene_construct.set_auto_rotation("model_rotating", True)  # Disable auto-rotation for second model

    instance.scene_construct.translate_renderer("model_stretched", (2, 0, 0))  # Translate second model
    instance.scene_construct.scale_renderer("model_stretched", (1.2, 1.2, 1.2))  # Scale second model

    instance.scene_construct.translate_renderer("model_opaque", (6, 0, -6))  # Translate second model
    instance.scene_construct.scale_renderer("model_opaque", (1.3, 1.3, 1.3))  # Scale second model
    instance.scene_construct.set_auto_rotation("model_opaque", False)  # Disable auto-rotation for second model

    # Run the rendering instance
    instance.run()
