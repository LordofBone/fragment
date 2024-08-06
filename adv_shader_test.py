from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance

if __name__ == "__main__":
    base_config = RendererConfig(
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
        msaa_level=8,
        culling=True,
        texture_lod_bias=0.2,
        env_map_lod_bias=1.5,
    )

    instance = RenderingInstance(base_config)
    instance.setup()

    water_config = base_config.add_surface(
        shader_name='adv_water',
        wave_speed=6.0,
        wave_amplitude=0.8,
        randomness=400.0,
        tex_coord_frequency=400.0,
        tex_coord_amplitude=0.085,
        width=50.0,
        height=50.0,
    )

    instance.add_renderer('surface', **water_config)
    instance.run()
