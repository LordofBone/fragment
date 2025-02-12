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
    lighting_mode="pbr",
    shadow_map_resolution=2048,
    particle_render_mode="vertex",
    vsync_enabled=True,
    sound_enabled=True,
    fullscreen=False,
):
    """
    Run the benchmark for the Treadlock configuration.
    """
    # ------------------------------------------------------------------------------
    # Initialize the base renderer configuration
    # ------------------------------------------------------------------------------
    base_config = RendererConfig(
        window_title="Treadlock",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "garage_2/"),
        # Single camera position (x, y, z, yaw, pitch)
        camera_positions=[(6.4, 0.0, 6.4, -270.0, 0.0)],
        lens_rotations=[0.0],
        fov=40,
        near_plane=0.1,
        far_plane=50.0,
        ambient_lighting_strength=0.2,
        ambient_lighting_color=(1.0, 0.984, 0.753),
        lights=[
            {
                "position": (5.0, 9.0, -5.4),
                "color": (0.996, 0.996, 0.996),
                "strength": 0.994,
                "orth_left": -10.0,
                "orth_right": 10.0,
                "orth_bottom": -10.0,
                "orth_top": 10.0,
            }
        ],
        lighting_mode=lighting_mode,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        shadow_map_resolution=shadow_map_resolution,
        shadow_strength=7.0,
        anisotropy=anisotropy,
        auto_camera=False,
        msaa_level=msaa_level,
        culling=True,
    )

    # ------------------------------------------------------------------------------
    # Create and set up the rendering instance
    # ------------------------------------------------------------------------------
    instance = RenderingInstance(base_config)
    instance.setup()
    instance.base_config = base_config  # Set attribute outside __init__

    # ------------------------------------------------------------------------------
    # Define the tyre model configuration
    # ------------------------------------------------------------------------------
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

    # ------------------------------------------------------------------------------
    # Define the skybox configuration
    # ------------------------------------------------------------------------------
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    # ------------------------------------------------------------------------------
    # Add renderers to the instance and configure scene transforms
    # ------------------------------------------------------------------------------
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("tyre", "model", **tyre_config)
    instance.scene_construct.translate_renderer("tyre", (-5.0, 0.0, 6.5))
    # Apply manual rotation (tilt) followed by auto-rotations on multiple axes.
    instance.scene_construct.rotate_renderer_euler("tyre", (0.0, 0.0, 0.0))
    instance.scene_construct.set_auto_rotations(
        "tyre",
        rotations=[((0.0, 1.0, 0.0), 14000.0), ((0.0, 0.0, 1.0), 8000.0)]
    )

    # ------------------------------------------------------------------------------
    # Run the rendering instance
    # ------------------------------------------------------------------------------
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
