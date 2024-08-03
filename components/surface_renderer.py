import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer


class SurfaceRenderer(AbstractRenderer):
    def __init__(self, shader_name, wave_speed=0.03, wave_amplitude=0.1, randomness=0.5,
                 tex_coord_frequency=100.0, tex_coord_amplitude=0.1, **kwargs):
        self.shader_name = shader_name
        self.wave_speed = wave_speed
        self.wave_amplitude = wave_amplitude
        self.randomness = randomness
        self.tex_coord_frequency = tex_coord_frequency
        self.tex_coord_amplitude = tex_coord_amplitude
        self.model = glm.mat4(1)
        self.environmentMap = None

        # Extract renderer-specific arguments
        renderer_kwargs = {k: v for k, v in kwargs.items() if k in {
            'shaders', 'window_size', 'anisotropy', 'auto_camera', 'width', 'height', 'height_factor',
            'distance_factor', 'cubemap_folder', 'rotation_speed', 'rotation_axis', 'lod_level', 'apply_tone_mapping',
            'apply_gamma_correction'
        }}
        super().__init__(**renderer_kwargs)

        self.camera_position = glm.vec3(*kwargs.get('camera_position', (0, 0, 0)))
        self.camera_target = glm.vec3(*kwargs.get('camera_target', (0, 0, 0)))
        self.up_vector = glm.vec3(*kwargs.get('up_vector', (0, 1, 0)))
        self.fov = kwargs.get('fov', 45)
        self.near_plane = kwargs.get('near_plane', 0.1)
        self.far_plane = kwargs.get('far_plane', 100)
        self.light_positions = [glm.vec3(*pos) for pos in kwargs.get('light_positions', [(3.0, 3.0, 3.0)])]
        self.light_colors = [glm.vec3(*col) for col in kwargs.get('light_colors', [(1.0, 1.0, 1.0)])]
        self.light_strengths = kwargs.get('light_strengths', [0.8])

    def create_buffers(self):
        half_width = self.width / 2.0
        half_height = self.height / 2.0
        vertices = [
            -half_width, 0.0, -half_height, 0.0, 1.0,
            half_width, 0.0, -half_height, 1.0, 1.0,
            half_width, 0.0, half_height, 1.0, 0.0,
            -half_width, 0.0, half_height, 0.0, 0.0
        ]
        indices = [0, 1, 2, 2, 3, 0]
        vertices_array = np.array(vertices, dtype=np.float32)
        indices_array = np.array(indices, dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices_array.nbytes, indices_array, GL_STATIC_DRAW)

        float_size = 4
        vertex_stride = 5 * float_size

        position_loc = 2
        tex_coords_loc = 0

        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        glEnableVertexAttribArray(tex_coords_loc)
        glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def load_textures(self):
        self.environmentMap = glGenTextures(1)
        if self.cubemap_folder:
            self.load_cubemap(self.cubemap_folder, self.environmentMap)

    def render(self):
        glUseProgram(self.shader_programs[self.shader_name])
        glEnable(GL_DEPTH_TEST)

        self.apply_transformations()
        self.set_shader_uniforms(self.shader_name)

        for i in range(len(self.light_positions)):
            glUniform3fv(glGetUniformLocation(self.shader_programs[self.shader_name], f'lightPositions[{i}]'), 1,
                         glm.value_ptr(self.light_positions[i]))
            glUniform3fv(glGetUniformLocation(self.shader_programs[self.shader_name], f'lightColors[{i}]'), 1,
                         glm.value_ptr(self.light_colors[i]))
            glUniform1f(glGetUniformLocation(self.shader_programs[self.shader_name], f'lightStrengths[{i}]'),
                        self.light_strengths[i])

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_programs[self.shader_name], 'environmentMap'), 0)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
