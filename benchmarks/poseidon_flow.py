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
    sound_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Poseidon Flow",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "glacier/"),
        camera_positions=[(4.2, 150, 4.2, 45.0, -10.0)],
        lens_rotations=[
            0.0,
            0.4,
            -0.4,
            0.6,
            -0.5,
            0.4,
            -0.6,
            0.5,
            -0.4,
            0.8,
        ],
        auto_camera=True,
        move_speed=0.1,
        fov=40,
        near_plane=0.1,
        far_plane=5000,
        ambient_lighting_strength=0.72,
        ambient_lighting_color=(0.349, 0.647, 0.902),
        lights=[
            {
                "position": (8.0, -10.0, 0.0),
                "color": (0.949, 0.463, 0.247),
                "strength": 1.0,
                "orth_left": -90.0,
                "orth_right": 90.0,
                "orth_bottom": -90.0,
                "orth_top": 90,
            },
        ],
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        msaa_level=msaa_level,
        culling=True,
        lighting_mode="phong",
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
        legacy_roughness=32,
        wave_speed=6.0,
        wave_amplitude=0.8,
        randomness=550.0,
        tex_coord_frequency=800.0,
        tex_coord_amplitude=0.01,
        width=5000.0,
        height=5000.0,
        env_map_strength=0.65,
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    instance.add_renderer("skybox", "skybox", **skybox_config)

    # Add the water surface renderer to the instance with a specific name
    instance.add_renderer("water_surface", "surface", **water_config)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
