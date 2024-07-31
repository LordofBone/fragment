from components.renderer_config import BaseConfig, ModelConfig, SurfaceConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    base_config = BaseConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/night_sky_egypt/",
        camera_position=(3.2, 3.2, 3.2),
        camera_target=(0, 0, 0),  # Center of the water surface
        up_vector=(0, 1, 0),  # Up vector
        fov=40,  # Field of view
        near_plane=0.1,
        far_plane=5000,
        light_positions=[(50.0, 200.0, 300.0)],  # Light positions
        light_colors=[(1.0, 1.0, 1.0)],  # Light colors
        light_strengths=[1.0],  # Light strengths
        anisotropy=16.0,
        auto_camera=True,
        height_factor=0.8,  # Height factor for camera calculation
        distance_factor=0.5,  # Distance factor for camera calculation
        msaa_level=8,
        culling=True,
        texture_lod_bias=1.0,  # Set texture LOD bias here
        env_map_lod_bias=1.5  # Set environment map LOD bias here
    )

    instance = RenderingInstance(base_config)
    instance.setup()

    model_config1 = ModelConfig(
        obj_path="models/pyramid.obj",
        texture_paths={
            'diffuse': 'textures/diffuse/crystal.png',
            'normal': 'textures/normal/crystal.png',
            'displacement': 'textures/displacement/crystal.png'
        },
        shader_name='embm',
        **base_config.unpack()
    )

    model_config2 = ModelConfig(
        obj_path="models/pyramid.obj",
        texture_paths={
            'diffuse': 'textures/diffuse/crystal.png',
            'normal': 'textures/normal/crystal.png',
            'displacement': 'textures/displacement/crystal.png'
        },
        shader_name='default',
        **base_config.unpack()
    )

    water_config = SurfaceConfig(
        shader_name='water',
        **base_config.unpack()
    )

    instance.add_renderer('model', **model_config1.unpack())
    instance.add_renderer('model', **model_config2.unpack())
    instance.add_renderer('water', **water_config.unpack())

    # Example transformations
    instance.scene.translate_renderer(0, (0, 1, 0))  # Translate first model
    instance.scene.rotate_renderer(0, 45, (0, 1, 0))  # Rotate first model
    instance.scene.scale_renderer(0, (1, 2, 1))  # Scale first model

    instance.scene.translate_renderer(1, (2, 0, 0))  # Translate second model
    instance.scene.set_auto_rotation(1, True)  # Enable auto-rotation for second model

    instance.run()
