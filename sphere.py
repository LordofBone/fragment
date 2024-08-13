from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/night_sky_egypt/",
        camera_positions=[(75, 75, 75)],
        camera_target=(0, 0.75, 0),
        up_vector=(0, 1, 0),
        fov=90,
        near_plane=0.1,
        far_plane=1000,
        light_positions=[(50.0, 50.0, 50.0)],
        light_colors=[(1.0, 1.0, 1.0)],
        light_strengths=[0.8, 0.5],
        anisotropy=16.0,
        auto_camera=False,
        msaa_level=8,
        culling=True,
        texture_lod_bias=1.0,
        env_map_lod_bias=2.0,
        phong_shading=False,
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
        shader_names=("standard", "embm"),
        rotation_speed=2000.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names=("skybox", "skybox"),
    )

    # Add the renderers to the instance with specific names
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("sphere", "model", **sphere_config)

    # Run the rendering instance
    instance.run()
