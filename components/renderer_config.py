import copy
import os


class RendererConfig:
    def __init__(
        self,
        window_title="Renderer",
        window_size=(800, 600),
        vsync_enabled=True,
        fullscreen=False,
        duration=60,
        texture_paths=None,
        cubemap_folder=None,
        camera_positions=None,
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        rotation_axis=(0, 3, 0),
        fov=40,
        near_plane=0.1,
        far_plane=1000,
        lights=None,
        anisotropy=16.0,
        auto_camera=False,
        msaa_level=8,
        alpha_blending=False,
        depth_testing=True,
            shadow_map_resolution=2048,
        culling=True,
        texture_lod_bias=0.0,
        env_map_lod_bias=0.0,
        move_speed=1.0,
        loop=True,
        front_face_winding="CCW",
        shaders=None,
        phong_shading=False,
        opacity=1.0,
        shininess=1.0,
        ambient_lighting_strength=(0.0, 0.0, 0.0),
        planar_camera=False,
        planar_fov=45,
        planar_near_plane=0.1,
        planar_far_plane=100,
        planar_resolution=(1024, 1024),
        planar_camera_position_rotation=(0, 0, 0, 0, 0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        screen_facing_planar_texture=False,
        lens_rotations=None,
        background_audio=None,
        audio_delay=0.0,
        audio_loop=False,
        debug_mode=None,
    ):
        if camera_positions is None:
            camera_positions = [(3.2, 3.2, 3.2, 0.0, 0.0)]
        self.window_title = window_title
        self.window_size = window_size
        self.vsync_enabled = vsync_enabled
        self.fullscreen = fullscreen
        self.duration = duration
        self.texture_paths = texture_paths
        self.shaders = shaders
        self.cubemap_folder = cubemap_folder
        self.camera_positions = camera_positions
        self.camera_target = camera_target
        self.rotation_axis = rotation_axis
        self.up_vector = up_vector
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.lights = lights
        self.anisotropy = anisotropy
        self.auto_camera = auto_camera
        self.msaa_level = msaa_level
        self.alpha_blending = alpha_blending
        self.depth_testing = depth_testing
        self.shadow_map_resolution = shadow_map_resolution
        self.culling = culling
        self.texture_lod_bias = texture_lod_bias
        self.env_map_lod_bias = env_map_lod_bias
        self.move_speed = move_speed
        self.loop = loop
        self.front_face_winding = front_face_winding
        self.phong_shading = phong_shading
        self.opacity = opacity
        self.shininess = shininess
        self.ambient_lighting_strength = ambient_lighting_strength
        self.shaders = {}

        # Planar camera settings combined
        self.planar_camera = planar_camera
        self.planar_fov = planar_fov
        self.planar_near_plane = planar_near_plane
        self.planar_far_plane = planar_far_plane
        self.planar_resolution = planar_resolution
        self.planar_camera_position_rotation = planar_camera_position_rotation
        self.planar_relative_to_camera = planar_relative_to_camera
        self.planar_camera_lens_rotation = planar_camera_lens_rotation
        self.screen_facing_planar_texture = screen_facing_planar_texture

        # Lens rotations for the camera
        self.lens_rotations = lens_rotations or [0.0] * len(self.camera_positions)

        # Audio settings
        self.background_audio = background_audio
        self.audio_delay = audio_delay
        self.audio_loop = audio_loop

        # Debug mode
        self.debug_mode = debug_mode

        self.validate_winding()
        self.discover_shaders()

    def validate_winding(self):
        """Validate the front face winding option."""
        if self.front_face_winding not in ("CW", "CCW"):
            raise ValueError("Invalid front_face_winding option. Use 'CW' or 'CCW'.")

    def discover_shaders(self):
        """Discover shaders in the shaders directory."""
        shader_root = os.path.abspath(os.path.join("shaders"))
        if not os.path.exists(shader_root):
            raise FileNotFoundError(f"The shader root directory '{shader_root}' does not exist.")

        for shader_type in ["vertex", "fragment", "compute"]:
            type_path = os.path.join(shader_root, shader_type)
            if not os.path.exists(type_path):
                continue

            for shader_dir in os.listdir(type_path):
                dir_path = os.path.join(type_path, shader_dir)
                shader_file_path = os.path.join(dir_path, f"{shader_type}.glsl")
                if os.path.exists(shader_file_path):
                    if shader_type not in self.shaders:
                        self.shaders[shader_type] = {}
                    self.shaders[shader_type][shader_dir] = shader_file_path

    def unpack(self):
        """Unpack the configuration into a dictionary."""
        return copy.deepcopy(self.__dict__)  # Use deepcopy to avoid mutating the original configuration

    def add_model(
        self,
        obj_path,
        texture_paths,
        shader_names=("standard", "default"),
        rotation_speed=0.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        width=10.0,
        height=10.0,
        alpha_blending=None,
        depth_testing=None,
        culling=None,
        cubemap_folder=None,
        phong_shading=None,
        opacity=1.0,
        shininess=1.0,
            shadow_map_resolution=None,
        planar_camera=None,
        planar_fov=None,
        planar_near_plane=None,
        planar_far_plane=None,
        planar_resolution=None,
        planar_camera_position_rotation=None,
        planar_relative_to_camera=None,
        planar_camera_lens_rotation=None,
        screen_facing_planar_texture=None,
        lens_rotations=None,
        debug_mode=None,
        **kwargs,
    ):
        """Add a model to the configuration."""

        # Start with a deep copy of the base configuration
        model_config = self.unpack()

        # Now apply specific overrides provided by the model, overwriting defaults
        model_specifics = {
            "obj_path": obj_path,
            "texture_paths": texture_paths,
            "shader_names": shader_names,
            "rotation_speed": rotation_speed,
            "rotation_axis": rotation_axis,
            "apply_tone_mapping": apply_tone_mapping,
            "apply_gamma_correction": apply_gamma_correction,
            "width": width,
            "height": height,
            "alpha_blending": alpha_blending,
            "depth_testing": depth_testing,
            "culling": culling,
            "cubemap_folder": cubemap_folder,
            "phong_shading": phong_shading,
            "opacity": opacity,
            "shininess": shininess,
            "shadow_map_resolution": shadow_map_resolution,
            "planar_camera": planar_camera,
            "planar_fov": planar_fov,
            "planar_near_plane": planar_near_plane,
            "planar_far_plane": planar_far_plane,
            "planar_resolution": planar_resolution,
            "planar_camera_position_rotation": planar_camera_position_rotation,
            "planar_relative_to_camera": planar_relative_to_camera,
            "planar_camera_lens_rotation": planar_camera_lens_rotation,
            "screen_facing_planar_texture": screen_facing_planar_texture,
            "lens_rotations": lens_rotations,
            "debug_mode": debug_mode,
        }

        # Update the configuration with model specifics, preserving non-None values
        model_config.update({k: v for k, v in model_specifics.items() if v is not None})

        # Apply any additional keyword arguments passed in kwargs
        for key, value in kwargs.items():
            if key not in model_config:
                model_config[key] = value

        return model_config

    def add_surface(
        self,
        shader_names=("standard", "default"),
        rotation_speed=0.0,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        width=500.0,
        height=500.0,
        alpha_blending=None,
        depth_testing=None,
        culling=None,
        cubemap_folder=None,
        phong_shading=None,
        opacity=1.0,
        shininess=1.0,
            shadow_map_resolution=None,
        planar_camera=None,
        planar_fov=None,
        planar_near_plane=None,
        planar_far_plane=None,
        planar_resolution=None,
        planar_camera_position_rotation=None,
        planar_relative_to_camera=None,
        planar_camera_lens_rotation=None,
        screen_facing_planar_texture=None,
        lens_rotations=None,
        debug_mode=None,
        **kwargs,
    ):
        """Add a surface to the configuration."""
        surface_config = self.unpack()

        surface_specifics = {
            "shader_names": shader_names,
            "rotation_speed": rotation_speed,
            "apply_tone_mapping": apply_tone_mapping,
            "apply_gamma_correction": apply_gamma_correction,
            "width": width,
            "height": height,
            "alpha_blending": alpha_blending,
            "depth_testing": depth_testing,
            "culling": culling,
            "cubemap_folder": cubemap_folder,
            "phong_shading": phong_shading,
            "opacity": opacity,
            "shininess": shininess,
            "shadow_map_resolution": shadow_map_resolution,
            "planar_camera": planar_camera,
            "planar_fov": planar_fov,
            "planar_near_plane": planar_near_plane,
            "planar_far_plane": planar_far_plane,
            "planar_resolution": planar_resolution,
            "planar_camera_position_rotation": planar_camera_position_rotation,
            "planar_relative_to_camera": planar_relative_to_camera,
            "planar_camera_lens_rotation": planar_camera_lens_rotation,
            "screen_facing_planar_texture": screen_facing_planar_texture,
            "lens_rotations": lens_rotations,
            "debug_mode": debug_mode,
        }

        surface_config.update({k: v for k, v in surface_specifics.items() if v is not None})

        # Apply any additional keyword arguments passed in kwargs
        for key, value in kwargs.items():
            if key not in surface_config:
                surface_config[key] = value

        return surface_config

    def add_skybox(self, cubemap_folder=None, shader_names=("skybox_vertex", "skybox_fragment"), **kwargs):
        """Add a skybox to the configuration."""
        skybox_config = self.unpack()

        skybox_specifics = {
            "shader_names": shader_names,
            "cubemap_folder": cubemap_folder,
        }

        skybox_config.update({k: v for k, v in skybox_specifics.items() if v is not None})

        # Apply any additional keyword arguments passed in kwargs
        for key, value in kwargs.items():
            if key not in skybox_config:
                skybox_config[key] = value

        return skybox_config

    def add_particle_renderer(
        self,
        particle_render_mode="transform_feedback",
        shader_names=("particle_vertex", "particle_fragment"),
        particle_shader_override=False,
        compute_shader_program=None,
        alpha_blending=None,
        phong_shading=None,
        opacity=1.0,
        # Lower shininess values create broader, more visible specular highlights; higher values create sharper, smaller highlights.
        shininess=0.001,
        depth_testing=None,
        culling=None,
        particle_generator=False,
        generator_delay=0.0,
        max_particles_map=None,
        particles_max=100,
        particle_batch_size=1,
        particle_type="points",
        particle_size=1.0,
        particle_smooth_edges=False,
        min_initial_velocity_x=-0.0,
        max_initial_velocity_x=0.0,
        min_initial_velocity_y=-0.0,
        max_initial_velocity_y=0.0,
        min_initial_velocity_z=-0.0,
        max_initial_velocity_z=0.0,
        particle_max_velocity=1.0,
        particle_color=(1.0, 0.0, 0.0),
        particle_fade_to_color=False,
        particle_fade_color=(0.0, 1.0, 0.0),
        particle_gravity=(0.0, -9.81, 0.0),
        particle_bounce_factor=0.5,
        particle_ground_plane_normal=(0.0, 1.0, 0.0),
        particle_ground_plane_height=0.0,
        particle_max_lifetime=5.0,
        particle_max_weight=1.0,
        particle_min_weight=0.1,
        particle_spawn_time_jitter=False,
        particle_max_spawn_time_jitter=5,
        min_width=-0.5,
        min_height=8.1,
        min_depth=-0.5,
        max_width=0.5,
        max_height=10.1,
        max_depth=0.5,
        fluid_simulation=False,
        particle_pressure=0.0,
        particle_viscosity=0.0,
        **kwargs,
    ):
        """Add a particle renderer to the configuration."""
        particle_config = self.unpack()

        particle_specifics = {
            "particle_render_mode": particle_render_mode,
            "particle_shader_override": particle_shader_override,
            "alpha_blending": alpha_blending,
            "phong_shading": phong_shading,
            "opacity": opacity,
            "shininess": shininess,
            "depth_testing": depth_testing,
            "culling": culling,
            "particle_generator": particle_generator,
            "generator_delay": generator_delay,
            "max_particles_map": max_particles_map,
            "particles_max": particles_max,
            "particle_batch_size": particle_batch_size,
            "particle_type": particle_type,
            "particle_smooth_edges": particle_smooth_edges,
            "particle_max_velocity": particle_max_velocity,
            "shader_names": shader_names,
            "compute_shader_program": compute_shader_program,
            "particle_size": particle_size,
            "min_initial_velocity_x": min_initial_velocity_x,
            "max_initial_velocity_x": max_initial_velocity_x,
            "min_initial_velocity_y": min_initial_velocity_y,
            "max_initial_velocity_y": max_initial_velocity_y,
            "min_initial_velocity_z": min_initial_velocity_z,
            "max_initial_velocity_z": max_initial_velocity_z,
            "particle_color": particle_color,
            "particle_fade_to_color": particle_fade_to_color,
            "particle_fade_color": particle_fade_color,
            "particle_gravity": particle_gravity,
            "particle_bounce_factor": particle_bounce_factor,
            "particle_ground_plane_normal": particle_ground_plane_normal,
            "particle_ground_plane_height": particle_ground_plane_height,
            "particle_max_lifetime": particle_max_lifetime,
            "particle_max_weight": particle_max_weight,
            "particle_min_weight": particle_min_weight,
            "particle_spawn_time_jitter": particle_spawn_time_jitter,
            "particle_max_spawn_time_jitter": particle_max_spawn_time_jitter,
            "min_width": min_width,
            "min_height": min_height,
            "min_depth": min_depth,
            "max_width": max_width,
            "max_height": max_height,
            "max_depth": max_depth,
            "fluid_simulation": fluid_simulation,
            "particle_pressure": particle_pressure,
            "particle_viscosity": particle_viscosity,
        }

        # Update the configuration with particle renderer specifics, preserving non-None values
        particle_config.update({k: v for k, v in particle_specifics.items() if v is not None})

        # Apply any additional keyword arguments passed in kwargs
        for key, value in kwargs.items():
            if key not in particle_config:
                particle_config[key] = value

        return particle_config
