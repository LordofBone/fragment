import os

from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance
from config.path_config import (
    audio_dir,
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
    Run the benchmark for the Shimmer configuration.
    """
    # ------------------------------------------------------------------------------
    # Initialize the base renderer configuration
    # ------------------------------------------------------------------------------
    base_config = RendererConfig(
        window_title="Shimmer",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=82,
        cubemap_folder=os.path.join(cubemaps_dir, "night_sky_egypt/"),
        # Define multiple camera positions (x, y, z, yaw, pitch)
        camera_positions=[
            (10.0, 10.0, 10.0, 5.0, -10.0),
            (8.0, 8.0, 8.0, 10.0, -10.0),
            (6.0, 6.0, 6.0, 10.0, -15.0),
            (4.0, 4.0, 10.0, 10.0, -5.0),
            (2.0, 6.0, 8.0, 5.0, -20.0),
            (0.0, 1.0, 12.0, 0.0, 15.0),
            (-14.0, 1.0, 10.0, -50.0, 15.0),
            (0.0, 2.0, 5.0, -30.0, 15.0),
            (8.0, 3.0, 7.0, 27.0, 4.0),
            (10.0, 10.0, 10.0, 30.0, 6.0),
            (15.0, 5.0, 8.0, 50.0, 6.0),
        ],
        # Lens rotations corresponding to each camera keyframe
        lens_rotations=[
            0.0,
            2.0,
            5.0,
            8.0,
            10.0,
            6.0,
            3.0,
            1.0,
            -2.0,
            -4.0,
            0.0,
        ],
        fov=40,
        near_plane=0.2,
        far_plane=100,
        ambient_lighting_strength=0.34,
        ambient_lighting_color=(0.78, 0.541, 0.0),
        lights=[
            {
                "position": (8.85, 7.0, 22.0),
                "color": (0.757, 0.902, 1),
                "strength": 1.0,
                "orth_left": -25.0,
                "orth_right": 25.0,
                "orth_bottom": -25.0,
                "orth_top": 25,
            }
        ],
        planar_fragment_view_threshold=-1.0,
        lighting_mode=lighting_mode,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        shadow_map_resolution=shadow_map_resolution,
        shadow_strength=1.0,
        anisotropy=anisotropy,
        auto_camera=True,
        move_speed=0.1,
        loop=True,
        msaa_level=msaa_level,
        culling=True,
        sound_enabled=sound_enabled,
        background_audio=os.path.join(audio_dir, "music/water_pyramid.wav"),
        audio_delay=0.0,
        audio_loop=True,
    )

    # ------------------------------------------------------------------------------
    # Create and set up the rendering instance
    # ------------------------------------------------------------------------------
    instance = RenderingInstance(base_config)
    instance.setup()

    # ------------------------------------------------------------------------------
    # Define the stretched pyramid model configuration
    # ------------------------------------------------------------------------------
    stretched_pyramid_config = base_config.add_model(
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
        legacy_opacity=0.0,
        legacy_roughness=32,
        distortion_strength=0.2,
        refraction_strength=0.3,
        planar_camera=True,
        planar_fov=30,
        planar_resolution=(1024, 1024),
        planar_camera_position_rotation=(0.0, 2.0, 5.0, 0.0, -10.0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        flip_planar_horizontally=False,
        flip_planar_vertically=False,
        use_planar_normal_distortion=True,
        screen_facing_planar_texture=True,
        texture_lod_bias=0.8,
        env_map_lod_bias=1.5,
        pbr_extension_overrides={
            "transmission": (1.0, 1.0, 1.0),
        },
    )

    # ------------------------------------------------------------------------------
    # Define the opaque pyramid model configuration
    # ------------------------------------------------------------------------------
    opaque_pyramid_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "pyramid.obj"),
        cubemap_folder="textures/cube/mountain_lake/",
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "metal_1.png"),
            "normal": os.path.join(normal_textures_dir, "metal_1.png"),
            "displacement": os.path.join(displacement_textures_dir, "metal_1.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "embm",
        },
        legacy_opacity=0.5,
        legacy_roughness=32,
        distortion_strength=0.2,
        refraction_strength=0.0,
        planar_camera=True,
        planar_fov=120,
        planar_resolution=(1024, 1024),
        planar_camera_position_rotation=(0.0, 1.0, 0.0, 120.0, 0.0),
        flip_planar_horizontally=True,
        flip_planar_vertically=False,
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        use_planar_normal_distortion=False,
        screen_facing_planar_texture=True,
        texture_lod_bias=0.8,
        env_map_lod_bias=1.5,
        pbr_extension_overrides={
            "transmission": (0.5, 0.5, 0.5),
        },
    )

    # ------------------------------------------------------------------------------
    # Define the rotating pyramid model configuration
    # ------------------------------------------------------------------------------
    rotating_pyramid_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "pyramid.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "crystal.png"),
            "normal": os.path.join(normal_textures_dir, "crystal.png"),
            "displacement": os.path.join(displacement_textures_dir, "crystal.png"),
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
        texture_lod_bias=0.0,
        env_map_lod_bias=1.5,
    )

    # ------------------------------------------------------------------------------
    # Define the particle renderer configuration
    # ------------------------------------------------------------------------------
    particle_config = base_config.add_particle_renderer(
        particle_render_mode=particle_render_mode,
        max_particles_map={"cpu": 200, "transform_feedback": 50000, "compute_shader": 4000000},
        particles_max=4000000,
        particle_batch_size=600000,
        particle_type="points",
        particle_shader_override=False,
        particle_generator=True,
        generator_delay=0.0,
        particle_size=10.0,
        min_initial_velocity_x=-6.0,
        max_initial_velocity_x=0.0,
        min_initial_velocity_y=-0.0,
        max_initial_velocity_y=35.0,
        min_initial_velocity_z=-3.0,
        max_initial_velocity_z=0.0,
        particle_max_velocity=35.0,
        particle_max_lifetime=2.0,
        particle_max_weight=1.5,
        particle_min_weight=0.1,
        particle_smooth_edges=True,
        particle_color=(0.18, 0.698, 1.0),
        particle_fade_to_color=False,
        particle_fade_color=(0.0, 0.0, 0.0),
        legacy_opacity=0.85,
        legacy_roughness=32,
        particle_gravity=(-8.5, -9.81, 5),
        particle_bounce_factor=0.28,
        particle_ground_plane_normal=(0.0, 1.0, 0.0),
        particle_ground_plane_angle=(0.0, 0.0),
        particle_ground_plane_height=1.0,
        fluid_simulation=True,
        fluid_pressure=0.95,
        fluid_viscosity=0.65,
        particle_spawn_time_jitter=True,
        particle_max_spawn_time_jitter=2.5,
        min_width=-25.0,
        min_height=8.0,
        min_depth=-25.0,
        max_width=25.0,
        max_height=45.0,
        max_depth=25.0,
    )

    # ------------------------------------------------------------------------------
    # Define the water surface configuration
    # ------------------------------------------------------------------------------
    water_config = base_config.add_surface(
        shader_names={
            "vertex": "parallax_mapping",
            "fragment": "water_parallax",
        },
        water_base_color=(0.142, 0.221, 0.861),
        invert_displacement_map=True,
        pom_height_scale=0.096,
        pom_min_steps=128,
        pom_max_steps=512,
        pom_eye_offset_scale=1.0,
        pom_max_depth_clamp=0.99,
        pom_max_forward_offset=1.0,
        pom_enable_frag_depth_adjustment=False,
        legacy_roughness=32,
        wave_speed=0.2,
        wave_amplitude=1.0,
        wave_detail=7.0,
        randomness=800.0,
        tex_coord_frequency=500.0,
        tex_coord_amplitude=0.04,
        width=1000.0,
        height=1000.0,
        surface_depth=10.0,
        shadow_strength=0.85,
        env_map_strength=1.0,
        texture_lod_bias=0.8,
        env_map_lod_bias=1.5,
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
    # Add renderers and apply scene transformations
    # ------------------------------------------------------------------------------
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("water_surface", "surface", **water_config)
    instance.add_renderer("model_stretched", "model", **stretched_pyramid_config)
    instance.add_renderer("model_rotating", "model", **rotating_pyramid_config)
    instance.add_renderer("model_opaque", "model", **opaque_pyramid_config)
    instance.add_renderer("rain", "particle", **particle_config)

    # Apply example scene transformations
    instance.scene_construct.translate_renderer("rain", (0, 0, 0))
    instance.scene_construct.translate_renderer("model_rotating", (0, 2.5, -5))
    instance.scene_construct.rotate_renderer("model_rotating", 45, (0, 1, 0))
    instance.scene_construct.scale_renderer("model_rotating", (1.5, 2.5, 1.5))
    instance.scene_construct.set_auto_rotation("model_rotating", True, axis=(0, 1, 0), speed=2000.0)
    instance.scene_construct.translate_renderer("model_stretched", (2, 2.5, 0))
    instance.scene_construct.scale_renderer("model_stretched", (1.2, 1.2, 1.2))
    instance.scene_construct.translate_renderer("model_opaque", (6, 2.5, -6))
    instance.scene_construct.scale_renderer("model_opaque", (1.3, 1.3, 1.3))

    # ------------------------------------------------------------------------------
    # Run the rendering instance
    # ------------------------------------------------------------------------------
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
