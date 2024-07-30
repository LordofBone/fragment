from components.renderer_config import BaseConfig, ModelConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    base_config = BaseConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/night_sky_egypt/",
        camera_position=(150.2, 150.2, 150.2),
        camera_target=(0, 0.75, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.1,
        far_plane=1000,
        light_positions=[(50.0, 50.0, 50.0)],
        light_colors=[(1.0, 1.0, 1.0)],
        light_strengths=[0.8, 0.5],
        anisotropy=16.0,
        auto_camera=False,
        height_factor=1.5,
        distance_factor=2.0,
        msaa_level=8,
        culling=False,
        texture_lod_bias=1.0,  # Set texture LOD bias here
        env_map_lod_bias=2.0  # Set environment map LOD bias here
    )

    model_config = ModelConfig(
        obj_path="models/sphere.obj",
        texture_paths={
            'diffuse': 'textures/diffuse/crystal.png',
            'normal': 'textures/normal/crystal.png',
            'displacement': 'textures/displacement/crystal.png'
        },
        shader_name='stealth',
        rotation_speed=2000.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        width=10.0,
        height=10.0,
        **base_config.unpack()
    )

    instance = RenderingInstance(base_config)
    instance.setup()

    instance.add_renderer('model', **model_config.unpack())
    instance.run()
