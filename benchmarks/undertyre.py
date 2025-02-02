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
        window_title="Undertyre",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "garage_2/"),
        camera_positions=[(6.4, 0.0, 6.4, -270.0, 0.0)],
        lens_rotations=[0.0],
        fov=40,
        near_plane=0.1,
        far_plane=50.0,
        ambient_lighting_strength=0.45,
        ambient_lighting_color=(1.0, 0.996, 0.753),
        lights=[
            {
                "position": (6.0, 0.0, 0.0),
                "color": (1.0, 1.0, 1.0),
                "strength": 1.0,
                "orth_left": -25.0,
                "orth_right": 25.0,
                "orth_bottom": -25.0,
                "orth_top": 25,
            }
        ],
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        auto_camera=False,
        msaa_level=msaa_level,
        culling=True,
        lighting_mode="pbr",
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()
    instance.base_config = base_config  # Attribute defined outside __init__

    # Define the configuration for the tyre model
    tyre_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "tyre.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "rubber.png"),
            "normal": os.path.join(normal_textures_dir, "rubber.png"),
            "displacement": os.path.join(displacement_textures_dir, "rubber.png"),
        },
        shader_names={
            "vertex": "parallax_mapping",
            "fragment": "parallax_mapping",
        },
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        legacy_roughness=32,
        invert_displacement_map=True,
        pom_height_scale=0.016,
        pom_min_steps=128,
        pom_max_steps=512,
        pom_eye_offset_scale=1.0,
        pom_max_depth_clamp=0.99,
        pom_max_forward_offset=1.0,
        pom_enable_frag_depth_adjustment=False,
        texture_lod_bias=0.4,
        env_map_lod_bias=0.0,
        env_map_strength=0.025,
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    # Add the tyre renderer to the instance with a specific name
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("tyre", "model", **tyre_config)

    # Translate the tyre model to a specific position, to get best view of skybox
    instance.scene_construct.translate_renderer("tyre", (-5.0, 0.0, 6.5))

    # First, tilt the tyre by 45° about the X‐axis (manual/initial rotation)
    instance.scene_construct.rotate_renderer_euler("tyre", (0.0, 0.0, 0.0))

    # Then, enable auto-rotation on multiple axes (for example, spin about the Y axis and also roll about the X axis)
    instance.scene_construct.set_auto_rotations("tyre",
                                                rotations=[((0.0, 1.0, 0.0), 14000.0), ((0.0, 0.0, 1.0), 8000.0)])
    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
