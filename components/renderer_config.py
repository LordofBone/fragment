import copy
import os


class RendererConfig:
    """
    RendererConfig stores all major configuration options for the rendering process:
    - Window properties
    - Camera settings
    - Lighting and material options
    - Parallax mapping and advanced features
    - Planar (secondary) camera
    - Audio settings
    - Debug mode
    """

    def __init__(
        self,
            # ------------------------------------------------------------------------------
            # Window/Runtime Settings
            # ------------------------------------------------------------------------------
        window_title="Renderer",
        window_size=(800, 600),
        vsync_enabled=True,
        fullscreen=False,
        duration=60,

            # ------------------------------------------------------------------------------
            # Texture and Cubemap
            # ------------------------------------------------------------------------------
        texture_paths=None,
        cubemap_folder=None,

            # ------------------------------------------------------------------------------
            # Camera Settings
            # ------------------------------------------------------------------------------
        camera_positions=None,
            lens_rotations=None,
        fov=40,
        near_plane=0.1,
        far_plane=1000,
            auto_camera=False,
            move_speed=1.0,
            loop=True,

            # ------------------------------------------------------------------------------
            # Core Rendering Options
            # ------------------------------------------------------------------------------
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        anisotropy=16.0,
        msaa_level=8,
        alpha_blending=False,
        depth_testing=True,
            culling=True,

            # ------------------------------------------------------------------------------
            # Lighting and Shadow Mapping
            # ------------------------------------------------------------------------------
            lighting_mode="diffuse",
            lights=None,
            ambient_lighting_strength=0.0,
            ambient_lighting_color=(0.0, 0.0, 0.0),
        shadow_map_resolution=2048,
        shadow_strength=1.0,

            # ------------------------------------------------------------------------------
            # Environment Mapping
            # ------------------------------------------------------------------------------
        texture_lod_bias=0.0,
        env_map_lod_bias=0.0,
        env_map_strength=0.5,

            # ------------------------------------------------------------------------------
            # Parallax / Displacement Mapping
            # ------------------------------------------------------------------------------
        invert_displacement_map=False,
        pom_height_scale=0.016,
        pom_min_steps=8,
        pom_max_steps=32,
        pom_eye_offset_scale=1.0,
        pom_max_depth_clamp=0.99,
        pom_max_forward_offset=1.0,
        pom_enable_frag_depth_adjustment=False,

            # ------------------------------------------------------------------------------
            # Front Face Winding, Legacy Material
            # ------------------------------------------------------------------------------
        front_face_winding="CCW",
        legacy_opacity=1.0,
        legacy_roughness=32,

            # ------------------------------------------------------------------------------
            # Planar (Secondary) Camera
            # ------------------------------------------------------------------------------
        planar_camera=False,
        planar_fov=45,
        planar_near_plane=0.1,
        planar_far_plane=100,
        planar_resolution=(1024, 1024),
        planar_camera_position_rotation=(0, 0, 0, 0, 0),
        planar_relative_to_camera=True,
        planar_camera_lens_rotation=0.0,
        flip_planar_horizontally=False,
        flip_planar_vertically=False,
        use_planar_normal_distortion=False,
        screen_facing_planar_texture=False,
        planar_fragment_view_threshold=0.0,
        distortion_strength=0.3,
        refraction_strength=0.3,

            # ------------------------------------------------------------------------------
            # PBR Extension Overrides
            # ------------------------------------------------------------------------------
        pbr_extension_overrides=None,

            # ------------------------------------------------------------------------------
            # Audio Settings
            # ------------------------------------------------------------------------------
        sound_enabled=True,
            background_audio=None,
        audio_delay=0.0,
        audio_loop=False,

            # ------------------------------------------------------------------------------
            # Debug Mode
            # ------------------------------------------------------------------------------
        debug_mode=None,
    ):
        """
        If camera_positions is not given, it defaults to a single position.
        lens_rotations should match the length of camera_positions if used.
        """
        if camera_positions is None:
            camera_positions = [(3.2, 3.2, 3.2, 0.0, 0.0)]
        if lens_rotations is None:
            lens_rotations = [0.0] * len(camera_positions)

        # ------------------------------------------------------------------------------
        # Store Window/Runtime Settings
        # ------------------------------------------------------------------------------
        self.window_title = window_title
        self.window_size = window_size
        self.vsync_enabled = vsync_enabled
        self.fullscreen = fullscreen
        self.duration = duration

        # ------------------------------------------------------------------------------
        # Texture and Cubemap
        # ------------------------------------------------------------------------------
        self.texture_paths = texture_paths
        self.cubemap_folder = cubemap_folder

        # ------------------------------------------------------------------------------
        # Camera Settings
        # ------------------------------------------------------------------------------
        self.camera_positions = camera_positions
        self.lens_rotations = lens_rotations
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.auto_camera = auto_camera
        self.move_speed = move_speed
        self.loop = loop

        # ------------------------------------------------------------------------------
        # Core Rendering Options
        # ------------------------------------------------------------------------------
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction
        self.anisotropy = anisotropy
        self.msaa_level = msaa_level
        self.alpha_blending = alpha_blending
        self.depth_testing = depth_testing
        self.culling = culling

        # ------------------------------------------------------------------------------
        # Lighting and Shadow Mapping
        # ------------------------------------------------------------------------------
        self.lighting_mode = lighting_mode
        self.lights = lights
        self.ambient_lighting_strength = ambient_lighting_strength
        self.ambient_lighting_color = ambient_lighting_color
        self.shadow_map_resolution = shadow_map_resolution
        self.shadow_strength = shadow_strength

        # ------------------------------------------------------------------------------
        # Environment Mapping
        # ------------------------------------------------------------------------------
        self.texture_lod_bias = texture_lod_bias
        self.env_map_lod_bias = env_map_lod_bias
        self.env_map_strength = env_map_strength

        # ------------------------------------------------------------------------------
        # Parallax / Displacement Mapping
        # ------------------------------------------------------------------------------
        self.invert_displacement_map = invert_displacement_map
        self.pom_height_scale = pom_height_scale
        self.pom_min_steps = pom_min_steps
        self.pom_max_steps = pom_max_steps
        self.pom_eye_offset_scale = pom_eye_offset_scale
        self.pom_max_depth_clamp = pom_max_depth_clamp
        self.pom_max_forward_offset = pom_max_forward_offset
        self.pom_enable_frag_depth_adjustment = pom_enable_frag_depth_adjustment

        # ------------------------------------------------------------------------------
        # Front Face Winding, Legacy Material
        # ------------------------------------------------------------------------------
        self.front_face_winding = front_face_winding
        self.legacy_opacity = legacy_opacity
        self.legacy_roughness = legacy_roughness

        # ------------------------------------------------------------------------------
        # Planar (Secondary) Camera
        # ------------------------------------------------------------------------------
        self.planar_camera = planar_camera
        self.planar_fov = planar_fov
        self.planar_near_plane = planar_near_plane
        self.planar_far_plane = planar_far_plane
        self.planar_resolution = planar_resolution
        self.planar_camera_position_rotation = planar_camera_position_rotation
        self.planar_relative_to_camera = planar_relative_to_camera
        self.planar_camera_lens_rotation = planar_camera_lens_rotation
        self.flip_planar_horizontally = flip_planar_horizontally
        self.flip_planar_vertically = flip_planar_vertically
        self.use_planar_normal_distortion = use_planar_normal_distortion
        self.screen_facing_planar_texture = screen_facing_planar_texture
        self.planar_fragment_view_threshold = planar_fragment_view_threshold
        self.distortion_strength = distortion_strength
        self.refraction_strength = refraction_strength

        # ------------------------------------------------------------------------------
        # PBR Extension Overrides
        # ------------------------------------------------------------------------------
        self.pbr_extension_overrides = pbr_extension_overrides

        # ------------------------------------------------------------------------------
        # Audio Settings
        # ------------------------------------------------------------------------------
        self.sound_enabled = sound_enabled
        self.background_audio = background_audio
        self.audio_delay = audio_delay
        self.audio_loop = audio_loop

        # ------------------------------------------------------------------------------
        # Debug Mode
        # ------------------------------------------------------------------------------
        self.debug_mode = debug_mode

        # Placeholder for external shader references
        self.shaders = {}

        # Attempt to discover known shaders
        self.discover_shaders()

    def discover_shaders(self):
        """
        Populate self.shaders by scanning the `shaders` directory.
        This function attempts to find vertex, fragment, and compute shader
        subdirectories, each containing a <type>.glsl file.
        """
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
        """
        Unpack the configuration into a dictionary.
        Returns a deep copy so mutations won't affect this config.
        """
        return copy.deepcopy(self.__dict__)

    def _validate_config(self, config):
        """
        Private method to validate certain configuration options.
        Raises ValueError if invalid options or combinations are detected.
        """
        # Validate front_face_winding
        winding = config.get("front_face_winding", self.front_face_winding)
        if winding not in ("CW", "CCW"):
            raise ValueError("Invalid front_face_winding option. Use 'CW' or 'CCW'.")

        # Validate lighting_mode
        lighting = config.get("lighting_mode", self.lighting_mode)
        if lighting not in ("diffuse", "phong", "pbr"):
            raise ValueError("Invalid lighting mode option. Use 'diffuse', 'phong', or 'pbr'.")

        # If 'diffuse' or 'phong', check legacy_roughness
        if lighting in ("diffuse", "phong"):
            legacy_roughness = config.get("legacy_roughness", self.legacy_roughness)
            if not (0.0 <= legacy_roughness <= 100.0):
                raise ValueError("Invalid legacy_roughness value. Must be between 0 and 100.")

        # Validate particle_render_mode if present
        if "particle_render_mode" in config:
            pmode = config["particle_render_mode"]
            valid_modes = ("cpu", "transform_feedback", "compute_shader")
            if pmode not in valid_modes:
                raise ValueError(
                    "Invalid particle render mode option. "
                    f"Use one of: {', '.join(valid_modes)}."
                )

        # Validate particle_type if present
        if "particle_type" in config:
            ptype = config["particle_type"]
            valid_types = (
                "points", "lines", "line_strip", "line_loop",
                "lines_adjacency", "line_strip_adjacency",
                "triangles", "triangle_strip", "triangle_fan",
                "triangles_adjacency", "triangle_strip_adjacency",
                "patches",
            )
            if ptype not in valid_types:
                raise ValueError(
                    "Invalid particle type option. Use one of: " + ", ".join(valid_types) + "."
                )

    # ------------------------------------------------------------------------------
    # Methods to produce specialized configurations
    # ------------------------------------------------------------------------------
    def add_model(
        self,
        obj_path,
        texture_paths,
        shader_names=("standard", "default"),
        apply_tone_mapping=None,
        apply_gamma_correction=None,
        width=10.0,
        height=10.0,
        alpha_blending=None,
        depth_testing=None,
        culling=None,
        front_face_winding=None,
        cubemap_folder=None,
        lighting_mode=None,
        legacy_opacity=None,
        ambient_lighting_strength=None,
        ambient_lighting_color=None,
        legacy_roughness=None,
        texture_lod_bias=None,
        env_map_lod_bias=None,
        env_map_strength=None,
        shadow_map_resolution=None,
        shadow_strength=None,
        invert_displacement_map=None,
        pom_height_scale=None,
        pom_min_steps=None,
        pom_max_steps=None,
        pom_eye_offset_scale=None,
        pom_max_depth_clamp=None,
        pom_max_forward_offset=None,
        pom_enable_frag_depth_adjustment=None,
        planar_camera=None,
        planar_fov=None,
        planar_near_plane=None,
        planar_far_plane=None,
        planar_resolution=None,
        planar_camera_position_rotation=None,
        planar_relative_to_camera=None,
        planar_camera_lens_rotation=None,
        screen_facing_planar_texture=None,
        planar_fragment_view_threshold=None,
        flip_planar_horizontally=None,
        flip_planar_vertically=None,
        use_planar_normal_distortion=None,
        distortion_strength=None,
        refraction_strength=None,
        lens_rotations=None,
        pbr_extension_overrides=None,
        debug_mode=None,
        **kwargs,
    ):
        """
        Create and return a config dict for a model within this renderer configuration.
        The returned dict is a deep copy of the base config with model-specific overrides applied.
        """

        # Validate pbr_extension_overrides keys if present
        if pbr_extension_overrides is not None:
            allowed_keys = {
                "roughness",
                "metallic",
                "clearcoat",
                "clearcoat_roughness",
                "sheen",
                "anisotropy",
                "anisotropy_rot",
                "transmission",
                "fresnel_exponent",
            }
            invalid_keys = [k for k in pbr_extension_overrides if k not in allowed_keys]
            if invalid_keys:
                raise ValueError(
                    "No such material property: "
                    + ", ".join(invalid_keys)
                    + "; available pbr overrides are: "
                    + ", ".join(sorted(allowed_keys))
                )

        # Start with a copy of the base config
        model_config = self.unpack()

        # Model-specific settings to override
        model_specifics = {
            "obj_path": obj_path,
            "texture_paths": texture_paths,
            "shader_names": shader_names,
            "apply_tone_mapping": apply_tone_mapping,
            "apply_gamma_correction": apply_gamma_correction,
            "width": width,
            "height": height,
            "alpha_blending": alpha_blending,
            "depth_testing": depth_testing,
            "culling": culling,
            "front_face_winding": front_face_winding,
            "cubemap_folder": cubemap_folder,
            "lighting_mode": lighting_mode,
            "legacy_opacity": legacy_opacity,
            "ambient_lighting_strength": ambient_lighting_strength,
            "ambient_lighting_color": ambient_lighting_color,
            "legacy_roughness": legacy_roughness,
            "texture_lod_bias": texture_lod_bias,
            "env_map_lod_bias": env_map_lod_bias,
            "env_map_strength": env_map_strength,
            "shadow_map_resolution": shadow_map_resolution,
            "shadow_strength": shadow_strength,
            "invert_displacement_map": invert_displacement_map,
            "pom_height_scale": pom_height_scale,
            "pom_min_steps": pom_min_steps,
            "pom_max_steps": pom_max_steps,
            "pom_eye_offset_scale": pom_eye_offset_scale,
            "pom_max_depth_clamp": pom_max_depth_clamp,
            "pom_max_forward_offset": pom_max_forward_offset,
            "pom_enable_frag_depth_adjustment": pom_enable_frag_depth_adjustment,
            "planar_camera": planar_camera,
            "planar_fov": planar_fov,
            "planar_near_plane": planar_near_plane,
            "planar_far_plane": planar_far_plane,
            "planar_resolution": planar_resolution,
            "planar_camera_position_rotation": planar_camera_position_rotation,
            "planar_relative_to_camera": planar_relative_to_camera,
            "planar_camera_lens_rotation": planar_camera_lens_rotation,
            "screen_facing_planar_texture": screen_facing_planar_texture,
            "planar_fragment_view_threshold": planar_fragment_view_threshold,
            "flip_planar_horizontally": flip_planar_horizontally,
            "flip_planar_vertically": flip_planar_vertically,
            "use_planar_normal_distortion": use_planar_normal_distortion,
            "distortion_strength": distortion_strength,
            "refraction_strength": refraction_strength,
            "lens_rotations": lens_rotations,
            "pbr_extension_overrides": pbr_extension_overrides,
            "debug_mode": debug_mode,
        }

        # Update with model-specific overrides if not None
        model_config.update({k: v for k, v in model_specifics.items() if v is not None})

        # Apply additional kwargs
        for key, value in kwargs.items():
            if key not in model_config:
                model_config[key] = value

        # Validate final config
        self._validate_config(model_config)
        return model_config

    def add_surface(
        self,
            # Basic overrides
        shader_names=("standard", "default"),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        width=500.0,
        height=500.0,
        alpha_blending=None,
        depth_testing=None,
        culling=None,
        cubemap_folder=None,

            # Lighting / Material
        lighting_mode=None,
        legacy_opacity=None,
        ambient_lighting_strength=None,
        ambient_lighting_color=None,
        legacy_roughness=None,
        texture_lod_bias=None,
        env_map_lod_bias=None,
        env_map_strength=None,
        shadow_map_resolution=None,
        shadow_strength=None,

            # Parallax
        invert_displacement_map=None,
        pom_height_scale=None,
        pom_min_steps=None,
        pom_max_steps=None,
        pom_eye_offset_scale=None,
        pom_max_depth_clamp=None,
        pom_max_forward_offset=None,
        pom_enable_frag_depth_adjustment=None,

            # Planar
        planar_camera=None,
        planar_fov=None,
        planar_near_plane=None,
        planar_far_plane=None,
        planar_resolution=None,
        planar_camera_position_rotation=None,
        planar_relative_to_camera=None,
        planar_camera_lens_rotation=None,
        screen_facing_planar_texture=None,
        flip_planar_horizontally=None,
        flip_planar_vertically=None,
        use_planar_normal_distortion=None,
        planar_fragment_view_threshold=None,
        distortion_strength=None,
        refraction_strength=None,
        lens_rotations=None,

            # Debug
        debug_mode=None,
        **kwargs,
    ):
        """
        Create and return a config dict for a surface within this renderer configuration.
        The returned dict is a copy of the base config with surface-specific overrides.
        """
        surface_config = self.unpack()

        surface_specifics = {
            "shader_names": shader_names,
            "apply_tone_mapping": apply_tone_mapping,
            "apply_gamma_correction": apply_gamma_correction,
            "width": width,
            "height": height,
            "alpha_blending": alpha_blending,
            "depth_testing": depth_testing,
            "culling": culling,
            "cubemap_folder": cubemap_folder,

            "lighting_mode": lighting_mode,
            "legacy_opacity": legacy_opacity,
            "ambient_lighting_strength": ambient_lighting_strength,
            "ambient_lighting_color": ambient_lighting_color,
            "legacy_roughness": legacy_roughness,
            "texture_lod_bias": texture_lod_bias,
            "env_map_lod_bias": env_map_lod_bias,
            "env_map_strength": env_map_strength,
            "shadow_map_resolution": shadow_map_resolution,
            "shadow_strength": shadow_strength,

            "invert_displacement_map": invert_displacement_map,
            "pom_height_scale": pom_height_scale,
            "pom_min_steps": pom_min_steps,
            "pom_max_steps": pom_max_steps,
            "pom_eye_offset_scale": pom_eye_offset_scale,
            "pom_max_depth_clamp": pom_max_depth_clamp,
            "pom_max_forward_offset": pom_max_forward_offset,
            "pom_enable_frag_depth_adjustment": pom_enable_frag_depth_adjustment,

            "planar_camera": planar_camera,
            "planar_fov": planar_fov,
            "planar_near_plane": planar_near_plane,
            "planar_far_plane": planar_far_plane,
            "planar_resolution": planar_resolution,
            "planar_camera_position_rotation": planar_camera_position_rotation,
            "planar_relative_to_camera": planar_relative_to_camera,
            "planar_camera_lens_rotation": planar_camera_lens_rotation,
            "screen_facing_planar_texture": screen_facing_planar_texture,
            "flip_planar_horizontally": flip_planar_horizontally,
            "flip_planar_vertically": flip_planar_vertically,
            "use_planar_normal_distortion": use_planar_normal_distortion,
            "planar_fragment_view_threshold": planar_fragment_view_threshold,
            "distortion_strength": distortion_strength,
            "refraction_strength": refraction_strength,
            "lens_rotations": lens_rotations,
            "debug_mode": debug_mode,
        }

        surface_config.update({k: v for k, v in surface_specifics.items() if v is not None})

        # Apply any additional kwargs
        for key, value in kwargs.items():
            if key not in surface_config:
                surface_config[key] = value

        self._validate_config(surface_config)
        return surface_config

    def add_skybox(
            self,
            cubemap_folder=None,
            shader_names=("skybox_vertex", "skybox_fragment"),
            **kwargs
    ):
        """
        Create and return a config dict for a skybox within this renderer configuration.
        The returned dict is a copy of the base config with skybox-specific overrides.
        """
        skybox_config = self.unpack()

        skybox_specifics = {
            "shader_names": shader_names,
            "cubemap_folder": cubemap_folder,
        }

        skybox_config.update({k: v for k, v in skybox_specifics.items() if v is not None})

        for key, value in kwargs.items():
            if key not in skybox_config:
                skybox_config[key] = value

        self._validate_config(skybox_config)
        return skybox_config

    def add_particle_renderer(
        self,
            # Particle mode and shader
        particle_render_mode="transform_feedback",
        shader_names=("particle_vertex", "particle_fragment"),
        particle_shader_override=False,
        compute_shader_program=None,

            # Basic render toggles
        alpha_blending=None,
        lighting_mode=None,
        legacy_opacity=None,
        texture_lod_bias=None,
        env_map_lod_bias=None,
        ambient_lighting_strength=None,
        ambient_lighting_color=None,
        legacy_roughness=None,
        depth_testing=None,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        culling=None,

            # Generator
        particle_generator=False,
        generator_delay=0.0,

            # Particle counts
        max_particles_map=None,
        particles_max=100,
        particle_batch_size=1,

            # Particle type and shape
        particle_type="points",
        particle_size=1.0,
        particle_smooth_edges=False,

            # Initial velocity ranges
        min_initial_velocity_x=-0.0,
        max_initial_velocity_x=0.0,
        min_initial_velocity_y=-0.0,
        max_initial_velocity_y=0.0,
        min_initial_velocity_z=-0.0,
        max_initial_velocity_z=0.0,
        particle_max_velocity=1.0,

            # Colors
        particle_color=(1.0, 0.0, 0.0),
        particle_fade_to_color=False,
        particle_fade_color=(0.0, 1.0, 0.0),

            # Gravity/Collision
        particle_gravity=(0.0, -9.81, 0.0),
        particle_bounce_factor=0.5,
        particle_ground_plane_normal=(0.0, 1.0, 0.0),
        particle_ground_plane_angle=(0.0, 0.0),
        particle_ground_plane_height=0.0,

            # Lifetimes/Weights
        particle_max_lifetime=5.0,
        particle_max_weight=1.0,
        particle_min_weight=0.1,
        particle_spawn_time_jitter=False,
        particle_max_spawn_time_jitter=5,

            # Placement area
        min_width=-0.5,
        min_height=8.1,
        min_depth=-0.5,
        max_width=0.5,
        max_height=10.1,
        max_depth=0.5,

            # Fluid
        fluid_simulation=False,
        fluid_pressure=0.0,
        fluid_viscosity=0.0,
        fluid_force_multiplier=1.0,

            # Debug
        debug_mode=None,
            **kwargs
    ):
        """
        Create and return a config dict for a particle renderer within this configuration.
        The returned dict is a copy of the base config with particle-specific overrides.
        """
        particle_config = self.unpack()

        particle_specifics = {
            "particle_render_mode": particle_render_mode,
            "particle_shader_override": particle_shader_override,
            "compute_shader_program": compute_shader_program,
            "alpha_blending": alpha_blending,
            "lighting_mode": lighting_mode,
            "legacy_opacity": legacy_opacity,
            "texture_lod_bias": texture_lod_bias,
            "env_map_lod_bias": env_map_lod_bias,
            "ambient_lighting_strength": ambient_lighting_strength,
            "ambient_lighting_color": ambient_lighting_color,
            "legacy_roughness": legacy_roughness,
            "depth_testing": depth_testing,
            "apply_tone_mapping": apply_tone_mapping,
            "apply_gamma_correction": apply_gamma_correction,
            "culling": culling,

            "particle_generator": particle_generator,
            "generator_delay": generator_delay,

            "max_particles_map": max_particles_map,
            "particles_max": particles_max,
            "particle_batch_size": particle_batch_size,

            "particle_type": particle_type,
            "particle_size": particle_size,
            "particle_smooth_edges": particle_smooth_edges,

            "min_initial_velocity_x": min_initial_velocity_x,
            "max_initial_velocity_x": max_initial_velocity_x,
            "min_initial_velocity_y": min_initial_velocity_y,
            "max_initial_velocity_y": max_initial_velocity_y,
            "min_initial_velocity_z": min_initial_velocity_z,
            "max_initial_velocity_z": max_initial_velocity_z,
            "particle_max_velocity": particle_max_velocity,

            "particle_color": particle_color,
            "particle_fade_to_color": particle_fade_to_color,
            "particle_fade_color": particle_fade_color,

            "particle_gravity": particle_gravity,
            "particle_bounce_factor": particle_bounce_factor,
            "particle_ground_plane_normal": particle_ground_plane_normal,
            "particle_ground_plane_angle": particle_ground_plane_angle,
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
            "fluid_pressure": fluid_pressure,
            "fluid_viscosity": fluid_viscosity,
            "fluid_force_multiplier": fluid_force_multiplier,

            "shader_names": shader_names,
            "debug_mode": debug_mode,
        }

        particle_config.update({k: v for k, v in particle_specifics.items() if v is not None})

        # Apply additional kwargs
        for key, value in kwargs.items():
            if key not in particle_config:
                particle_config[key] = value

        self._validate_config(particle_config)
        return particle_config
