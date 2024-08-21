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
        glUniform3fv(glGetUniformLocation(self.shader_program, "viewPosition"), 1, glm.value_ptr(viewPosition))

        # Culling setup
        if self.culling:
            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)
            glFrontFace(self.front_face_winding)
        else:
            glDisable(GL_CULL_FACE)

        self.apply_transformations()
        self.set_shader_uniforms()
        if self.lights_enabled:
            self.set_light_uniforms(self.shader_program)

        result = func(self, *args, **kwargs)

        # Unbind textures
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)
        glBindTexture(GL_TEXTURE_2D, 0)

        # Culling teardown
        if self.culling:
            glDisable(GL_CULL_FACE)

        return result

    return wrapper


class AbstractRenderer(ABC):
    def __init__(self, shader_names, shaders=None, cubemap_folder=None, camera_positions=None, camera_target=(0, 0, 0),
                 up_vector=(0, 1, 0), fov=45, near_plane=0.1, far_plane=100, ambient_lighting_strength=(0.0, 0.0, 0.0),
                 lights=None, rotation_speed=2000.0, rotation_axis=(0, 3, 0), apply_tone_mapping=False,
                 apply_gamma_correction=False, texture_lod_bias=0.0, env_map_lod_bias=0.0, culling=True,
                 msaa_level=8, anisotropy=16.0, auto_camera=False, move_speed=1.0, loop=True,
                 front_face_winding="CCW", window_size=(800, 600), phong_shading=False, opacity=1.0,
                 distortion_strength=0.3, reflection_strength=0.0, screen_texture=None, planar_camera=False,
                 planar_resolution=(1024, 1024), planar_fov=45, planar_near_plane=0.1, planar_far_plane=100,
                 planar_camera_position_offset=(0, 0, 0), planar_camera_rotation=(0, 0),
                 planar_relative_to_camera=False, **kwargs):

        self.dynamic_attrs = kwargs

        self.shader_names = shader_names
        self.shaders = shaders or {}
        self.cubemap_folder = cubemap_folder
        self.camera_positions = camera_positions or [(0, 0, 0)]
        self.camera_target = glm.vec3(*camera_target)
        self.up_vector = glm.vec3(*up_vector)
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
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

        self.opacity = opacity
        self.distortion_strength = distortion_strength
        self.reflection_strength = reflection_strength

        self.screen_texture = screen_texture
        self.planar_resolution = planar_resolution
        self.planar_fov = planar_fov
        self.planar_near_plane = planar_near_plane
        self.planar_far_plane = planar_far_plane

        # Convert planar_camera_position_offset to glm.vec3 here
        self.planar_camera_position_offset = glm.vec3(*planar_camera_position_offset)
        self.planar_camera_rotation = glm.vec2(*planar_camera_rotation)
        self.planar_relative_to_camera = planar_relative_to_camera

        self.vbos = []
        self.vaos = []

        self.shader_program = None

        self.phong_shading = phong_shading

        self.ambient_lighting_strength = glm.vec3(ambient_lighting_strength)

        self.lights_enabled = lights is not None
        if self.lights_enabled:
            self.lights = [
                {
                    "position": glm.vec3(*light.get("position", (0, 0, 0))),
                    "color": glm.vec3(*light.get("color", (1.0, 1.0, 1.0))),
                    "strength": light.get("strength", 1.0),
                }
                for light in lights
            ]
        else:
            self.lights = []

        if self.auto_camera:
            self.camera_controller = CameraController(self.camera_positions, self.move_speed, self.loop)
            self.camera_position = self.camera_controller.update(0)
        else:
            self.camera_position = glm.vec3(*self.camera_positions[0])

        self.planar_camera = planar_camera
        if self.planar_camera:
            self.setup_planar_camera()

    def get_winding_constant(self, winding):
        winding_options = {"CW": GL_CW, "CCW": GL_CCW}
        if winding not in winding_options:
            raise ValueError("Invalid front_face_winding option. Use 'CW' or 'CCW'.")
        return winding_options[winding]

    def setup(self):
        self.init_shaders()
        self.create_buffers()
        self.load_textures()
        self.setup_camera()
        self.set_constant_uniforms()

    def setup_planar_camera(self):
        glActiveTexture(GL_TEXTURE8)
        self.planar_framebuffer = glGenFramebuffers(1)
        self.planar_texture = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.planar_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.planar_resolution[0], self.planar_resolution[1], 0, GL_RGB,
                     GL_UNSIGNED_BYTE, None)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, self.anisotropy)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_LOD_BIAS, self.texture_lod_bias)

        glBindFramebuffer(GL_FRAMEBUFFER, self.planar_framebuffer)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.planar_texture, 0)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Framebuffer for planar camera is not complete")

        self.screen_texture = self.planar_texture
        glBindTexture(GL_TEXTURE_2D, self.screen_texture)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def render_planar_view(self, scene_renderers):
        if not self.planar_camera:
            return None

        # Determine planar camera position based on relative-to-object offset
        if self.planar_relative_to_camera:
            # Calculate direction vector from object to camera
            direction_to_camera = glm.normalize(self.camera_position - self.translation)
            self.planar_camera_position = (
                                                  self.translation + self.planar_camera_position_offset
                                          ) + direction_to_camera * self.dynamic_attrs.get("camera_distance", 2.0)
        else:
            self.planar_camera_position = self.translation + self.planar_camera_position_offset

        # Define the planar target as the object’s position (self.translation)
        planar_target = self.translation + glm.vec3(0.0, 0.0, 0.0)  # Planar camera looks at the object

        # Apply the rotation to adjust the direction
        direction_to_target = glm.vec3(0.0, 0.0, -1.0)  # Default direction is along the negative Z-axis
        rotation_matrix = glm.rotate(glm.mat4(1.0), glm.radians(self.planar_camera_rotation.x), glm.vec3(1.0, 0.0, 0.0))
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(self.planar_camera_rotation.y),
                                     glm.vec3(0.0, 1.0, 0.0))
        adjusted_direction = glm.vec3(rotation_matrix * glm.vec4(direction_to_target, 1.0))

        planar_target = self.planar_camera_position + adjusted_direction

        self.planar_view = glm.lookAt(self.planar_camera_position, planar_target, self.up_vector)

        aspect_ratio = self.planar_resolution[0] / self.planar_resolution[1]
        self.planar_projection = glm.perspective(
            glm.radians(self.planar_fov), aspect_ratio, self.planar_near_plane, self.planar_far_plane
        )

        # Temporarily remove this object from the list of renderers
        scene_renderers = [renderer for renderer in scene_renderers if renderer is not self]

        glBindFramebuffer(GL_FRAMEBUFFER, self.planar_framebuffer)

        # Set the viewport to match the planar resolution
        glViewport(0, 0, self.planar_resolution[0], self.planar_resolution[1])

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for renderer in scene_renderers:
            renderer.render_with_custom_camera(self.planar_view, self.planar_projection)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # Reset the viewport back to the window size
        glViewport(0, 0, self.window_size[0], self.window_size[1])

        glBindTexture(GL_TEXTURE_2D, 0)

    def render_with_custom_camera(self, view_matrix, projection_matrix):
        self.view = view_matrix
        self.projection = projection_matrix
        self.render()

    def init_shaders(self):
        vertex_shader, fragment_shader = self.shader_names
        vertex_shader_path = self.shaders["vertex"][vertex_shader]
        fragment_shader_path = self.shaders["fragment"][fragment_shader]
        shader_engine = ShaderEngine(vertex_shader_path, fragment_shader_path)
        self.shader_program = shader_engine.shader_program

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
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_LOD_BIAS, self.texture_lod_bias)
        glBindTexture(GL_TEXTURE_2D, 0)

    def load_cubemap(self, folder_path, texture, texture_unit):
        faces = ["right.png", "left.png", "bottom.png", "top.png", "front.png", "back.png"]
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        glBindTexture(GL_TEXTURE_CUBE_MAP, texture)
        for i, face in enumerate(faces):
            surface = pygame.image.load(folder_path + face)
            img_data = pygame.image.tostring(surface, "RGB", True)
            width, height = surface.get_size()
            glTexImage2D(
                GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data
            )
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAX_ANISOTROPY_EXT, self.anisotropy)
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_LOD_BIAS, self.env_map_lod_bias)
        glGenerateMipmap(GL_TEXTURE_CUBE_MAP)
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)

    def setup_camera(self):
        if self.auto_camera:
            self.camera_position = self.camera_controller.update(0)
            self.camera_target = self.camera_controller.get_current_target()
        aspect_ratio = self.window_size[0] / self.window_size[1]
        self.view = glm.lookAt(self.camera_position, self.camera_target, self.up_vector)
        self.projection = glm.perspective(glm.radians(self.fov), aspect_ratio, self.near_plane, self.far_plane)

    def set_light_uniforms(self, shader_program):
        glUseProgram(shader_program)
        for i, light in enumerate(self.lights):
            glUniform3fv(
                glGetUniformLocation(shader_program, f"lightPositions[{i}]"), 1, glm.value_ptr(light["position"])
            )
            glUniform3fv(glGetUniformLocation(shader_program, f"lightColors[{i}]"), 1, glm.value_ptr(light["color"]))
            glUniform1f(glGetUniformLocation(shader_program, f"lightStrengths[{i}]"), light["strength"])

        glUniform1i(glGetUniformLocation(shader_program, "phongShading"), int(self.phong_shading))

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
            if self.rotation_speed != 0.0:
                rotation_matrix = glm.rotate(
                    glm.mat4(1), pygame.time.get_ticks() / self.rotation_speed, self.rotation_axis
                )
                self.model_matrix = self.manual_transformations * rotation_matrix
            else:
                self.auto_rotation_enabled = False
                self.model_matrix = self.manual_transformations
        else:
            self.model_matrix = self.manual_transformations

    def enable_auto_rotation(self, enabled):
        self.auto_rotation_enabled = enabled

    def set_constant_uniforms(self):
        glUseProgram(self.shader_program)
        glUniform1f(glGetUniformLocation(self.shader_program, "textureLodLevel"), self.texture_lod_bias)
        glUniform1f(glGetUniformLocation(self.shader_program, "envMapLodLevel"), self.env_map_lod_bias)
        glUniform1i(glGetUniformLocation(self.shader_program, "applyToneMapping"), self.apply_tone_mapping)
        glUniform1i(glGetUniformLocation(self.shader_program, "applyGammaCorrection"), self.apply_gamma_correction)

    def set_shader_uniforms(self):
        glUseProgram(self.shader_program)
        glUniform3fv(
            glGetUniformLocation(self.shader_program, "ambientColor"), 1, glm.value_ptr(self.ambient_lighting_strength)
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "model"), 1, GL_FALSE, glm.value_ptr(self.model_matrix)
        )
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, "view"), 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "projection"), 1, GL_FALSE, glm.value_ptr(self.projection)
        )
        glUniform1f(glGetUniformLocation(self.shader_program, "opacity"), self.opacity)
        glUniform1f(glGetUniformLocation(self.shader_program, "distortionStrength"), self.distortion_strength)
        glUniform1f(glGetUniformLocation(self.shader_program, "reflectionStrength"), self.reflection_strength)

        if self.screen_texture:
            glUniform1i(glGetUniformLocation(self.shader_program, "screenTexture"), 8)

        glUniform1f(glGetUniformLocation(self.shader_program, "waveSpeed"), self.dynamic_attrs.get("wave_speed", 10.0))
        glUniform1f(
            glGetUniformLocation(self.shader_program, "waveAmplitude"), self.dynamic_attrs.get("wave_amplitude", 0.1)
        )
        glUniform1f(glGetUniformLocation(self.shader_program, "randomness"), self.dynamic_attrs.get("randomness", 0.8))
        glUniform1f(
            glGetUniformLocation(self.shader_program, "texCoordFrequency"),
            self.dynamic_attrs.get("tex_coord_frequency", 100.0),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_program, "texCoordAmplitude"),
            self.dynamic_attrs.get("tex_coord_amplitude", 0.1),
        )
        glUniform3fv(glGetUniformLocation(self.shader_program, "cameraPos"), 1, glm.value_ptr(self.camera_position))
        glUniform1f(glGetUniformLocation(self.shader_program, "time"), pygame.time.get_ticks() / 1000.0)

    def update_camera(self, delta_time):
        if self.auto_camera:
            self.camera_position = self.camera_controller.update(delta_time)
            self.camera_target = self.camera_controller.get_current_target()
        self.setup_camera()

    @abstractmethod
    def create_buffers(self):
        pass

    @abstractmethod
    def render(self):
        pass
