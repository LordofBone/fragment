from abc import ABC, abstractmethod

import glm
import pygame
from OpenGL.GL import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT

from components.camera_control import CameraController
from components.shader_engine import ShaderEngine


def common_funcs(func):
    def wrapper(self, *args, **kwargs):
        glUseProgram(self.shader_program)
        glEnable(GL_DEPTH_TEST)

        viewPosition = self.camera_position
        glUniform3fv(glGetUniformLocation(self.shader_program, 'viewPosition'), 1, glm.value_ptr(viewPosition))

        # Culling setup
        if self.culling:
            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)
            # Set front face winding based on the attribute
            glFrontFace(self.front_face_winding)
        else:
            glDisable(GL_CULL_FACE)

        self.apply_transformations()
        self.set_shader_uniforms()
        self.set_light_uniforms(self.shader_program)

        result = func(self, *args, **kwargs)

        # Unbind textures to avoid affecting subsequent renders
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)
        glBindTexture(GL_TEXTURE_2D, 0)

        # Culling teardown
        if self.culling:
            glDisable(GL_CULL_FACE)

        return result

    return wrapper


class AbstractRenderer(ABC):
    def __init__(self, shader_names, shaders=None, cubemap_folder=None,
                 camera_positions=None, camera_target=(0, 0, 0), up_vector=(0, 1, 0), fov=45, near_plane=0.1,
                 far_plane=100, light_positions=None, light_colors=None, light_strengths=None, rotation_speed=2000.0,
                 rotation_axis=(0, 3, 0), apply_tone_mapping=False, apply_gamma_correction=False, texture_lod_bias=0.0,
                 env_map_lod_bias=0.0, culling=True, msaa_level=8, anisotropy=16.0, auto_camera=False, move_speed=1.0,
                 loop=True, front_face_winding="CCW", window_size=(800, 600), phong_shading=False, **kwargs):

        if light_strengths is None:
            light_strengths = [0.8]
        if light_colors is None:
            light_colors = [(1.0, 1.0, 1.0)]
        if light_positions is None:
            light_positions = [(3.0, 3.0, 3.0)]

        self.dynamic_attrs = kwargs

        self.shader_names = shader_names  # Expecting a tuple (vertex_shader_name, fragment_shader_name)
        self.shaders = shaders or {}
        self.cubemap_folder = cubemap_folder  # Per-instance cubemap folder
        self.camera_positions = camera_positions or [(0, 0, 0)]
        self.camera_target = glm.vec3(*camera_target)
        self.up_vector = glm.vec3(*up_vector)
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.light_positions = [glm.vec3(*pos) for pos in light_positions]
        self.light_colors = [glm.vec3(*col) for col in light_colors]
        self.light_strengths = light_strengths
        self.rotation_speed = rotation_speed
        self.rotation_axis = glm.vec3(*rotation_axis)
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction
        self.model_matrix = glm.mat4(1)
        self.manual_transformations = glm.mat4(1)
        self.translation = glm.vec3(0.0)
        self.rotation = glm.vec3(0.0)
        self.scaling = glm.vec3(1.0)
        self.auto_rotation_enabled = rotation_speed != 0.0
        self.texture_lod_bias = texture_lod_bias
        self.env_map_lod_bias = env_map_lod_bias
        self.culling = culling
        self.msaa_level = msaa_level
        self.anisotropy = anisotropy
        self.auto_camera = auto_camera
        self.move_speed = move_speed
        self.loop = loop
        self.front_face_winding = self.get_winding_constant(front_face_winding)
        self.window_size = window_size

        self.vbos = []
        self.vaos = []

        self.shader_program = None

        self.phong_shading = phong_shading  # Add Phong shading option

        if self.auto_camera:
            self.camera_controller = CameraController(self.camera_positions, self.move_speed, self.loop)
        else:
            self.camera_position = glm.vec3(*self.camera_positions[0])

    def get_winding_constant(self, winding):
        """Convert winding string to OpenGL constant."""
        winding_options = {
            "CW": GL_CW,
            "CCW": GL_CCW
        }
        if winding not in winding_options:
            raise ValueError("Invalid front_face_winding option. Use 'CW' or 'CCW'.")
        return winding_options[winding]

    def setup(self):
        """Setup resources and initialize the renderer."""
        self.init_shaders()
        self.create_buffers()
        self.load_textures()  # Load textures including cubemap
        self.setup_camera()
        self.set_constant_uniforms()

    def init_shaders(self):
        """Initialize shaders from provided shader paths."""
        vertex_shader, fragment_shader = self.shader_names
        vertex_shader_path = self.shaders['vertex'][vertex_shader]
        fragment_shader_path = self.shaders['fragment'][fragment_shader]
        shader_engine = ShaderEngine(vertex_shader_path, fragment_shader_path)
        self.shader_program = shader_engine.shader_program

    def load_texture(self, path, texture):
        """Load a 2D texture from file."""
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
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_LOD_BIAS, self.texture_lod_bias)
        glBindTexture(GL_TEXTURE_2D, 0)  # Unbind texture after loading

    def load_cubemap(self, folder_path, texture, texture_unit):
        """Load a cubemap texture from a folder."""
        faces = ['right.png', 'left.png', 'bottom.png', 'top.png', 'front.png', 'back.png']
        glActiveTexture(GL_TEXTURE0 + texture_unit)  # Activate the correct texture unit
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
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_LOD_BIAS, self.env_map_lod_bias)
        glGenerateMipmap(GL_TEXTURE_CUBE_MAP)
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)  # Unbind after loading to avoid conflicts

    def setup_camera(self):
        """Setup the camera view and projection matrices."""
        if self.auto_camera:
            self.camera_position = self.camera_controller.update(0)  # Initialize the first camera position
            self.camera_target = self.camera_controller.get_current_target()
        aspect_ratio = self.window_size[0] / self.window_size[1]
        self.view = glm.lookAt(self.camera_position, self.camera_target, self.up_vector)
        self.projection = glm.perspective(glm.radians(self.fov), aspect_ratio, self.near_plane, self.far_plane)

    def set_light_uniforms(self, shader_program):
        """Set light uniforms for the shader program."""
        glUseProgram(shader_program)
        for i, (position, color, strength) in enumerate(
                zip(self.light_positions, self.light_colors, self.light_strengths)):
            glUniform3fv(glGetUniformLocation(shader_program, f'lightPositions[{i}]'), 1, glm.value_ptr(position))
            glUniform3fv(glGetUniformLocation(shader_program, f'lightColors[{i}]'), 1, glm.value_ptr(color))
            glUniform1f(glGetUniformLocation(shader_program, f'lightStrengths[{i}]'), strength)

        # Set Phong shading boolean uniform
        glUniform1i(glGetUniformLocation(shader_program, 'phongShading'), int(self.phong_shading))

    def set_model_matrix(self, matrix):
        """Set the model matrix."""
        self.model_matrix = matrix

    def translate(self, position):
        """Translate the model."""
        self.translation = glm.vec3(*position)
        self.update_model_matrix()

    def rotate(self, angle, axis):
        """Rotate the model."""
        self.rotation = glm.vec3(*axis) * glm.radians(angle)
        self.update_model_matrix()

    def scale(self, scale):
        """Scale the model."""
        self.scaling = glm.vec3(*scale)
        self.update_model_matrix()

    def update_model_matrix(self):
        """Update the model matrix with transformations."""
        self.manual_transformations = glm.translate(glm.mat4(1), self.translation)
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.x, glm.vec3(1, 0, 0))
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.y, glm.vec3(0, 1, 0))
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.z, glm.vec3(0, 0, 1))
        self.manual_transformations = glm.scale(self.manual_transformations, self.scaling)

    def apply_transformations(self):
        """Apply transformations to the model matrix."""
        if self.auto_rotation_enabled:
            if self.rotation_speed != 0.0:
                rotation_matrix = glm.rotate(glm.mat4(1), pygame.time.get_ticks() / self.rotation_speed,
                                             self.rotation_axis)
                self.model_matrix = self.manual_transformations * rotation_matrix
            else:
                self.auto_rotation_enabled = False
                self.model_matrix = self.manual_transformations
        else:
            self.model_matrix = self.manual_transformations

    def enable_auto_rotation(self, enabled):
        """Enable or disable auto-rotation."""
        self.auto_rotation_enabled = enabled

    def set_constant_uniforms(self):
        """Set constant uniforms for the shader program."""
        glUseProgram(self.shader_program)
        glUniform1f(glGetUniformLocation(self.shader_program, 'textureLodLevel'), self.texture_lod_bias)
        glUniform1f(glGetUniformLocation(self.shader_program, 'envMapLodLevel'), self.env_map_lod_bias)
        glUniform1i(glGetUniformLocation(self.shader_program, 'applyToneMapping'), self.apply_tone_mapping)
        glUniform1i(glGetUniformLocation(self.shader_program, 'applyGammaCorrection'), self.apply_gamma_correction)

    def set_shader_uniforms(self):
        """Set uniforms for the shader program."""
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'model'), 1, GL_FALSE,
                           glm.value_ptr(self.model_matrix))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'view'), 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'projection'), 1, GL_FALSE,
                           glm.value_ptr(self.projection))
        glUniform1f(glGetUniformLocation(self.shader_program, 'waveSpeed'), self.dynamic_attrs.get('wave_speed', 10.0))
        glUniform1f(glGetUniformLocation(self.shader_program, 'waveAmplitude'),
                    self.dynamic_attrs.get('wave_amplitude', 0.1))
        glUniform1f(glGetUniformLocation(self.shader_program, 'randomness'), self.dynamic_attrs.get('randomness', 0.8))
        glUniform1f(glGetUniformLocation(self.shader_program, 'texCoordFrequency'),
                    self.dynamic_attrs.get('tex_coord_frequency', 100.0))
        glUniform1f(glGetUniformLocation(self.shader_program, 'texCoordAmplitude'),
                    self.dynamic_attrs.get('tex_coord_amplitude', 0.1))
        glUniform3fv(glGetUniformLocation(self.shader_program, 'cameraPos'), 1, glm.value_ptr(self.camera_position))
        glUniform1f(glGetUniformLocation(self.shader_program, 'time'), pygame.time.get_ticks() / 1000.0)

    def update_camera(self, delta_time):
        if self.auto_camera:
            self.camera_position = self.camera_controller.update(delta_time)
            self.camera_target = self.camera_controller.get_current_target()
        self.setup_camera()

    @abstractmethod
    def create_buffers(self):
        """Abstract method to create buffers."""
        pass

    @abstractmethod
    def render(self):
        """Abstract method to render the object."""
        pass
