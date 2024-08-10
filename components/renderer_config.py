import copy
import os


class RendererConfig:
    def __init__(self, window_size=(800, 600), cubemap_folder=None, camera_positions=None,
                 camera_target=(0, 0, 0), up_vector=(0, 1, 0), rotation_axis=(0, 3, 0), fov=40, near_plane=0.1,
                 far_plane=1000, light_positions=None, light_colors=None, light_strengths=None, anisotropy=16.0,
                 auto_camera=False, height_factor=1.5, distance_factor=2.0, msaa_level=8, culling=True,
                 texture_lod_bias=0.0, env_map_lod_bias=0.0, move_speed=1.0, loop=True, front_face_winding="CCW",
                 shaders=None):
        if light_strengths is None:
            light_strengths = [0.8]
        if light_colors is None:
            light_colors = [(1.0, 1.0, 1.0)]
        if light_positions is None:
            light_positions = [(3.0, 3.0, 3.0)]
        if camera_positions is None:
            camera_positions = [(3.2, 3.2, 3.2)]
        self.window_size = window_size
        self.shaders = shaders
        self.cubemap_folder = cubemap_folder
        self.camera_positions = camera_positions
        self.camera_target = camera_target
        self.rotation_axis = rotation_axis
        self.up_vector = up_vector
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.light_positions = light_positions
        self.light_colors = light_colors
        self.light_strengths = light_strengths
        self.anisotropy = anisotropy
        self.auto_camera = auto_camera
        self.height_factor = height_factor
        self.distance_factor = distance_factor
        self.msaa_level = msaa_level
        self.culling = culling
        self.texture_lod_bias = texture_lod_bias
        self.env_map_lod_bias = env_map_lod_bias
        self.move_speed = move_speed
        self.loop = loop
        self.front_face_winding = front_face_winding
        self.shaders = {}

        self.validate_winding()
        self.discover_shaders()

    def validate_winding(self):
        """Validate the front face winding option."""
        if self.front_face_winding not in ("CW", "CCW"):
            raise ValueError("Invalid front_face_winding option. Use 'CW' or 'CCW'.")

    def discover_shaders(self):
        """Discover shaders in the shaders directory."""
        shader_root = os.path.abspath(os.path.join('shaders'))
        if not os.path.exists(shader_root):
            raise FileNotFoundError(f"The shader root directory '{shader_root}' does not exist.")

        for shader_type in ['vertex', 'fragment']:
            type_path = os.path.join(shader_root, shader_type)
            if not os.path.exists(type_path):
                continue

            for shader_dir in os.listdir(type_path):
                dir_path = os.path.join(type_path, shader_dir)
                shader_file_path = os.path.join(dir_path, f'{shader_type}.glsl')
                if os.path.exists(shader_file_path):
                    if shader_type not in self.shaders:
                        self.shaders[shader_type] = {}
                    self.shaders[shader_type][shader_dir] = shader_file_path

    def unpack(self):
        """Unpack the configuration into a dictionary."""
        return copy.deepcopy(self.__dict__)  # Use deepcopy to avoid mutating the original configuration

    def add_model(self, obj_path, texture_paths, shader_names=('standard', 'default'), rotation_speed=0.0,
                  rotation_axis=(0, 3, 0), apply_tone_mapping=False, apply_gamma_correction=False, width=10.0,
                  height=10.0, wave_speed=10.0, wave_amplitude=0.1, randomness=0.8, tex_coord_frequency=100.0,
                  tex_coord_amplitude=0.1, cubemap_folder=None, **kwargs):
        """Add a model to the configuration."""

        # Start with a deep copy of the base configuration
        model_config = self.unpack()

        # Now apply specific overrides provided by the model, overwriting defaults
        model_specifics = {
            'obj_path': obj_path,
            'texture_paths': texture_paths,
            'shader_names': shader_names,
            'rotation_speed': rotation_speed,
            'rotation_axis': rotation_axis,
            'apply_tone_mapping': apply_tone_mapping,
            'apply_gamma_correction': apply_gamma_correction,
            'width': width,
            'height': height,
            'wave_speed': wave_speed,
            'wave_amplitude': wave_amplitude,
            'randomness': randomness,
            'tex_coord_frequency': tex_coord_frequency,
            'tex_coord_amplitude': tex_coord_amplitude,
            'cubemap_folder': cubemap_folder  # Specific or None
        }

        # Update the configuration with model specifics, preserving non-None values
        model_config.update({k: v for k, v in model_specifics.items() if v is not None})

        # Apply any additional keyword arguments passed in kwargs
        model_config.update(kwargs)

        return model_config

    def add_surface(self, shader_names=('standard', 'default'), wave_speed=10.0, wave_amplitude=0.1, randomness=0.8,
                    rotation_speed=0.0, apply_tone_mapping=False, apply_gamma_correction=False,
                    tex_coord_frequency=100.0,
                    tex_coord_amplitude=0.1, width=500.0, height=500.0, cubemap_folder=None, **kwargs):
        """Add a surface to the configuration."""
        surface_config = self.unpack()

        surface_specifics = {
            'shader_names': shader_names,
            'rotation_speed': rotation_speed,
            'apply_tone_mapping': apply_tone_mapping,
            'apply_gamma_correction': apply_gamma_correction,
            'wave_speed': wave_speed,
            'wave_amplitude': wave_amplitude,
            'randomness': randomness,
            'tex_coord_frequency': tex_coord_frequency,
            'tex_coord_amplitude': tex_coord_amplitude,
            'width': width,
            'height': height,
            'cubemap_folder': cubemap_folder  # Specific or None
        }

        surface_config.update({k: v for k, v in surface_specifics.items() if v is not None})
        surface_config.update(kwargs)

        return surface_config

    def add_skybox(self, cubemap_folder=None, shader_names=('skybox_vertex', 'skybox_fragment'), **kwargs):
        """Add a skybox to the configuration."""
        skybox_config = self.unpack()

        skybox_specifics = {
            'shader_names': shader_names,
            'cubemap_folder': cubemap_folder  # Specific or None
        }

        skybox_config.update({k: v for k, v in skybox_specifics.items() if v is not None})
        skybox_config.update(kwargs)

        return skybox_config
