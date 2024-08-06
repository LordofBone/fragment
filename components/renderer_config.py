import os


class RendererConfig:
    def __init__(self, window_size=(800, 600), cubemap_folder=None, camera_position=(3.2, 3.2, 3.2),
                 camera_target=(0, 0, 0), up_vector=(0, 1, 0), rotation_axis=(0, 3, 0), fov=40, near_plane=0.1,
                 far_plane=1000, light_positions=None, light_colors=None, light_strengths=None, anisotropy=16.0,
                 auto_camera=False, height_factor=1.5, distance_factor=2.0, msaa_level=8, culling=True,
                 texture_lod_bias=0.0, env_map_lod_bias=0.0, shaders=None):
        if light_strengths is None:
            light_strengths = [0.8]
        if light_colors is None:
            light_colors = [(1.0, 1.0, 1.0)]
        if light_positions is None:
            light_positions = [(3.0, 3.0, 3.0)]
        self.window_size = window_size
        self.shaders = shaders
        self.cubemap_folder = cubemap_folder
        self.camera_position = camera_position
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
        self.shaders = {}

        self.discover_shaders()

    def discover_shaders(self):
        """Discover shaders in the shaders directory."""
        shader_root = os.path.abspath(os.path.join('shaders'))
        if not os.path.exists(shader_root):
            raise FileNotFoundError(f"The shader root directory '{shader_root}' does not exist.")

        for shader_dir in os.listdir(shader_root):
            dir_path = os.path.join(shader_root, shader_dir)
            if os.path.isdir(dir_path):
                vertex_shader_path = os.path.join(dir_path, 'vertex.glsl')
                fragment_shader_path = os.path.join(dir_path, 'fragment.glsl')
                if os.path.exists(vertex_shader_path) and os.path.exists(fragment_shader_path):
                    self.shaders[shader_dir] = {
                        'vertex': vertex_shader_path,
                        'fragment': fragment_shader_path
                    }

    def unpack(self):
        """Unpack the configuration into a dictionary."""
        return self.__dict__

    def add_model(self, obj_path, texture_paths, shader_name='default', rotation_speed=0.0, rotation_axis=(0, 3, 0),
                  apply_tone_mapping=False, apply_gamma_correction=False, width=10.0, height=10.0, wave_speed=10.0,
                  wave_amplitude=0.1, randomness=0.8, tex_coord_frequency=100.0, tex_coord_amplitude=0.1, **kwargs):
        """Add a model to the configuration."""
        model_config = {
            'obj_path': obj_path,
            'texture_paths': texture_paths,
            'shader_name': shader_name,
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
        }
        model_config.update(kwargs)
        model_config.update(self.unpack())
        return model_config

    def add_surface(self, shader_name='default', wave_speed=10.0, wave_amplitude=0.1, randomness=0.8,
                    rotation_speed=0.0,
                    apply_tone_mapping=False, apply_gamma_correction=False, tex_coord_frequency=100.0,
                    tex_coord_amplitude=0.1, width=500.0, height=500.0, **kwargs):
        """Add a surface to the configuration."""
        surface_config = {
            'shader_name': shader_name,
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
        }
        surface_config.update(kwargs)
        surface_config.update(self.unpack())
        return surface_config
