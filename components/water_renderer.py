import glm
import numpy as np
import pygame
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer


class WaterRenderer(AbstractRenderer):
    def __init__(self, vertex_shader_path, fragment_shader_path, cubemap_folder, width, height, window_size=(800, 600),
                 camera_position=(4, 2, 4), camera_target=(0, 0, 0), up_vector=(0, 1, 0), fov=45, near_plane=0.1,
                 far_plane=100,
                 light_positions=[(3.0, 3.0, 3.0)], light_colors=[(1.0, 1.0, 1.0)], light_strengths=[0.8],
                 anisotropy=16.0, wave_speed=0.03, wave_amplitude=0.1, randomness=0.5):
        super().__init__(vertex_shader_path, fragment_shader_path, window_size, anisotropy)
        self.cubemap_folder = cubemap_folder
        self.width = width
        self.height = height
        self.camera_target = glm.vec3(*camera_target)
        self.up_vector = glm.vec3(*up_vector)
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.light_positions = [glm.vec3(*pos) for pos in light_positions]
        self.light_colors = [glm.vec3(*col) for col in light_colors]
        self.light_strengths = light_strengths
        self.wave_speed = wave_speed
        self.wave_amplitude = wave_amplitude
        self.randomness = randomness
        self.model = glm.mat4(1)
        self.view = None
        self.projection = None
        self.environmentMap = None

        # Calculate camera position based on the size of the water surface
        self.camera_position = self.calculate_camera_position(camera_position, width, height)

        # Setup camera after shaders are initialized
        self.setup_camera()

        # Create buffers and load textures
        self.create_buffers()
        self.load_textures()

    def init_shaders(self):
        super().init_shaders()

    def create_buffers(self):
        # Create a configurable plane for the water surface
        hw = self.width / 2.0
        hh = self.height / 2.0
        vertices = [
            -hw, 0.0, -hh, 0.0, 1.0,
            hw, 0.0, -hh, 1.0, 1.0,
            hw, 0.0, hh, 1.0, 0.0,
            -hw, 0.0, hh, 0.0, 0.0
        ]
        indices = [
            0, 1, 2,
            2, 3, 0
        ]
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

        position_loc = 0  # location specified in vertex shader
        tex_coords_loc = 1  # location specified in vertex shader

        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        glEnableVertexAttribArray(tex_coords_loc)
        glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def load_textures(self):
        self.environmentMap = glGenTextures(1)
        self.load_cubemap(self.cubemap_folder, self.environmentMap)

    def render(self):
        glClearColor(0.2, 0.3, 0.3, 1.0)  # Set clear color to something distinct
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.shader_program)
        glEnable(GL_DEPTH_TEST)

        # Update uniforms
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'model'), 1, GL_FALSE, glm.value_ptr(self.model))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'view'), 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'projection'), 1, GL_FALSE,
                           glm.value_ptr(self.projection))
        glUniform1f(glGetUniformLocation(self.shader_program, 'waveSpeed'), self.wave_speed)
        glUniform1f(glGetUniformLocation(self.shader_program, 'waveAmplitude'), self.wave_amplitude)
        glUniform1f(glGetUniformLocation(self.shader_program, 'randomness'), self.randomness)

        # Set camera position
        glUniform3fv(glGetUniformLocation(self.shader_program, 'cameraPos'), 1, glm.value_ptr(self.camera_position))

        # Set time uniform
        time_value = pygame.time.get_ticks() / 1000.0
        glUniform1f(glGetUniformLocation(self.shader_program, 'time'), time_value)

        for i in range(len(self.light_positions)):
            glUniform3fv(glGetUniformLocation(self.shader_program, f'lightPositions[{i}]'), 1,
                         glm.value_ptr(self.light_positions[i]))
            glUniform3fv(glGetUniformLocation(self.shader_program, f'lightColors[{i}]'), 1,
                         glm.value_ptr(self.light_colors[i]))
            glUniform1f(glGetUniformLocation(self.shader_program, f'lightStrengths[{i}]'), self.light_strengths[i])

        # Bind environment map texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'environmentMap'), 0)

        # Draw the water surface
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)  # Ensure EBO is bound
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
