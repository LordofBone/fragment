from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance


def run_benchmark(
    stats_queue=None,
    stop_event=None,
    resolution=(800, 600),
        msaa_level=4,
    anisotropy=16,
        shadow_map_resolution=2048,
        particle_render_mode="vertex",
    vsync_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Muon Shower",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        camera_positions=[(4.2, 6.2, 4.2, -60.0, 55.0)],
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=60,
        lights=[
            {"position": (3.0, 1.0, 4.0), "color": (0.0, 1.0, 0.0), "strength": 1.0},
            {"position": (0.0, 1.0, 8.0), "color": (1.0, 0.0, 1.0), "strength": 1.0},
        ],
        near_plane=0.1,
        far_plane=5000,
        anisotropy=anisotropy,
        auto_camera=True,
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
        particles_max=600,
        particle_batch_size=150,
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
        particle_size=36.0,
        min_initial_velocity_x=-3.0,
        max_initial_velocity_x=3.0,
        min_initial_velocity_y=-0.0,
        max_initial_velocity_y=20.0,
        min_initial_velocity_z=-3.0,
        max_initial_velocity_z=3.0,
        particle_max_velocity=20.0,  # Set max velocity to a realistic value
        particle_max_lifetime=15.0,  # Set max lifetime to a realistic value
        particle_max_weight=1.5,  # Set max weight to a realistic value
        particle_min_weight=0.5,  # Set min weight to a realistic value
        particle_smooth_edges=False,
        particle_color=(1.0, 0.7, 0.2),
        particle_fade_to_color=False,
        particle_fade_color=(0.0, 1.0, 0.0),
        phong_shading=True,
        opacity=1.0,
        shininess=0.001,
        particle_gravity=(0.0, -9.81, 0.0),
        particle_bounce_factor=0.65,  # Standard bounce factor
        particle_ground_plane_normal=(0.0, 1.0, 0.0),  # Corrected normal for ground plane
        particle_ground_plane_height=1.0,  # Height of the ground plane (y = 0)
        fluid_simulation=False,  # Enable fluid simulation
        particle_pressure=6.5,  # Pressure factor for the particles
        particle_viscosity=5.1,  # Viscosity factor for the particles
        particle_spawn_time_jitter=True,  # Jitter for spawn time
        particle_max_spawn_time_jitter=2.5,  # Max jitter for spawn time
        min_width=-0.1,  # Adjusted for a realistic spread along X and Z-axes
        min_height=-0.1,  # Adjusted for a realistic spread along Y-axis
        min_depth=-0.1,  # Adjusted for a realistic spread along X and Z-axes
        max_width=0.1,  # Adjusted for a realistic spread along X and Z-axes
        max_height=0.1,  # Adjusted for a realistic spread along Y-axis
        max_depth=0.1,  # Adjusted for a realistic spread along X and Z-axes
    )

    # Add the particle renderer to the instance with a specific name
    instance.add_renderer("sparks", "particle", **particle_config)
    instance.scene_construct.translate_renderer("sparks", (-1, 0, 2.45))  # Translate first model
    instance.scene_construct.set_auto_rotation("sparks", False)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
