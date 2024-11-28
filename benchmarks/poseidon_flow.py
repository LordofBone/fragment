import os

from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance
from config.path_config import cubemaps_dir


def run_benchmark(
    stats_queue=None,
    stop_event=None,
    resolution=(800, 600),
        msaa_level=4,
    anisotropy=16,
        shadow_map_resolution=2048,
        particle_render_mode="vertex",
    vsync_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Poseidon Flow",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "mountain_lake/"),
        camera_positions=[(4.2, 4.2, 4.2, -60.0, 55.0)],
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.1,
        far_plane=5000,
        lights=[
            {"position": (5.0, 10.0, 0.0), "color": (1.0, 1.0, 1.0), "strength": 0.8},
        ],
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        auto_camera=True,
        msaa_level=msaa_level,
        culling=True,
        phong_shading=True,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the water surface
    water_config = base_config.add_surface(
        shader_names={
            "vertex": "standard",
            "fragment": "water",
        },
        wave_speed=6.0,
        wave_amplitude=0.8,
        randomness=400.0,
        tex_coord_frequency=400.0,
        tex_coord_amplitude=0.085,
        width=50.0,
        height=50.0,
    )

    # Add the water surface renderer to the instance with a specific name
    instance.add_renderer("water_surface", "surface", **water_config)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
