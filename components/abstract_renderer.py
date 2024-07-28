from abc import ABC, abstractmethod

import glm
import pygame
from OpenGL.GL import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT

from components.shader_engine import ShaderEngine


class AbstractRenderer(ABC):
    def __init__(self, shaders, window_size=(800, 600), anisotropy=16.0,
                 auto_camera=False, width=10.0, height=10.0, height_factor=1.5, distance_factor=2.0,
                 cubemap_folder=None, rotation_speed=2000.0, rotation_axis=(0, 1, 0),
                 lod_level=1.0, apply_tone_mapping=False, apply_gamma_correction=False):
        self.shaders = shaders
        self.window_size = window_size
        self.anisotropy = anisotropy
        self.shader_programs = {}
        self.auto_camera = auto_camera
        self.width = width
        self.height = height
        self.height_factor = height_factor
        self.distance_factor = distance_factor
        self.camera_position = None
        self.camera_target = None
        self.up_vector = None
        self.fov = None
        self.near_plane = None
        self.far_plane = None
        self.light_positions = []
        self.light_colors = []
        self.light_strengths = []
        self.cubemap_folder = cubemap_folder
        self.rotation_speed = rotation_speed
        self.rotation_axis = glm.vec3(*rotation_axis)
        self.lod_level = lod_level
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction

        # Initialize shaders now that the OpenGL context is created
        self.init_shaders()

    def init_shaders(self):
        for name, paths in self.shaders.items():
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
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, self.anisotropy)

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
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAX_ANISOTROPY_EXT, self.anisotropy)
        glGenerateMipmap(GL_TEXTURE_CUBE_MAP)

    def setup_camera(self):
        if self.auto_camera:
            self.camera_position = glm.vec3(*self.calculate_camera_position_for_object_size(
                self.width, self.height, self.height_factor, self.distance_factor))
        aspect_ratio = self.window_size[0] / self.window_size[1]
        self.view = glm.lookAt(self.camera_position, self.camera_target, self.up_vector)
        self.projection = glm.perspective(glm.radians(self.fov), aspect_ratio, self.near_plane, self.far_plane)

    @staticmethod
    def calculate_camera_position_for_object_size(width, height, height_factor=1.5, distance_factor=2.0):
        """Calculate camera position for a large water surface."""
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

    @abstractmethod
    def create_buffers(self):
        pass

    @abstractmethod
    def render(self):
        pass
