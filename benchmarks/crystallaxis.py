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
    shadow_map_resolution=2048,
    particle_render_mode="vertex",
    vsync_enabled=True,
    sound_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Crystallaxis",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "magick_dome/"),
        camera_positions=[
            (4.5, 2.85, -1.4, 120.0, 55.0),
        ],
        fov=40,
        near_plane=0.1,
        far_plane=100,
        lights=[
            {"position": (6.85, 5.0, 4.0), "color": (0.85, 0.85, 0.85), "strength": 1.0},
        ],
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        auto_camera=False,
        msaa_level=msaa_level,
        culling=True,
        phong_shading=False,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the pyramid model
    pyramid_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "pyramid.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "crystal.png"),
            "normal": os.path.join(normal_textures_dir, "crystal.png"),
            "displacement": os.path.join(displacement_textures_dir, "crystal.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "embm",
        },
        rotation_speed=5000.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        env_map_strength=0.3,
        texture_lod_bias=1.0,
        env_map_lod_bias=0.75,
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    # Add the skybox and the pyramid to the scene
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("pyramid", "model", **pyramid_config)

    # Optionally enable auto-rotation for the pyramid
    instance.scene_construct.set_auto_rotation("pyramid", True)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
