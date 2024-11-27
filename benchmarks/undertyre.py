import os

from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance
from config.path_config import (
    cubemaps_dir,
    diffuse_textures_dir,
    displacement_textures_dir,
    models_dir,
    normal_textures_dir,
)


def run_benchmark(
    stats_queue=None,
    stop_event=None,
    resolution=(800, 600),
        msaa_level=4,
    anisotropy=16,
    particle_render_mode="vertex",
        shadow_map_resolution=1024,
    vsync_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Undertyre",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "mountain_lake/"),
        camera_positions=[
            (6.4, 6.4, 6.4, -45.0, 36.0),
        ],
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.1,
        far_plane=50.0,
        lights=[
            {"position": (2.85, 2.0, 1.0), "color": (0.55, 0.55, 0.55), "strength": 1.0},
        ],
        anisotropy=anisotropy,
        auto_camera=False,
        msaa_level=msaa_level,
        culling=True,
        texture_lod_bias=0.4,
        env_map_lod_bias=0.0,
        phong_shading=True,
        shadow_map_resolution=shadow_map_resolution,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()
    instance.base_config = base_config  # Attribute defined outside __init__

    # Define the configuration for the tyre model
    tyre_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "tyre.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "rubber_1.png"),
            "normal": os.path.join(normal_textures_dir, "rubber_1.png"),
            "displacement": os.path.join(displacement_textures_dir, "rubber_1.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "rubber",
        },
        rotation_speed=2000.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
    )

    # Add the tyre renderer to the instance with a specific name
    instance.add_renderer("tyre", "model", **tyre_config)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
