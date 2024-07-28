class BaseConfig:
    def __init__(self, window_size=(800, 600), shaders=None, cubemap_folder=None, camera_position=(3.2, 3.2, 3.2),
                 camera_target=(0, 0, 0), up_vector=(0, 1, 0), fov=40, near_plane=0.1, far_plane=1000,
                 light_positions=[(3.0, 3.0, 3.0)], light_colors=[(1.0, 1.0, 1.0)], light_strengths=[0.8],
                 anisotropy=16.0, auto_camera=False, height_factor=1.5, distance_factor=2.0, msaa_level=8,
                 culling=True):
        self.window_size = window_size
        self.shaders = shaders
        self.cubemap_folder = cubemap_folder
        self.camera_position = camera_position
        self.camera_target = camera_target
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

    def unpack(self):
        return self.__dict__


class ModelConfig(BaseConfig):
    def __init__(self, obj_path=None, texture_paths=None, shader_name='default', lod_level=7.5, rotation_speed=2000.0,
                 rotation_axis=(0, 3, 0), apply_tone_mapping=False, apply_gamma_correction=False, width=10.0,
                 height=10.0, **kwargs):
        super().__init__(**kwargs)
        self.obj_path = obj_path
        self.texture_paths = texture_paths
        self.shader_name = shader_name
        self.lod_level = lod_level
        self.rotation_speed = rotation_speed
        self.rotation_axis = rotation_axis
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction
        self.width = width
        self.height = height


class WaterConfig(BaseConfig):
    def __init__(self, shader_name='default', wave_speed=10.0, wave_amplitude=0.1, randomness=0.8,
                 tex_coord_frequency=100.0, tex_coord_amplitude=0.1, width=500.0, height=500.0, **kwargs):
        super().__init__(**kwargs)
        self.shader_name = shader_name
        self.wave_speed = wave_speed
        self.wave_amplitude = wave_amplitude
        self.randomness = randomness
        self.tex_coord_frequency = tex_coord_frequency
        self.tex_coord_amplitude = tex_coord_amplitude
        self.width = width
        self.height = height
