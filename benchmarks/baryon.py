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
    lighting_mode="pbr",
    shadow_map_resolution=2048,
    particle_render_mode="vertex",
    vsync_enabled=True,
    sound_enabled=True,
    fullscreen=False,
):
    """
    Run the benchmark for the Baryon configuration.
    """
    # ------------------------------------------------------------------------------
    # Initialize the base renderer configuration
    # ------------------------------------------------------------------------------
    base_config = RendererConfig(
        window_title="Baryon",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "space/"),
        # Camera positions simulate a spaceship gliding through space.
        # Each tuple represents (x, y, z, yaw, pitch).
        camera_positions=[
            (-2.95, 0.0, -7.2, 207.0, 0.0),  # Start at (0,0,-7.2,187,0)
            (-2.95, 0.0, -7.2, 199.0, -2.0),  # Slight forward, mild yaw decrease
            (-2.95, 0.0, -7.2, 195.0, -3.0),  # More forward, gently pitch down
            (-2.95, 0.0, -7.2, 192.0, -5.0),  # Arcing left, pitch ~-5
            (-2.95, 0.0, -7.2, 198.0, -4.0),  # Slight right pan
            (-2.95, 0.0, -7.2, 200.0, -2.0),  # Yaw ~170, pitch easing up
            (-2.95, 0.0, -7.2, 199.0, -2.0),  # Passing behind objects, mild rise
            (-2.95, 0.0, -7.2, 202.0, -1.0),  # Further forward
            (-2.95, 0.0, -7.2, 209.0, 0.0),  # Pitch to level
            (-2.95, 0.0, -7.2, 215.0, 1.0),  # End vantage, gentle final yaw
        ],
        # Lens rotations for each keyframe (subtle roll from 0 to ~3° then back).
        lens_rotations=[
            0.0,  # No roll
            1.0,  # Slight roll
            2.0,  # Increased roll
            3.0,  # Peak roll ~3°
            2.0,  # Easing back
            1.0,  # Minor roll
            0.0,  # Level
            -1.0,  # Negative roll
            -2.0,  # More negative
            -1.0,  # Near-flat roll
        ],
        fov=60,
        ambient_lighting_strength=0.55,
        ambient_lighting_color=(0.4, 1.0, 0.651),
        lights=[
            {
                "position": (-0.10, 0.0, 0.0),
                "color": (1.0, 1.0, 1.0),
                "strength": 1.0,
                "orth_left": -25.0,
                "orth_right": 25.0,
                "orth_bottom": -25.0,
                "orth_top": 25,
            },
        ],
        near_plane=0.1,
        far_plane=5000,
        lighting_mode=lighting_mode,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        auto_camera=True,
        move_speed=0.1,
        msaa_level=msaa_level,
        alpha_blending=True,
        culling=True,
    )

    # ------------------------------------------------------------------------------
    # Create and set up the rendering instance
    # ------------------------------------------------------------------------------
    instance = RenderingInstance(base_config)
    instance.setup()

    # ------------------------------------------------------------------------------
    # Define the particle renderer configuration
    # ------------------------------------------------------------------------------
    particle_config = base_config.add_particle_renderer(
        particle_render_mode=particle_render_mode,
        particles_max=2000,
        particle_batch_size=2000,
        # Available particle types:
        # ['points', 'lines', 'line_strip', 'line_loop', 'lines_adjacency',
        #  'line_strip_adjacency', 'triangles', 'triangle_strip', 'triangle_fan',
        #  'triangles_adjacency', 'triangle_strip_adjacency', 'patches']
        particle_type="points",
        particle_shader_override=False,
        # Uncomment below to override particle shader names:
        # shader_names={
        #     "vertex": "particles_transform_feedback",
        #     "fragment": "particles",
        #     "compute": None,
        # },
        particle_generator=True,
        generator_delay=0.0,
        particle_size=18.0,
        min_initial_velocity_x=-0.50,
        max_initial_velocity_x=0.0,
        min_initial_velocity_y=-0.07,
        max_initial_velocity_y=0.07,
        min_initial_velocity_z=-1.0,
        max_initial_velocity_z=0.0,
        particle_max_velocity=20.0,
        particle_max_lifetime=85.0,
        particle_max_weight=125.5,
        particle_min_weight=40.5,
        particle_smooth_edges=True,
        particle_color=(0.98, 0.0357, 0.08),
        particle_fade_to_color=True,
        particle_fade_color=(0.0973, 1.0, 0.0541),  # Boosted 5x in shader
        legacy_opacity=0.9,
        legacy_roughness=32,
        particle_gravity=(0.0, 0.0, 0.0),
        particle_bounce_factor=0.025,
        particle_ground_plane_normal=(0.0, 0.0, 1.0),
        particle_ground_plane_angle=(0.0, -30.0),
        particle_ground_plane_height=-7.9,
        fluid_simulation=False,
        fluid_pressure=6.5,
        fluid_viscosity=5.1,
        fluid_force_multiplier=1.0,
        particle_spawn_time_jitter=True,
        particle_max_spawn_time_jitter=7.5,
        min_width=-0.0,
        min_height=-0.0,
        min_depth=-0.0,
        max_width=0.0,
        max_height=0.0,
        max_depth=0.0,
    )

    # ------------------------------------------------------------------------------
    # Define the skybox renderer configuration
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
    instance.add_renderer("warp_particles", "particle", **particle_config)
    instance.scene_construct.translate_renderer("warp_particles", (0.7, 0, 0))
    instance.scene_construct.set_auto_rotation("warp_particles", False, axis=(0, 0, 0), speed=5000.0)

    # ------------------------------------------------------------------------------
    # Run the rendering instance
    # ------------------------------------------------------------------------------
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
