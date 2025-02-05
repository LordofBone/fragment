"""
AbstractRenderer Module

This module defines the AbstractRenderer class which provides an abstract
interface for rendering 3D objects/scenes with OpenGL. It handles shader
initialization, texture loading (including cubemaps), shadow mapping,
camera control, and many configurable rendering options (parallax mapping,
tone mapping, gamma correction, etc).

The module also includes helper functions and decorators used by the renderer.
"""

import functools
import os
import time
from abc import ABC, abstractmethod

import glm
import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT
from PIL import Image

from components.camera_control import CameraController
from components.shader_engine import ShaderEngine
from components.shadow_map_manager import ShadowMapManager
from components.texture_manager import TextureManager
from config.path_config import screenshots_dir
from utils.image_saver import ImageSaver

# Global managers
texture_manager = TextureManager()
image_saver = ImageSaver(screenshots_dir="screenshots")


def check_gl_error(context: str, debug_mode: bool):
    """
    Check for OpenGL errors if debug_mode is enabled.

    :param context: A string indicating where in the code the check occurs.
    :param debug_mode: If True, any OpenGL error raises a RuntimeError.
    """
    if debug_mode:
        gl_error = glGetError()
        if gl_error != GL_NO_ERROR:
            raise RuntimeError(f"OpenGL error in {context}: {gl_error}")


def with_gl_render_state(func):
    """
    Decorator to set up common OpenGL state, apply transformations,
    set uniforms, and reset state after a render function call.
    """

    @functools.wraps(func)
    def render_config(self, *args, **kwargs):
        # Use the main shader program.
        self.shader_engine.use_shader_program()
        check_gl_error("glUseProgram", self.debug_mode)

        # --- Alpha Blending ---
        if self.alpha_blending:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        else:
            glDisable(GL_BLEND)

        # --- Depth Testing ---
        if self.depth_testing:
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)
        check_gl_error("Depth testing setup", self.debug_mode)

        # --- Set view position uniform ---
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "viewPosition"),
            1,
            glm.value_ptr(self.camera_position),
        )
        check_gl_error("Setting viewPosition uniform", self.debug_mode)

        # --- Face Culling ---
        if self.culling:
            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)
            glFrontFace(self.front_face_winding)
        else:
            glDisable(GL_CULL_FACE)
        check_gl_error("Culling setup", self.debug_mode)

        # --- Apply model transformations ---
        self.apply_transformations()
        check_gl_error("apply_transformations", self.debug_mode)

        # --- Set lighting and other uniforms ---
        if self.lights_enabled:
            self.set_light_uniforms(self.shader_engine.shader_program)
        check_gl_error("set_light_uniforms", self.debug_mode)

        self.set_shader_uniforms()
        check_gl_error("set_shader_uniforms", self.debug_mode)

        self.set_shadow_shader_uniforms()
        check_gl_error("set_shadow_shader_uniforms", self.debug_mode)

        # --- Call the decorated render function ---
        result = func(self, *args, **kwargs)
        check_gl_error("render function", self.debug_mode)

        # --- Unbind textures and reset state ---
        glBindTexture(GL_TEXTURE_2D, 0)
        check_gl_error("Unbind textures", self.debug_mode)

        if self.alpha_blending:
            glDisable(GL_BLEND)
        if self.depth_testing:
            glDisable(GL_DEPTH_TEST)
        check_gl_error("Depth testing teardown", self.debug_mode)
        if self.culling:
            glDisable(GL_CULL_FACE)
        check_gl_error("Culling teardown", self.debug_mode)

        return result

    return render_config


