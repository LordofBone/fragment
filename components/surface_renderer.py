import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer


class SurfaceRenderer(AbstractRenderer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.shader_name = kwargs.get('shader_name')
        self.model = glm.mat4(1)
        self.environmentMap = None

    def create_buffers(self):
        half_width = self.dynamic_attrs['width'] / 2.0
        half_height = self.dynamic_attrs['height'] / 2.0
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
        if self.dynamic_attrs['cubemap_folder']:
            self.load_cubemap(self.dynamic_attrs['cubemap_folder'], self.environmentMap)

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
