from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/mountain_lake/",
        camera_positions=[
            (100.0, 100.0, 0.0),  # Front top view
            (60.0, 60.0, 60.0),  # 45 degrees top view
            (0.0, 100.0, 100.0),  # Side top view
            (-60.0, 60.0, 100.0),  # 135 degrees top view
            (-100.0, 100.0, 0.0),  # Back top view
            (-60.0, 60.0, -60.0),  # 225 degrees top view
            (0.0, 100.0, -100.0),  # Other side top view
            (60.0, 60.0, -60.0),  # 315 degrees top view
            (100.0, -100.0, 0.0),  # Front bottom view
            (60.0, -60.0, 60.0),  # 45 degrees bottom view
            (0.0, -100.0, 100.0),  # Side bottom view
            (-60.0, -60.0, 100.0),  # 135 degrees bottom view
            (-100.0, -100.0, 0.0),  # Back bottom view
            (-60.0, -60.0, -60.0),  # 225 degrees bottom view
            (0.0, -100.0, -100.0),  # Other side bottom view
            (60.0, -60.0, -60.0),  # 315 degrees bottom view
            (100.0, 100.0, 0.0),  # Return to front top view
        ],
        auto_camera=True,
        camera_target=(0, 0.75, 0),
        up_vector=(0, 1, 0),
        fov=90,
        near_plane=0.1,
        far_plane=1000,
        lights=[
            {"position": (50.0, 50.0, 50.0), "color": (1.0, 1.0, 1.0), "strength": 0.8},
        ],
        anisotropy=16.0,
        move_speed=0.2,
        msaa_level=8,
        culling=True,
        texture_lod_bias=1.0,
        env_map_lod_bias=2.0,
        phong_shading=True,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the sphere model
    sphere_config = base_config.add_model(
        obj_path="models/sphere.obj",
        texture_paths={
            "diffuse": "textures/diffuse/metal_1.png",
            "normal": "textures/normal/metal_1.png",
            "displacement": "textures/displacement/metal_1.png",
        },
        shader_names=("standard", "stealth"),
        opacity=0.0,
        distortion_strength=0.1,
        reflection_strength=0.5,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        cubemap_folder=False,
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names=("skybox", "skybox"),
    )

    # Add the renderers to the instance with specific names
    instance.add_renderer("skybox", order=0, renderer_type="skybox", **skybox_config)
    instance.add_renderer("sphere", order=1, renderer_type="model", **sphere_config)

    # Run the rendering instance
    instance.run()
