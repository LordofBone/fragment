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
        window_title="Nebulon",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "mountain_lake/"),
        camera_positions=[
            (60.4, 60.4, 60.4, 35.0, -50.0),  # Starting position
            (50.0, 70.0, 50.0, 36.0, -45.0),  # Move up and to the side
            (40.0, 60.0, 70.0, 36.0, -45.0),  # Move further around, maintaining view
            (30.0, 50.0, 80.0, 36.0, -45.0),  # Continue to rotate around, higher
            (20.0, 40.0, 70.0, 36.0, -45.0),  # Move down, still rotating
            (10.0, 30.0, 60.0, 45.0, -60.0),  # Rotate towards the back
            (0.0, 20.0, 50.0, -30.0, -45.0),  # Directly behind, looking at the object
            (-10.0, 30.0, 40.0, -30.0, -40.0),  # Rotate back around
            (-20.0, 40.0, 30.0, -23.0, -38.0),  # Continue moving down
            (-30.0, 50.0, 20.0, -29.0, -45.0),  # Directly opposite the starting point
            (-40.0, 60.0, 30.0, -23.0, -47.0),  # Rotate around to the side
            (-50.0, 70.0, 40.0, -25.0, -48.0),  # Move back around towards the front
            (-60.4, 60.4, 60.4, -25.0, -48.0),  # Return to symmetrical position opposite start
            (60.4, 60.4, 60.4, 36.0, -45.0),  # Return to starting position
        ],
        lens_rotations=[
            0.0,  # Start with no roll
            3.0,
            7.0,
            10.0,
            12.0,
            8.0,
            3.0,
            -2.0,
            -5.0,
            -10.0,
            -5.0,
            -2.0,
            0.0,
            0.0  # End with no roll, back at start
        ],
        auto_camera=True,
        fov=90,
        near_plane=0.1,
        far_plane=1000,
        ambient_lighting_strength=0.60,
        ambient_lighting_color=(0.216, 0.871, 0.165),
        lights=[
            {
                "position": (50.0, 50.0, 50.0),
                "color": (0.992, 1.0, 0.769),
                "strength": 0.8,
                "orth_left": -100.0,
                "orth_right": 100.0,
                "orth_bottom": -100.0,
                "orth_top": 100.0,
            },
        ],
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        move_speed=0.2,
        msaa_level=msaa_level,
        culling=True,
        lighting_mode="pbr",
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the sphere model
    sphere_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "sphere.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "metal_1.png"),
            "normal": os.path.join(normal_textures_dir, "metal_1.png"),
            "displacement": os.path.join(displacement_textures_dir, "metal_1.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "stealth",
        },
        planar_fragment_view_threshold=-1.0,
        legacy_opacity=0.0,
        legacy_roughness=32,
        distortion_strength=0.2,
        reflection_strength=0.0,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        cubemap_folder=False,
        planar_camera=True,
        planar_fov=90,
        planar_camera_position_rotation=(0.0, 0.0, 0.0, 0.0, 0.0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        flip_planar_horizontally=True,
        flip_planar_vertically=True,
        use_planar_normal_distortion=True,
        screen_facing_planar_texture=True,
        texture_lod_bias=1.2,
        env_map_lod_bias=2.0,
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    # Add the renderers to the instance with specific names
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("sphere", "model", **sphere_config)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
