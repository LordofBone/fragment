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
    msaa_level=0,
    anisotropy=16,
    particle_render_mode="vertex",
    vsync_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Aureonrain",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "night_sky_egypt/"),
        camera_positions=[
            (10.0, 10.0, 10.0, -30.0, 0.0),  # Initial position
            (6.0, 6.0, 6.0, -30.0, 0.0),  # Zoom in
            (4.0, 4.0, 10.0, -20.0, 15.0),  # Rotate around
            (0.0, 6.0, 6.0, -15.0, 15.0),  # Rotate around
            (4.0, 10.0, 4.0, -15.0, 15.0),  # Rotate around
            (6.0, 6.0, 6.0, -15.0, 15.0),  # Zoom out to origin
            (10.0, 10.0, 10.0, -30.0, 15.0),  # Back to initial
        ],
        lens_rotations=[0.0],
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.2,
        far_plane=5000,
        lights=[
            {"position": (50.0, 20.0, 30.0), "color": (1.0, 1.0, 1.0), "strength": 0.8},
        ],
        anisotropy=anisotropy,
        auto_camera=True,
        move_speed=0.1,
        loop=True,
        msaa_level=msaa_level,
        culling=True,
        texture_lod_bias=0.8,
        env_map_lod_bias=1.5,
        phong_shading=True,
        background_audio=os.path.join(audio_dir, "music/water_pyramid.wav"),
        audio_delay=0.0,
        audio_loop=True,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the stretched pyramid model
    stretched_pyramid_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "pyramid.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "crystal.png"),
            "normal": os.path.join(normal_textures_dir, "crystal.png"),
            "displacement": os.path.join(displacement_textures_dir, "crystal.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "stealth",
            "shadow_vertex": "shadow_mapping",
            "shadow_fragment": "shadow_mapping",
        },
        opacity=0.0,
        distortion_strength=0.2,
        reflection_strength=0.0,
        planar_camera=True,
        planar_resolution=(1024, 1024),
        planar_fov=30,
        planar_camera_position_rotation=(3.0, 6.0, 0.0, 0.0, 0.0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        screen_facing_planar_texture=True,
        shadowing_enabled=True,
    )

    # Define the configuration for the opaque pyramid model
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
            "fragment": "stealth",
            "shadow_vertex": "shadow_mapping",
            "shadow_fragment": "shadow_mapping",
        },
        opacity=0.5,
        distortion_strength=0.2,
        reflection_strength=0.4,
        planar_camera=True,
        planar_resolution=(1024, 1024),
        planar_fov=30,
        planar_camera_position_rotation=(3.0, 6.0, 0.0, 0.0, 0.0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        screen_facing_planar_texture=True,
        shadowing_enabled=True,
    )

    # Define the configuration for the rotating pyramid model
    rotating_pyramid_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "pyramid.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "crystal.png"),
            "normal": os.path.join(normal_textures_dir, "crystal.png"),
            "displacement": os.path.join(displacement_textures_dir, "crystal.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "embm",
            "shadow_vertex": "shadow_mapping",
            "shadow_fragment": "shadow_mapping",
        },
        rotation_speed=2000.0,
        shadowing_enabled=True,
    )

    # Define the configuration for the particle renderer
    particle_config = base_config.add_particle_renderer(
        particle_render_mode=particle_render_mode,
        # overriding max_particles_map to reduce lag (default values are too high when other things are being rendered)
        max_particles_map={"cpu": 200, "transform_feedback": 50000, "compute_shader": 4000000},
        particles_max=4000000,
        particle_batch_size=600000,
        particle_type="points",
        particle_shader_override=False,
        particle_generator=True,
        generator_delay=0.0,
        particle_size=36.0,
        min_initial_velocity_x=-6.0,
        max_initial_velocity_x=0.0,
        min_initial_velocity_y=-0.0,
        max_initial_velocity_y=35.0,
        min_initial_velocity_z=-3.0,
        max_initial_velocity_z=0.0,
        particle_max_velocity=35.0,  # Set max velocity to a realistic value
        particle_max_lifetime=2.0,  # Set max lifetime to a realistic value
        particle_max_weight=1.5,  # Set max weight to a realistic value
        particle_min_weight=0.5,  # Set min weight to a realistic value
        particle_smooth_edges=False,
        particle_color=(1.02, 3.456, 5.98),
        particle_fade_to_color=True,
        particle_fade_color=(0.0, 0.0, 0.0),
        phong_shading=True,
        opacity=0.85,
        shininess=5.0,
        particle_gravity=(-8.5, -9.81, 5),
        particle_bounce_factor=0.28,  # Standard bounce factor
        particle_ground_plane_normal=(0.0, 1.0, 0.0),  # Corrected normal for ground plane
        particle_ground_plane_height=1.0,  # Height of the ground plane (y = 0)
        fluid_simulation=True,  # Enable fluid simulation
        particle_pressure=0.75,  # Pressure factor for the particles
        particle_viscosity=0.25,  # Viscosity factor for the particles
        particle_spawn_time_jitter=True,  # Jitter for spawn time
        particle_max_spawn_time_jitter=2.5,  # Max jitter for spawn time
        min_width=-25.0,  # Adjusted for a realistic spread along X and Z-axes
        min_height=8.0,  # Adjusted for a realistic spread along Y-axis
        min_depth=-25.0,  # Adjusted for a realistic spread along X and Z-axes
        max_width=25.0,  # Adjusted for a realistic spread along X and Z-axes
        max_height=45.0,  # Adjusted for a realistic spread along Y-axis
        max_depth=25.0,  # Adjusted for a realistic spread along X and Z-axes
    )

    # Define the configuration for the water surface
    water_config = base_config.add_surface(
        shader_names={
            "vertex": "standard",
            "fragment": "water",
        },
        wave_speed=6.0,
        wave_amplitude=0.8,
        randomness=600.0,
        tex_coord_frequency=400.0,
        tex_coord_amplitude=0.010,
        width=50.0,
        height=50.0,
        phong_shading=False,
    )

    # Add a skybox renderer
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    # Add the renderers to the instance
    instance.add_renderer("water_surface", "surface", **water_config)

    instance.add_renderer("skybox", "skybox", **skybox_config)

    instance.add_renderer("model_stretched", "model", **stretched_pyramid_config)
    instance.add_renderer("model_rotating", "model", **rotating_pyramid_config)
    instance.add_renderer("model_opaque", "model", **opaque_pyramid_config)

    instance.add_renderer("rain", "particle", **particle_config)
    instance.scene_construct.translate_renderer("rain", (0, 0, 0))  # Translate first model
    instance.scene_construct.set_auto_rotation("rain", False)

    # Example transformations
    instance.scene_construct.translate_renderer("model_rotating", (0, 0, -3))  # Translate first model
    instance.scene_construct.rotate_renderer("model_rotating", 45, (0, 1, 0))  # Rotate first model
    instance.scene_construct.scale_renderer("model_rotating", (1.5, 2.5, 1.5))  # Scale first model
    instance.scene_construct.set_auto_rotation("model_rotating", True)  # Disable auto-rotation for second model

    instance.scene_construct.translate_renderer("model_stretched", (2, 0, 0))  # Translate second model
    instance.scene_construct.scale_renderer("model_stretched", (1.2, 1.2, 1.2))  # Scale second model

    instance.scene_construct.translate_renderer("model_opaque", (6, 0, -6))  # Translate second model
    instance.scene_construct.scale_renderer("model_opaque", (1.3, 1.3, 1.3))  # Scale second model
    instance.scene_construct.set_auto_rotation("model_opaque", False)  # Disable auto-rotation for second model

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
