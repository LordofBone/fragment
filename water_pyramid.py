from components.renderer_config import BaseConfig, ModelConfig, WaterConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    shaders = {
        'default': {
            'vertex': "shaders/embm/vertex.glsl",
            'fragment': "shaders/embm/fragment.glsl"
        },
        'water': {
            'vertex': "shaders/water/vertex.glsl",
            'fragment': "shaders/water/fragment.glsl"
        }
    }

    base_config = BaseConfig(
        window_size=(800, 600),
        shaders=shaders,
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
        msaa_level=8
    )

    instance = RenderingInstance(base_config)
    instance.setup()

    model_config = ModelConfig(
        obj_path="models/pyramid.obj",
        texture_paths={
            'diffuse': 'textures/diffuse/crystal.png',
            'normal': 'textures/normal/crystal.png',
            'displacement': 'textures/displacement/crystal.png'
        },
        shader_name='default',
        **base_config.unpack()
    )

    water_config = WaterConfig(
        shader_name='water',
        **base_config.unpack()
    )

    instance.add_renderer('model', **model_config.unpack())
    instance.add_renderer('water', **water_config.unpack())
    instance.run()
