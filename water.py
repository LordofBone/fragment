from components.renderer_config import BaseConfig, SurfaceConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    base_config = BaseConfig(
        window_size=(800, 600),
        cubemap_folder="textures/cube/night_sky_egypt/",
        camera_position=(3.2, 3.2, 3.2),
        camera_target=(0, 0, 0),  # Center of the surface
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

    water_config = SurfaceConfig(
        shader_name='water',
        wave_speed=10.0,
        wave_amplitude=0.1,
        randomness=0.5,
        tex_coord_frequency=100.0,
        tex_coord_amplitude=0.1,
        width=500.0,
        height=500.0,
        **base_config.unpack()
    )

    instance = RenderingInstance(base_config)
    instance.setup()

    instance.add_renderer('surface', **water_config.unpack())
    instance.run()