class AbstractRenderer(ABC):
    """
    AbstractRenderer provides a base class for renderers that set up shaders,
    load textures, manage shadow mapping and camera control, and render the
    scene. Concrete subclasses must implement create_buffers() and render().
    """

    def __init__(
        self,
        renderer_name,
        shader_names,
        shaders=None,
        texture_paths=None,
        cubemap_folder=None,
        camera_positions=None,
        fov=45,
        near_plane=0.1,
        far_plane=100,
        ambient_lighting_strength=0.0,
        ambient_lighting_color=(0.0, 0.0, 0.0),
        lights=None,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        texture_lod_bias=0.0,
        env_map_lod_bias=0.0,
        alpha_blending=False,
        depth_testing=True,
        culling=True,
        msaa_level=4,
        anisotropy=16,
        auto_camera=False,
        move_speed=1.0,
        loop=True,
        front_face_winding="CCW",
        window_size=(800, 600),
        invert_displacement_map=False,
        pom_height_scale=0.016,
        pom_min_steps=8,
        pom_max_steps=32,
        pom_eye_offset_scale=1.0,
        pom_max_depth_clamp=0.99,
        pom_max_forward_offset=1.0,
        pom_enable_frag_depth_adjustment=False,
        shadow_map_resolution=2048,
        shadow_strength=1.0,
        lighting_mode="diffuse",
        legacy_opacity=1.0,
        legacy_roughness=32,
        env_map_strength=0.5,
        distortion_strength=0.3,
        refraction_strength=0.3,
        distortion_warped=False,
        flip_planar_horizontally=False,
        flip_planar_vertically=False,
        use_planar_normal_distortion=False,
        planar_fragment_view_threshold=0.0,
        screen_texture=None,
        planar_camera=False,
        planar_resolution=(1024, 1024),
        planar_fov=45,
        planar_near_plane=0.1,
        planar_far_plane=100,
        planar_camera_position_rotation=(0, 0, 0, 0, 0),
        planar_relative_to_camera=False,
        planar_camera_lens_rotation=0.0,
        lens_rotations=None,
        screen_facing_planar_texture=False,
        debug_mode=False,
        **kwargs,
    ):
        # Identification and basic settings
        self.renderer_name = renderer_name
        self.debug_mode = debug_mode
        self.dynamic_attrs = kwargs
        self.identifier = self  # Identifier for texture manager keys

        # Planar rendering attributes
        self.flip_planar_horizontally = flip_planar_horizontally
        self.flip_planar_vertically = flip_planar_vertically
        self.use_planar_normal_distortion = use_planar_normal_distortion
        self.planar_fragment_view_threshold = planar_fragment_view_threshold
        self.planar_texture = None
        self.planar_framebuffer = None
        self.planar_camera_position = None
        self.planar_camera_rotation = None
        self.planar_view = None
        self.planar_projection = None

        # Environment mapping
        self.environmentMap = None

        # View and projection matrices
        self.view = None
        self.projection = None

        # Shader and texture configurations
        self.shader_names = shader_names
        self.shaders = shaders or {}
        self.texture_paths = texture_paths or {}
        self.cubemap_folder = cubemap_folder

        # Camera settings
        self.camera_positions = camera_positions or [(0, 0, 0, 0, 0)]
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane

        # Transformations
        self.translation = glm.vec3(0.0)
        self.rotation = glm.vec3(0.0)
        self.scaling = glm.vec3(1.0)
        self.model_matrix = glm.mat4(1)
        self.manual_transformations = glm.mat4(1)
        self.auto_rotation_enabled = False
        self.rotation_axis = glm.vec3(0, 0, 0)
        self.rotation_speed = 0.0

        # Texture and environment mapping LOD/bias settings
        self.texture_lod_bias = texture_lod_bias
        self.env_map_lod_bias = env_map_lod_bias

        # Render options
        self.alpha_blending = alpha_blending
        self.depth_testing = depth_testing
        self.culling = culling
        self.msaa_level = msaa_level
        self.anisotropy = anisotropy

        # Auto-camera settings
        self.auto_camera = auto_camera
        self.move_speed = move_speed
        self.loop = loop
        self.front_face_winding = self.get_winding_constant(front_face_winding)
        self.window_size = window_size

        # Parallax/Displacement mapping settings
        self.invert_displacement_map = invert_displacement_map
        self.pom_height_scale = pom_height_scale
        self.pom_min_steps = pom_min_steps
        self.pom_max_steps = pom_max_steps
        self.pom_eye_offset_scale = pom_eye_offset_scale
        self.pom_max_depth_clamp = pom_max_depth_clamp
        self.pom_max_forward_offset = pom_max_forward_offset
        self.pom_enable_frag_depth_adjustment = pom_enable_frag_depth_adjustment

        # Legacy material properties and environment map strength
        self.legacy_opacity = legacy_opacity
        self.legacy_roughness = legacy_roughness
        self.env_map_strength = env_map_strength

        # Distortion and refraction
        self.distortion_strength = distortion_strength
        self.refraction_strength = refraction_strength
        self.distortion_warped = distortion_warped

        # Planar camera options
        self.screen_texture = screen_texture
        self.planar_resolution = planar_resolution
        self.planar_fov = planar_fov
        self.planar_near_plane = planar_near_plane
        self.planar_far_plane = planar_far_plane
        self.planar_camera_position_rotation = planar_camera_position_rotation
        self.planar_relative_to_camera = planar_relative_to_camera
        self.planar_camera_lens_rotation = planar_camera_lens_rotation

        self.lens_rotations = lens_rotations or [planar_camera_lens_rotation]
        self.screen_facing_planar_texture = screen_facing_planar_texture
        self.screen_facing_planar_screenshotted = False
        self.screen_depth_map_screenshotted = False

        # Size of a float in bytes
        self.float_size = 4

        # Buffers
        self.vbos = []
        self.vaos = []

        # Shader engine placeholder
        self.shader_engine = None

        # Shadow mapping setup
        if shadow_map_resolution > 0:
            self.shadowing_enabled = True
            self.shadow_width = self.shadow_height = shadow_map_resolution
            self.shadow_map_manager = ShadowMapManager(shadow_width=self.shadow_width, shadow_height=self.shadow_height)
        else:
            self.shadowing_enabled = False
            self.shadow_map_manager = None
        self.shadow_strength = shadow_strength

        # Ambient lighting
        self.ambient_lighting_strength = ambient_lighting_strength
        self.ambient_lighting_color = glm.vec3(*ambient_lighting_color)

        # Additional colors and dynamic attributes
        self.water_base_color = glm.vec3(self.dynamic_attrs.get("water_base_color", (0.0, 0.0, 0.0)))
        self.lava_base_color = glm.vec3(self.dynamic_attrs.get("lava_base_color", (0.0, 0.0, 0.0)))
        self.lava_bright_color = glm.vec3(self.dynamic_attrs.get("lava_bright_color", (0.0, 0.0, 0.0)))
        self.dynamic_attrs.get("randomness", 0.8)

        # Lighting mode: map string to integer code.
        self.lighting_mode = {"diffuse": 0, "phong": 1, "pbr": 2}.get(lighting_mode, 0)

        # Light sources
        self.lights_enabled = lights is not None
        if self.lights_enabled:
            self.lights = [
                {
                    "position": glm.vec3(*light.get("position", (0, 0, 0))),
                    "color": glm.vec3(*light.get("color", (1.0, 1.0, 1.0))),
                    "strength": light.get("strength", 1.0),
                    "orth_left": light.get("orth_left", -10.0),
                    "orth_right": light.get("orth_right", 10.0),
                    "orth_bottom": light.get("orth_bottom", -10.0),
                    "orth_top": light.get("orth_top", 10.0),
                }
                for light in lights
            ]
        else:
            self.lights = []

        # Camera controller
        if self.auto_camera:
            self.camera_controller = CameraController(
                self.camera_positions,
                lens_rotations=self.lens_rotations,
                move_speed=self.move_speed,
                loop=self.loop,
            )
            self.camera_position, self.camera_rotation = self.camera_controller.update(0)
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            self.camera_controller = CameraController(self.camera_positions, lens_rotations=self.lens_rotations)
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]

        self.planar_camera = planar_camera
        if self.planar_camera:
            self.setup_planar_camera()

        # Store tone mapping and gamma correction flags (re-added)
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction

        # Initialize the list of auto-rotations.
        # Each element is a tuple: (axis, speed)
        # For example: [((0.0, 1.0, 0.0), 4000.0), ((1.0, 0.0, 0.0), 2000.0)]
        self.auto_rotations = []

    def get_winding_constant(self, winding: str):
        """
        Return the OpenGL constant corresponding to the front face winding.
        """
        winding_options = {"CW": GL_CW, "CCW": GL_CCW}
        if winding not in winding_options:
            raise ValueError("Invalid front_face_winding option. Use 'CW' or 'CCW'.")
        return winding_options[winding]

    def supports_shadow_mapping(self):
        """
        Indicates whether this renderer supports shadow mapping.
        """
        return self.shadowing_enabled

    def setup(self):
        """
        Initialize shaders, buffers, textures, camera, and constant uniforms.
        Optionally set up a debug framebuffer for depth map visualization.
        """
        self.init_shaders()
        self.create_buffers()
        self.load_textures()
        self.setup_camera()
        self.set_constant_uniforms()
        if self.debug_mode:
            self.init_depth_map_visualization_framebuffer()
            self.screen_taken = False

    def init_depth_map_visualization_framebuffer(self):
        """
        Setup a framebuffer for visualizing the depth map (for debugging purposes).
        """
        self.depth_vis_fbo = glGenFramebuffers(1)
        self.depth_vis_texture = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.depth_vis_texture)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGB, self.window_size[0], self.window_size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, None
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glBindFramebuffer(GL_FRAMEBUFFER, self.depth_vis_fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.depth_vis_texture, 0)

        # Attach a depth-stencil renderbuffer.
        rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, self.window_size[0], self.window_size[1])
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, rbo)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print("Error: Depth Map Visualization Framebuffer is not complete!")
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def render_shadow_map_visualization(self):
        """
        Reads the depth map texture and saves an 8-bit grayscale image for debugging.
        """
        glBindTexture(GL_TEXTURE_2D, self.shadow_map_manager.depth_map)
        width = self.shadow_map_manager.shadow_width
        height = self.shadow_map_manager.shadow_height

        depth_data = glGetTexImage(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, GL_FLOAT)
        depth_array = np.frombuffer(depth_data, dtype=np.float32).reshape(height, width)
        depth_image = (depth_array * 255).astype(np.uint8)
        image = Image.fromarray(depth_image)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        if not self.screen_depth_map_screenshotted:
            filename = f"renderer_{self.renderer_name}_depth_map.png"
            image_saver.save_image(image, filename)
            self.screen_depth_map_screenshotted = True
            print(f"Depth map visualization saved to '{os.path.join(screenshots_dir, filename)}'")

    def setup_planar_camera(self):
        """
        Set up the planar camera by creating a dedicated framebuffer and texture.
        """
        texture_unit = texture_manager.get_texture_unit(str(self.identifier), "planar_camera")
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        self.planar_framebuffer = glGenFramebuffers(1)
        self.planar_texture = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.planar_texture)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            self.planar_resolution[0],
            self.planar_resolution[1],
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            None,
        )
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

    def render_shadow_map(self, scene_renderers):
        """
        Render the scene from the light's perspective to build a shadow map.
        Only works if shadow mapping is enabled and lights are available.
        """
        if not self.shadowing_enabled or not self.lights_enabled:
            return

        glViewport(0, 0, self.shadow_width, self.shadow_height)
        glBindFramebuffer(GL_FRAMEBUFFER, self.shadow_map_manager.depth_map_fbo)
        glClear(GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glCullFace(GL_FRONT)

        light = self.lights[0]
        self.shadow_map_manager.setup(light, self.near_plane, self.far_plane)
        light_space_matrix = self.shadow_map_manager.light_space_matrix

        for renderer in scene_renderers:
            if renderer.supports_shadow_mapping():
                renderer.render_from_light(light_space_matrix)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glCullFace(GL_BACK)

    def render_planar_view(self, scene_renderers):
        """
        Render the scene from a planar camera perspective.
        If `planar_relative_to_camera` is True, the planar camera position is
        computed relative to the main camera's orientation.
        """
        if not self.planar_camera:
            return None

        main_cam_yaw = self.camera_rotation.x
        main_cam_pitch = self.camera_rotation.y
        combined_lens_rotation = self.main_camera_lens_rotation + self.planar_camera_lens_rotation
        offset_x, offset_y, offset_z, local_yaw_offset, local_pitch_offset = self.planar_camera_position_rotation

        if self.planar_relative_to_camera:
            self.planar_camera_position = self.translation + glm.vec3(offset_x, offset_y, offset_z)
            final_yaw = main_cam_yaw + local_yaw_offset
            final_pitch = main_cam_pitch + local_pitch_offset
            self.planar_camera_rotation = glm.vec2(final_yaw, final_pitch)
        else:
            self.planar_camera_position = self.translation + glm.vec3(offset_x, offset_y, offset_z)
            final_yaw = local_yaw_offset
            final_pitch = local_pitch_offset
            self.planar_camera_rotation = glm.vec2(final_yaw, final_pitch)

        rotation_matrix = glm.mat4(1.0)
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(final_yaw), glm.vec3(0.0, 1.0, 0.0))
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(final_pitch), glm.vec3(1.0, 0.0, 0.0))
        forward_dir = glm.vec3(rotation_matrix * glm.vec4(0.0, 0.0, -1.0, 0.0))
        planar_target = self.planar_camera_position + forward_dir
        up_vector = glm.vec3(0.0, 1.0, 0.0)
        self.planar_view = glm.lookAt(self.planar_camera_position, planar_target, up_vector)
        lens_rotation_matrix = glm.rotate(glm.mat4(1.0), glm.radians(combined_lens_rotation), forward_dir)
        self.planar_view = lens_rotation_matrix * self.planar_view

        aspect_ratio = self.planar_resolution[0] / self.planar_resolution[1]
        self.planar_projection = glm.perspective(
            glm.radians(self.planar_fov), aspect_ratio, self.planar_near_plane, self.planar_far_plane
        )

        scene_renderers = [r for r in scene_renderers if r is not self]
        glBindFramebuffer(GL_FRAMEBUFFER, self.planar_framebuffer)
        glViewport(0, 0, self.planar_resolution[0], self.planar_resolution[1])
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for renderer in scene_renderers:
            renderer.render_with_custom_camera(self.planar_view, self.planar_projection)

        if self.debug_mode and not self.screen_facing_planar_screenshotted:
            glBindTexture(GL_TEXTURE_2D, self.screen_texture)
            data = glReadPixels(0, 0, self.planar_resolution[0], self.planar_resolution[1], GL_RGB, GL_UNSIGNED_BYTE)
            image = Image.frombytes("RGB", self.planar_resolution, data)
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"renderer_{self.renderer_name}_screen_texture_{timestamp}.png"
            image_saver.save_image(image, filename)
            self.screen_facing_planar_screenshotted = True

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.window_size[0], self.window_size[1])
        glBindTexture(GL_TEXTURE_2D, 0)

    def render_with_custom_camera(self, view_matrix, projection_matrix):
        """
        Render using a custom view and projection matrix.
        :param view_matrix: The view matrix to use.
        :param projection_matrix: The projection matrix to use.
        """
        self.view = view_matrix
        self.projection = projection_matrix
        self.render()

    def render_from_light(self, light_space_matrix):
        """
        Render the object from the light's perspective to populate the shadow map.
        :param light_space_matrix: The light-space transformation matrix.
        """
        self.apply_transformations()
        self.shader_engine.use_shadow_shader_program()
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shadow_shader_program, "model"),
            1,
            GL_FALSE,
            glm.value_ptr(self.model_matrix),
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shadow_shader_program, "lightSpaceMatrix"),
            1,
            GL_FALSE,
            glm.value_ptr(light_space_matrix),
        )

        if hasattr(self, "object") and hasattr(self.object, "mesh_list"):
            for i, mesh in enumerate(self.object.mesh_list):
                if hasattr(mesh, "materials"):
                    vao_counter = 0
                    for material in mesh.materials:
                        vertices = material.vertices
                        if not vertices:
                            continue
                        count = len(vertices) // self.get_vertex_stride(material.vertex_format)
                        if vao_counter < len(self.vaos):
                            glBindVertexArray(self.vaos[vao_counter])
                            glDrawArrays(GL_TRIANGLES, 0, count)
                            glBindVertexArray(0)
                        else:
                            print("Warning: VAO index out of range for mesh list.")
                        vao_counter += 1
                else:
                    if i < len(self.vaos):
                        glBindVertexArray(self.vaos[i])
                        glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
                        glBindVertexArray(0)
                    else:
                        print("Warning: VAO index out of range for mesh list.")
        else:
            if hasattr(self, "materials") and hasattr(self, "vertex_counts"):
                for material, vao, count in zip(self.materials, self.vaos, self.vertex_counts):
                    if count == 0:
                        continue
                    glBindVertexArray(vao)
                    glDrawArrays(GL_TRIANGLES, 0, count)
                    glBindVertexArray(0)
            else:
                print("No mesh_list or materials/vertex_counts to render from light.")

        if self.debug_mode:
            self.render_shadow_map_visualization()

    def init_shaders(self):
        """
        Initialize the main and shadow mapping shader programs.
        """
        vertex_shader_path = self.shaders.get("vertex", {}).get(self.shader_names.get("vertex"))
        fragment_shader_path = self.shaders.get("fragment", {}).get(self.shader_names.get("fragment"))
        compute_shader_path = self.shaders.get("compute", {}).get(self.shader_names.get("compute"))
        shadow_vertex_shader_path = None
        shadow_fragment_shader_path = None
        if self.shadowing_enabled:
            shadow_vertex_shader_path = self.shaders.get("vertex", {}).get("shadow_mapping")
            shadow_fragment_shader_path = self.shaders.get("fragment", {}).get("shadow_mapping")

        self.shader_engine = ShaderEngine(
            vertex_shader_path,
            fragment_shader_path,
            compute_shader_path,
            shadow_vertex_shader_path,
            shadow_fragment_shader_path,
        )

    def load_textures(self):
        """
        Load the diffuse, normal, and displacement textures (if provided)
        and set up the environment cubemap.
        """
        self.shader_engine.use_shader_program()
        if self.texture_paths:
            self.load_and_set_texture("diffuse", "diffuseMap")
            self.load_and_set_texture("normal", "normalMap")
            self.load_and_set_texture("displacement", "displacementMap")

        self.environmentMap = glGenTextures(1)
        env_map_unit = texture_manager.get_texture_unit(str(self.identifier), "environment")
        glActiveTexture(GL_TEXTURE0 + env_map_unit)
        if self.cubemap_folder:
            self.load_cubemap(self.cubemap_folder, self.environmentMap)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "environmentMap"), env_map_unit)

    def load_and_set_texture(self, texture_type, uniform_name):
        """
        Helper method to load a texture from the provided path and assign it
        to the corresponding uniform.
        :param texture_type: A key in texture_paths (e.g. "diffuse").
        :param uniform_name: The name of the uniform in the shader.
        """
        texture_map = glGenTextures(1)
        texture_unit = texture_manager.get_texture_unit(str(self.identifier), texture_type)
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        self.load_texture(self.texture_paths[texture_type], texture_map)
        glBindTexture(GL_TEXTURE_2D, texture_map)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, uniform_name), texture_unit)

    def load_texture(self, path, texture):
        """
        Load an image using pygame, convert it to a string, and create an OpenGL texture.
        :param path: File path to the image.
        :param texture: OpenGL texture handle.
        """
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

    def load_cubemap(self, folder_path, texture):
        """
        Load a cubemap from a folder containing 6 face images.
        :param folder_path: Path to the folder containing the cubemap faces.
        :param texture: OpenGL texture handle.
        """
        faces = ["right.png", "left.png", "top.png", "bottom.png", "front.png", "back.png"]
        glBindTexture(GL_TEXTURE_CUBE_MAP, texture)
        for i, face in enumerate(faces):
            face_path = os.path.join(folder_path, face)
            surface = pygame.image.load(face_path)
            surface = pygame.transform.flip(surface, False, True)
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
        """
        Setup the main camera. If auto_camera is enabled, use the CameraController
        to update the position/rotation; otherwise, use the first camera position.
        Then, compute the view and projection matrices.
        """
        if self.auto_camera:
            self.camera_controller = CameraController(
                self.camera_positions, lens_rotations=self.lens_rotations, move_speed=self.move_speed, loop=self.loop
            )
            self.camera_position, self.camera_rotation = self.camera_controller.update(0)
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            self.camera_controller = CameraController(self.camera_positions, lens_rotations=self.lens_rotations)
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]

        self.setup_camera_matrices()

    def setup_camera_matrices(self):
        """
        Compute the view and projection matrices based on camera position, rotation,
        and lens rotation.
        """
        aspect_ratio = self.window_size[0] / self.window_size[1]
        yaw, pitch = self.camera_rotation[0], self.camera_rotation[1]

        rotation_matrix = glm.mat4(1.0)
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(yaw), glm.vec3(0.0, 1.0, 0.0))
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(pitch), glm.vec3(1.0, 0.0, 0.0))

        forward_direction = glm.vec3(rotation_matrix * glm.vec4(0.0, 0.0, -1.0, 0.0))
        up_vector = glm.vec3(0.0, 1.0, 0.0)

        self.view = glm.lookAt(self.camera_position, self.camera_position + forward_direction, up_vector)
        lens_rotation_matrix = glm.rotate(glm.mat4(1.0), glm.radians(self.main_camera_lens_rotation), forward_direction)
        self.view = lens_rotation_matrix * self.view

        self.projection = glm.perspective(glm.radians(self.fov), aspect_ratio, self.near_plane, self.far_plane)

    def set_light_uniforms(self, shader_program):
        """
        Set light-related uniforms in the shader.
        """
        self.shader_engine.use_shader_program()
        for i, light in enumerate(self.lights):
            glUniform3fv(
                glGetUniformLocation(shader_program, f"lightPositions[{i}]"), 1, glm.value_ptr(light["position"])
            )
            glUniform3fv(glGetUniformLocation(shader_program, f"lightColors[{i}]"), 1, glm.value_ptr(light["color"]))
            glUniform1f(glGetUniformLocation(shader_program, f"lightStrengths[{i}]"), light["strength"])
            glUniform1f(glGetUniformLocation(shader_program, f"lightOrthoLeft[{i}]"), light["orth_left"])
            glUniform1f(glGetUniformLocation(shader_program, f"lightOrthoRight[{i}]"), light["orth_right"])
            glUniform1f(glGetUniformLocation(shader_program, f"lightOrthoBottom[{i}]"), light["orth_bottom"])
            glUniform1f(glGetUniformLocation(shader_program, f"lightOrthoTop[{i}]"), light["orth_top"])
        glUniform1i(glGetUniformLocation(shader_program, "lightingMode"), self.lighting_mode)

    def set_model_matrix(self, matrix):
        """
        Set the object's model matrix.
        """
        self.model_matrix = matrix

    def translate(self, position):
        """
        Translate the object.
        :param position: A tuple or list of (x, y, z) coordinates.
        """
        self.translation = glm.vec3(*position)
        self.update_model_matrix()

    def rotate_euler(self, angles_deg):
        """
        Set the object's rotation using Euler angles in degrees.
        :param angles_deg: Tuple of (xDeg, yDeg, zDeg).
        """
        xDeg, yDeg, zDeg = angles_deg
        self.rotation.x = glm.radians(xDeg)
        self.rotation.y = glm.radians(yDeg)
        self.rotation.z = glm.radians(zDeg)
        self.update_model_matrix()

    def rotate(self, angle, axis):
        """
        Rotate the object by a given angle around a specified axis.
        :param angle: Angle in degrees.
        :param axis: Tuple or list representing the (x, y, z) axis.
        """
        self.rotation = glm.vec3(*axis) * glm.radians(angle)
        self.update_model_matrix()

    def scale(self, scale):
        """
        Scale the object.
        :param scale: Tuple or list representing scaling factors in (x, y, z).
        """
        self.scaling = glm.vec3(*scale)
        self.update_model_matrix()

    def update_model_matrix(self):
        """
        Recompute the model matrix based on current translation, rotation, and scaling.
        """
        self.manual_transformations = glm.translate(glm.mat4(1), self.translation)
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.x, glm.vec3(1, 0, 0))
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.y, glm.vec3(0, 1, 0))
        self.manual_transformations = glm.rotate(self.manual_transformations, self.rotation.z, glm.vec3(0, 0, 1))
        self.manual_transformations = glm.scale(self.manual_transformations, self.scaling)

    def apply_transformations(self):
        """
        Apply manual transformations (translation, initial rotation, scaling)
        and then apply any auto-rotations. The auto-rotations are applied in sequence
        (the order of rotations in the list matters).
        """
        # self.manual_transformations was computed by update_model_matrix()
        if self.auto_rotations:
            auto_matrix = glm.mat4(1.0)
            # For each auto rotation, compute an incremental rotation matrix and multiply them
            for axis, speed in self.auto_rotations:
                # Here, we compute an angle based on time (you might wish to adjust the divisor)
                angle = pygame.time.get_ticks() / speed
                auto_matrix = auto_matrix * glm.rotate(glm.mat4(1.0), angle, glm.vec3(*axis))
            self.model_matrix = self.manual_transformations * auto_matrix
        else:
            self.model_matrix = self.manual_transformations

    def enable_auto_rotation(self, enabled=False, axis=None, speed=None, rotations=None):
        """
        Enable or disable automatic rotation.

        If rotations is provided, it should be a list of (axis, speed) tuples.
        Otherwise, if enabled is True and axis and speed are provided, then a single auto-rotation is set.
        If none of these conditions are met, auto-rotation is disabled.

        Example usage:
          # For a single auto rotation:
          r.enable_auto_rotation(enabled=True, axis=(0.0, 1.0, 0.0), speed=4000.0)

          # For multiple auto rotations:
          r.enable_auto_rotation(rotations=[((0.0, 1.0, 0.0), 4000.0), ((1.0, 0.0, 0.0), 2000.0)])
        """
        if rotations is not None:
            self.auto_rotations = rotations
        elif enabled and axis is not None and speed is not None:
            self.auto_rotations = [(axis, speed)]
        else:
            self.auto_rotations = []

    def set_constant_uniforms(self):
        """
        Set uniforms that remain constant for the shader program.
        """
        self.shader_engine.use_shader_program()
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "textureLodLevel"), self.texture_lod_bias)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "envMapLodLevel"), self.env_map_lod_bias)
        # Re-added tone mapping and gamma correction flags:
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "applyToneMapping"), self.apply_tone_mapping
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "applyGammaCorrection"), self.apply_gamma_correction
        )

    def set_shader_uniforms(self):
        """
        Set various dynamic uniforms in the shader including model, view, projection,
        parallax mapping parameters, lighting, and material properties.
        """
        self.shader_engine.use_shader_program()

        # --- Model, View, Projection ---
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "model"),
            1,
            GL_FALSE,
            glm.value_ptr(self.model_matrix),
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "view"), 1, GL_FALSE, glm.value_ptr(self.view)
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "projection"),
            1,
            GL_FALSE,
            glm.value_ptr(self.projection),
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "nearPlane"), self.near_plane)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "farPlane"), self.far_plane)

        # --- Shadow Mapping ---
        if self.shadow_map_manager and self.shadowing_enabled and self.lights_enabled:
            glUniformMatrix4fv(
                glGetUniformLocation(self.shader_engine.shader_program, "lightSpaceMatrix"),
                1,
                GL_FALSE,
                glm.value_ptr(self.shadow_map_manager.light_space_matrix),
            )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "shadowingEnabled"), int(self.shadowing_enabled)
        )

        # --- Parallax Mapping ---
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "invertDisplacementMap"),
            int(self.invert_displacement_map),
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "pomHeightScale"), self.pom_height_scale)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "pomMinSteps"), self.pom_min_steps)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "pomMaxSteps"), self.pom_max_steps)
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "parallaxEyeOffsetScale"), self.pom_eye_offset_scale
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "parallaxMaxDepthClamp"), self.pom_max_depth_clamp
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "maxForwardOffset"), self.pom_max_forward_offset
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "enableFragDepthAdjustment"),
            int(self.pom_enable_frag_depth_adjustment),
        )

        # --- Ambient and Material ---
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "ambientStrength"), self.ambient_lighting_strength
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "ambientColor"),
            1,
            glm.value_ptr(self.ambient_lighting_color),
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "legacyOpacity"), self.legacy_opacity)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "legacyRoughness"), self.legacy_roughness)
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "environmentMapStrength"), self.env_map_strength
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "distortionStrength"), self.distortion_strength
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "refractionStrength"), self.refraction_strength
        )

        # --- Screen and Planar Texture ---
        glUniform2f(
            glGetUniformLocation(self.shader_engine.shader_program, "screenResolution"),
            self.window_size[0],
            self.window_size[1],
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "flipPlanarHorizontal"),
            int(self.flip_planar_horizontally),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "flipPlanarVertical"),
            int(self.flip_planar_vertically),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "usePlanarNormalDistortion"),
            int(self.use_planar_normal_distortion),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "planarFragmentViewThreshold"),
            self.planar_fragment_view_threshold,
        )
        if self.screen_texture:
            screen_texture_unit = texture_manager.get_texture_unit(str(self.identifier), "planar_camera")
            glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "screenTexture"), screen_texture_unit)
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "screenFacingPlanarTexture"),
            int(self.screen_facing_planar_texture),
        )

        # --- Dynamic Material and Effects ---
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "useCheckerPattern"),
            int(self.dynamic_attrs.get("use_checker_pattern", 1)),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "waterBaseColor"),
            1,
            glm.value_ptr(self.water_base_color),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "lavaBaseColor"),
            1,
            glm.value_ptr(self.lava_base_color),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "lavaBrightColor"),
            1,
            glm.value_ptr(self.lava_bright_color),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "waveSpeed"),
            self.dynamic_attrs.get("wave_speed", 10.0),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "waveAmplitude"),
            self.dynamic_attrs.get("wave_amplitude", 0.1),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "waveDetail"),
            self.dynamic_attrs.get("wave_detail", 10.0),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "randomness"),
            self.dynamic_attrs.get("randomness", 0.8),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "texCoordFrequency"),
            self.dynamic_attrs.get("tex_coord_frequency", 100.0),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "texCoordAmplitude"),
            self.dynamic_attrs.get("tex_coord_amplitude", 0.1),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "surfaceDepth"),
            self.dynamic_attrs.get("surface_depth", 0.0),
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "shadowStrength"), self.shadow_strength)
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "cameraPos"), 1, glm.value_ptr(self.camera_position)
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "time"), pygame.time.get_ticks() / 1000.0)

    def create_dummy_texture(self):
        """
        Create a dummy texture (1x1 white) to use when no valid shadow map is available.
        """
        dummy_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, dummy_texture)
        data = np.array([1.0], dtype=np.float32)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, 1, 1, 0, GL_DEPTH_COMPONENT, GL_FLOAT, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return dummy_texture

    def set_shadow_shader_uniforms(self):
        """
        Set uniforms related to shadow mapping. Bind the actual shadow map if available;
        otherwise, bind a dummy texture.
        """
        self.shader_engine.use_shader_program()
        shadow_map_unit = texture_manager.get_texture_unit(str(self.identifier), "shadow_map")
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "shadowMap"), shadow_map_unit)
        glActiveTexture(GL_TEXTURE0 + shadow_map_unit)

        if self.shadow_map_manager and self.shadowing_enabled and self.lights_enabled:
            glUniformMatrix4fv(
                glGetUniformLocation(self.shader_engine.shader_program, "lightSpaceMatrix"),
                1,
                GL_FALSE,
                glm.value_ptr(self.shadow_map_manager.light_space_matrix),
            )
            glUniform3fv(
                glGetUniformLocation(self.shader_engine.shader_program, "lightPosition"),
                1,
                glm.value_ptr(self.lights[0]["position"]),
            )
            glBindTexture(GL_TEXTURE_2D, self.shadow_map_manager.depth_map)
        else:
            dummy_texture = texture_manager.get_dummy_texture()
            glBindTexture(GL_TEXTURE_2D, dummy_texture)

    def update_camera(self, delta_time):
        """
        Update the camera based on delta time using the CameraController.
        """
        if self.auto_camera:
            self.camera_position, self.camera_rotation = self.camera_controller.update(delta_time)
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]
        self.setup_camera_matrices()

    def shutdown(self):
        """
        Clean up OpenGL resources (VAOs, VBOs, shader programs).
        """
        if hasattr(self, "vaos") and len(self.vaos) > 0:
            glDeleteVertexArrays(len(self.vaos), self.vaos)
        if hasattr(self, "vbos") and len(self.vbos) > 0:
            glDeleteBuffers(len(self.vbos), self.vbos)
        self.shader_engine.delete_shader_programs()

    @abstractmethod
    def create_buffers(self):
        """
        Abstract method: subclasses should implement creation of VBOs/VAOs.
        """
        pass

    @abstractmethod
    def render(self):
        """
        Abstract method: subclasses should implement the actual render logic.
        """
        pass
