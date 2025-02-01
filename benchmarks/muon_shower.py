import os

from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance
from config.path_config import (
    cubemaps_dir,
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
        window_title="Muon Shower",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "space/"),
        # Camera path simulating a spaceship gliding through space.
        # Each tuple is (x, y, z, yaw, pitch).
        camera_positions=[
            (-2.95, 0.0, -7.2, 207.0, 0.0),  # 1) Start exactly at (0,0,-7.2,187,0)
            (-2.95, 0.0, -7.2, 199.0, -2.0),  # 2) Slight forward, mild yaw decrease
            (-2.95, 0.0, -7.2, 195.0, -3.0),  # 3) More forward, gently pitch down
            (-2.95, 0.0, -7.2, 192.0, -5.0),  # 4) Arcing left, pitch ~-5
            (-2.95, 0.0, -7.2, 198.0, -4.0),  # 5) Slight right pan
            (-2.95, 0.0, -7.2, 200.0, -2.0),  # 6) Yaw ~170, pitch easing up
            (-2.95, 0.0, -7.2, 199.0, -2.0),  # 7) Passing behind objects, mild rise
            (-2.95, 0.0, -7.2, 202.0, -1.0),  # 8) Further forward
            (-2.95, 0.0, -7.2, 209.0, 0.0),  # 9) Pitch to level
            (-2.95, 0.0, -7.2, 215.0, 1.0),  # 10) End vantage, gentle final yaw
        ],
        # Matching lens (roll) rotations for each keyframe
        # A subtle roll from 0 up to ~3°, then back down.
        lens_rotations=[
            0.0,  # 1) no roll
            1.0,  # 2) slight roll
            2.0,  # 3) roll a bit more
            3.0,  # 4) peak ~3°
            2.0,  # 5) easing back
            1.0,  # 6) smaller tilt
            0.0,  # 7) level
            -1.0,  # 8) negative roll
            -2.0,  # 9) bit more negative
            -1.0,  # 10) near-flat
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
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        auto_camera=True,
        move_speed=0.1,
        msaa_level=msaa_level,
        alpha_blending=True,
        culling=True,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)

    # Set up the rendering instance
    instance.setup()

    # Define the configuration for the particle renderer
    particle_config = base_config.add_particle_renderer(
        particle_render_mode=particle_render_mode,
        particles_max=2000,
        particle_batch_size=2000,
        # available_particle_types = ['points','lines','line_strip','line_loop','lines_adjacency','line_strip_adjacency','triangles','triangle_strip','triangle_fan','triangles_adjacency','triangle_strip_adjacency','patches']
        particle_type="points",
        particle_shader_override=False,
        # if above is True it allows override of shaders for the particle renderer, but you must uncomment the shader_names below
        # and provide the names of the shaders you want to be used
        # shader_names = {
        #     "vertex": "particles_transform_feedback",
        #     "fragment": "particles",
        #     "compute": None,
        # },
        particle_generator=True,
        generator_delay=0.0,
        particle_size=9.0,
        min_initial_velocity_x=-0.84,
        max_initial_velocity_x=-0.04,
        min_initial_velocity_y=-0.10,
        max_initial_velocity_y=0.10,
        min_initial_velocity_z=-1.0,
        max_initial_velocity_z=0.0,
        particle_max_velocity=20.0,  # Set max velocity to a realistic value
        particle_max_lifetime=70.0,  # Set max lifetime to a realistic value
        particle_max_weight=125.5,  # Set max weight to a realistic value
        particle_min_weight=100.5,  # Set min weight to a realistic value
        particle_smooth_edges=True,
        particle_color=(0.973, 1.0, 0.541),
        particle_fade_to_color=True,
        particle_fade_color=(0.984, 0.988, 0.898),
        lighting_mode="phong",
        legacy_opacity=1.0,
        legacy_roughness=32,
        particle_gravity=(0.0, 0.0, 0.0),
        particle_bounce_factor=0.025,  # Standard bounce factor
        particle_ground_plane_normal=(0.0, 0.0, 1.0),  # Corrected normal for ground plane
        particle_ground_plane_height=-7.1,
        # Height of the ground plane on the axis as set by particle_ground_plane_normal
        fluid_simulation=False,  # Enable fluid simulation
        fluid_pressure=6.5,  # Pressure factor for the particles
        fluid_viscosity=5.1,  # Viscosity factor for the particles
        fluid_force_multiplier=1.0,  # Force multiplier for the fluid simulation
        particle_spawn_time_jitter=True,  # Jitter for spawn time
        particle_max_spawn_time_jitter=7.5,  # Max jitter for spawn time
        min_width=-0.0,  # Adjusted for a realistic spread along X and Z-axes
        min_height=-0.0,  # Adjusted for a realistic spread along Y-axis
        min_depth=-0.0,  # Adjusted for a realistic spread along X and Z-axes
        max_width=0.0,  # Adjusted for a realistic spread along X and Z-axes
        max_height=0.0,  # Adjusted for a realistic spread along Y-axis
        max_depth=0.0,  # Adjusted for a realistic spread along X and Z-axes
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

    # Add the particle renderer to the instance with a specific name
    instance.add_renderer("warp_particles", "particle", **particle_config)

    instance.scene_construct.translate_renderer("warp_particles", (0.7, 0, 0))  # Translate first model
    instance.scene_construct.set_auto_rotation("warp_particles", False, axis=(0, 0, 0), speed=5000.0)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
