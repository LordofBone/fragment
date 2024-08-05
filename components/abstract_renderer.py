from abc import ABC, abstractmethod

import glm
import pygame
from OpenGL.GL import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT

from components.shader_engine import ShaderEngine


def common_funcs(func):
    def wrapper(self, *args, **kwargs):
        glUseProgram(self.shader_programs[self.shader_name])
        glEnable(GL_DEPTH_TEST)
        self.apply_transformations()
        self.set_shader_uniforms(self.shader_name)
        self.set_light_uniforms(self.shader_programs[self.shader_name])
        return func(self, *args, **kwargs)

    return wrapper


class AbstractRenderer(ABC):
    def __init__(self, **kwargs):
        # Dynamically set attributes from kwargs
        self.dynamic_attrs = kwargs

        self.shader_programs = {}
        self.camera_position = glm.vec3(*kwargs.get('camera_position', (0, 0, 0)))
        self.camera_target = glm.vec3(*kwargs.get('camera_target', (0, 0, 0)))
        self.up_vector = glm.vec3(*kwargs.get('up_vector', (0, 1, 0)))
        self.fov = kwargs.get('fov', 45)
        self.near_plane = kwargs.get('near_plane', 0.1)
        self.far_plane = kwargs.get('far_plane', 100)
        self.light_positions = [glm.vec3(*pos) for pos in kwargs.get('light_positions', [(3.0, 3.0, 3.0)])]
        self.light_colors = [glm.vec3(*col) for col in kwargs.get('light_colors', [(1.0, 1.0, 1.0)])]
        self.light_strengths = kwargs.get('light_strengths', [0.8])
        self.rotation = glm.vec3(0.0)
        self.rotation_speed = self.dynamic_attrs['rotation_speed']
        self.rotation_axis = glm.vec3(*self.dynamic_attrs['rotation_axis'])
        self.apply_tone_mapping = self.dynamic_attrs['apply_tone_mapping']
        self.apply_gamma_correction = self.dynamic_attrs['apply_gamma_correction']
        self.model_matrix = glm.mat4(1)
        self.manual_transformations = glm.mat4(1)
        self.translation = glm.vec3(0.0)
        self.rotation = glm.vec3(0.0)
        self.scaling = glm.vec3(1.0)
        self.auto_rotation_enabled = False if self.dynamic_attrs['rotation_speed'] == 0.0 else True

    def setup(self):
        """Setup resources and initialize the renderer."""
        self.init_shaders()
        self.create_buffers()
        self.load_textures()
        self.setup_camera()

    def init_shaders(self):
        for name, paths in self.dynamic_attrs['shaders'].items():
            shader_engine = ShaderEngine(paths['vertex'], paths['fragment'])
            shader_engine.init_shaders()
            self.shader_programs[name] = shader_engine.shader_program

    def load_texture(self, path, texture):
        surface = pygame.image.load(path)
        img_data = pygame.image.tostring(surface, "RGB", True)
        width, height = surface.get_size()
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, self.dynamic_attrs['anisotropy'])
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_LOD_BIAS,
                        self.dynamic_attrs['texture_lod_bias'])  # Set texture LOD bias

    def load_cubemap(self, folder_path, texture):
        faces = ['right.png', 'left.png', 'top.png', 'bottom.png', 'front.png', 'back.png']
        glBindTexture(GL_TEXTURE_CUBE_MAP, texture)
        for i, face in enumerate(faces):
            surface = pygame.image.load(folder_path + face)
            img_data = pygame.image.tostring(surface, "RGB", True)
            width, height = surface.get_size()
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE,
                         img_data)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAX_ANISOTROPY_EXT, self.dynamic_attrs['anisotropy'])
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_LOD_BIAS,
                        self.dynamic_attrs['env_map_lod_bias'])  # Set env map LOD bias
        glGenerateMipmap(GL_TEXTURE_CUBE_MAP)

    def setup_camera(self):
        if self.dynamic_attrs['auto_camera']:
            self.camera_position = glm.vec3(*self.calculate_camera_position_for_object_size(
                self.dynamic_attrs['width'], self.dynamic_attrs['height'], self.dynamic_attrs['height_factor'],
                self.dynamic_attrs['distance_factor']))
        aspect_ratio = self.dynamic_attrs['window_size'][0] / self.dynamic_attrs['window_size'][1]
        self.dynamic_attrs['view'] = glm.lookAt(self.camera_position, self.camera_target, self.up_vector)
        self.dynamic_attrs['projection'] = glm.perspective(glm.radians(self.fov), aspect_ratio, self.near_plane,
                                                           self.far_plane)

    @staticmethod
    def calculate_camera_position_for_object_size(width, height, height_factor=1.5, distance_factor=2.0):
        """Calculate camera position for a large surface."""
        camera_height = max(width, height) * height_factor
        camera_distance = max(width, height) * distance_factor
        return camera_distance, camera_height, camera_distance

    def set_light_uniforms(self, shader_program):
        glUseProgram(shader_program)
        for i in range(len(self.light_positions)):
            glUniform3fv(glGetUniformLocation(shader_program, f'lightPositions[{i}]'), 1,
                         glm.value_ptr(self.light_positions[i]))
            glUniform3fv(glGetUniformLocation(shader_program, f'lightColors[{i}]'), 1,
                         glm.value_ptr(self.light_colors[i]))
            glUniform1f(glGetUniformLocation(shader_program, f'lightStrengths[{i}]'), self.light_strengths[i])

    def set_model_matrix(self, matrix):
        self.model_matrix = matrix

    def translate(self, position):
        self.translation = glm.vec3(*position)
        self.update_model_matrix()

    def rotate(self, angle, axis):
        self.rotation = glm.vec3(*axis) * glm.radians(angle)
        self.update_model_matrix()

    def scale(self, scale):
        self.scaling = glm.vec3(*scale)
        self.update_model_matrix()

    def update_model_matrix(self):
        self.manual_transformations = glm.translate(glm.mat4(1), self.translation)
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.x, glm.vec3(1, 0, 0))
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.y, glm.vec3(0, 1, 0))
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.z, glm.vec3(0, 0, 1))
        self.manual_transformations = glm.scale(self.manual_transformations, self.scaling)

    def apply_transformations(self):
        if self.auto_rotation_enabled:
            if self.dynamic_attrs['rotation_speed'] != 0.0:
                rotation_matrix = glm.rotate(glm.mat4(1),
                                             pygame.time.get_ticks() / self.dynamic_attrs['rotation_speed'],
                                             self.dynamic_attrs['rotation_axis'])
                self.model_matrix = self.manual_transformations * rotation_matrix
            else:
                self.auto_rotation_enabled = False
                self.model_matrix = self.manual_transformations
        else:
            self.model_matrix = self.manual_transformations

    def enable_auto_rotation(self, enabled):
        self.auto_rotation_enabled = enabled

    def set_shader_uniforms(self, shader_name):
        glUseProgram(self.shader_programs[shader_name])
        glUniformMatrix4fv(glGetUniformLocation(self.shader_programs[shader_name], 'model'), 1, GL_FALSE,
                           glm.value_ptr(self.model_matrix))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_programs[shader_name], 'view'), 1, GL_FALSE,
                           glm.value_ptr(self.dynamic_attrs['view']))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_programs[shader_name], 'projection'), 1, GL_FALSE,
                           glm.value_ptr(self.dynamic_attrs['projection']))
        glUniform1f(glGetUniformLocation(self.shader_programs[shader_name], 'waveSpeed'),
                    self.dynamic_attrs['wave_speed'])
        glUniform1f(glGetUniformLocation(self.shader_programs[shader_name], 'waveAmplitude'),
                    self.dynamic_attrs['wave_amplitude'])
        glUniform1f(glGetUniformLocation(self.shader_programs[shader_name], 'randomness'),
                    self.dynamic_attrs['randomness'])
        glUniform1f(glGetUniformLocation(self.shader_programs[shader_name], 'texCoordFrequency'),
                    self.dynamic_attrs['tex_coord_frequency'])
        glUniform1f(glGetUniformLocation(self.shader_programs[shader_name], 'texCoordAmplitude'),
                    self.dynamic_attrs['tex_coord_amplitude'])
        glUniform3fv(glGetUniformLocation(self.shader_programs[shader_name], 'cameraPos'), 1,
                     glm.value_ptr(self.camera_position))
        glUniform1f(glGetUniformLocation(self.shader_programs[shader_name], 'time'),
                    pygame.time.get_ticks() / 1000.0)

    @abstractmethod
    def create_buffers(self):
        pass

    @abstractmethod
    def render(self):
        pass
