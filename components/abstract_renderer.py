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

texture_manager = TextureManager()

image_saver = ImageSaver(screenshots_dir="screenshots")


def check_gl_error(context, debug_mode):
    if debug_mode:
        gl_error = glGetError()
        if gl_error != GL_NO_ERROR:
            raise RuntimeError(f"OpenGL error in {context}: {gl_error}")


def common_funcs(func):
    def render_config(self, *args, **kwargs):
        self.shader_engine.use_shader_program()
        check_gl_error("glUseProgram", self.debug_mode)

        # Enable alpha blending
        if self.alpha_blending:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        else:
            glDisable(GL_BLEND)

        # Depth testing setup
        if self.depth_testing:
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)
        check_gl_error("Depth testing setup", self.debug_mode)

        view_position = self.camera_position
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "viewPosition"), 1, glm.value_ptr(view_position)
        )
        check_gl_error("Setting viewPosition uniform", self.debug_mode)

        # Culling setup
        if self.culling:
            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)
            glFrontFace(self.front_face_winding)
        else:
            glDisable(GL_CULL_FACE)
        check_gl_error("Culling setup", self.debug_mode)

        self.apply_transformations()
        check_gl_error("apply_transformations", self.debug_mode)

        # **Call set_light_uniforms before set_shader_uniforms and set_shadow_shader_uniforms**
        if self.lights_enabled:
            self.set_light_uniforms(self.shader_engine.shader_program)
        check_gl_error("set_light_uniforms", self.debug_mode)

        self.set_shader_uniforms()
        check_gl_error("set_shader_uniforms", self.debug_mode)

        self.set_shadow_shader_uniforms()
        check_gl_error("set_shadow_shader_uniforms", self.debug_mode)

        result = func(self, *args, **kwargs)
        check_gl_error("render function", self.debug_mode)

        # Unbind textures
        glBindTexture(GL_TEXTURE_2D, 0)
        check_gl_error("Unbind textures", self.debug_mode)

        # Disable alpha blending
        if self.alpha_blending:
            glDisable(GL_BLEND)

        # Depth testing teardown
        if self.depth_testing:
            glDisable(GL_DEPTH_TEST)
        check_gl_error("Depth testing teardown", self.debug_mode)

        # Culling teardown
        if self.culling:
            glDisable(GL_CULL_FACE)
        check_gl_error("Culling teardown", self.debug_mode)

        return result

    return render_config


class AbstractRenderer(ABC):
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
        pom_height_scale=0.04,
        pom_min_steps=8,
        pom_max_steps=32,
        shadow_map_resolution=2048,
        phong_shading=False,
        opacity=1.0,
        shininess=1.0,
        env_map_strength=0.5,
        distortion_strength=0.3,
        reflection_strength=0.0,
        distortion_warped=False,
            flip_planar_horizontally=False,
            flip_planar_vertically=False,
            use_planar_normal_distortion=False,
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
        self.renderer_name = renderer_name

        self.flip_planar_horizontally = flip_planar_horizontally
        self.flip_planar_vertically = flip_planar_vertically
        self.use_planar_normal_distortion = use_planar_normal_distortion
        self.planar_texture = None
        self.planar_framebuffer = None
        self.planar_camera_position = None
        self.planar_camera_rotation = None
        self.planar_view = None
        self.planar_projection = None
        self.environmentMap = None
        self.view = None
        self.projection = None
        self.identifier = self

        # Proceed with other initializations
        self.debug_mode = debug_mode
        self.dynamic_attrs = kwargs

        self.shader_names = shader_names
        self.shaders = shaders or {}
        self.texture_paths = texture_paths or {}
        self.cubemap_folder = cubemap_folder
        self.camera_positions = camera_positions or [(0, 0, 0, 0, 0)]
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.rotation_axis = glm.vec3(0, 0, 0)
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction
        self.model_matrix = glm.mat4(1)
        self.manual_transformations = glm.mat4(1)
        self.translation = glm.vec3(0.0)
        self.rotation = glm.vec3(0.0)
        self.scaling = glm.vec3(1.0)
        self.auto_rotation_enabled = False
        self.rotation_speed = 0.0
        self.texture_lod_bias = texture_lod_bias
        self.env_map_lod_bias = env_map_lod_bias
        self.alpha_blending = alpha_blending
        self.depth_testing = depth_testing
        self.culling = culling
        self.msaa_level = msaa_level
        self.anisotropy = anisotropy
        self.auto_camera = auto_camera
        self.move_speed = move_speed
        self.loop = loop
        self.front_face_winding = self.get_winding_constant(front_face_winding)
        self.window_size = window_size

        # Parallax mapping attributes
        self.invert_displacement_map = invert_displacement_map
        self.pom_height_scale = pom_height_scale
        self.pom_min_steps = pom_min_steps
        self.pom_max_steps = pom_max_steps

        self.opacity = opacity
        self.shininess = shininess
        self.env_map_strength = env_map_strength
        self.distortion_strength = distortion_strength
        self.reflection_strength = reflection_strength
        self.distortion_warped = distortion_warped

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

        self.float_size = 4  # Size of a float in bytes

        self.vbos = []
        self.vaos = []

        self.shader_engine = None

        if shadow_map_resolution > 0:
            self.shadowing_enabled = True
            self.shadow_width = self.shadow_height = shadow_map_resolution
            self.shadow_map_manager = ShadowMapManager(shadow_width=self.shadow_width, shadow_height=self.shadow_height)
        else:
            self.shadowing_enabled = False
            self.shadow_map_manager = None  # Shadows are disabled

        self.ambient_lighting_strength = ambient_lighting_strength
        self.ambient_lighting_color = glm.vec3(*ambient_lighting_color)

        self.phong_shading = phong_shading

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

        if self.auto_camera:
            # Pass lens_rotations to the CameraController
            self.camera_controller = CameraController(
                self.camera_positions, lens_rotations=self.lens_rotations, move_speed=self.move_speed, loop=self.loop
            )
            self.camera_position, self.camera_rotation = self.camera_controller.update(0)
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            # Pass lens_rotations to the CameraController even if auto_camera is False
            self.camera_controller = CameraController(self.camera_positions, lens_rotations=self.lens_rotations)
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]

        self.planar_camera = planar_camera
        if self.planar_camera:
            self.setup_planar_camera()

    def supports_shadow_mapping(self):
        """Indicates whether this renderer supports shadow mapping."""
        return self.shadowing_enabled

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
        if self.debug_mode:
            self.init_depth_map_visualization_framebuffer()
            self.screen_taken = False

    def init_depth_map_visualization_framebuffer(self):
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

        # Optionally attach a depth buffer
        rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, self.window_size[0], self.window_size[1])
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, rbo)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print("Error: Depth Map Visualization Framebuffer is not complete!")
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def render_shadow_map_visualization(self):
        # Ensure the depth map has been rendered before this function is called.

        # Bind the depth map texture
        glBindTexture(GL_TEXTURE_2D, self.shadow_map_manager.depth_map)

        # Read the depth texture data
        width = self.shadow_map_manager.shadow_width
        height = self.shadow_map_manager.shadow_height

        # Create a buffer to store the depth data
        depth_data = glGetTexImage(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, GL_FLOAT)

        # Convert the data to a NumPy array
        depth_array = np.frombuffer(depth_data, dtype=np.float32).reshape(height, width)

        # Optionally normalize the depth values to [0, 1] if they are not already
        # depth_array = (depth_array - depth_array.min()) / (depth_array.max() - depth_array.min())

        # Map the depth values to an 8-bit grayscale image
        depth_image = (depth_array * 255).astype(np.uint8)

        # Convert the NumPy array to an image using PIL
        image = Image.fromarray(depth_image)

        # Flip the image vertically to match OpenGL's coordinate system
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        if not self.screen_depth_map_screenshotted:
            filename = f"renderer_{self.renderer_name}_depth_map.png"
            image_saver.save_image(image, filename)
            self.screen_depth_map_screenshotted = True
            print(f"Depth map visualization saved to '{screenshots_dir}{filename}'")

    def setup_planar_camera(self):
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
        if not self.shadowing_enabled or not self.lights_enabled:
            return

        # Setup shadow map framebuffer and viewport
        glViewport(0, 0, self.shadow_width, self.shadow_height)
        glBindFramebuffer(GL_FRAMEBUFFER, self.shadow_map_manager.depth_map_fbo)
        glClear(GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glCullFace(GL_FRONT)  # Optional: to prevent shadow acne

        # Setup light space matrix
        light = self.lights[0]
        self.shadow_map_manager.setup(light, self.near_plane, self.far_plane)
        light_space_matrix = self.shadow_map_manager.light_space_matrix

        # Render the scene from the light's perspective
        # Exclude self to avoid rendering the object twice
        for renderer in scene_renderers:
            if renderer.supports_shadow_mapping():
                renderer.render_from_light(light_space_matrix)

        # Unbind the framebuffer and reset state
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glCullFace(GL_BACK)

    def render_planar_view(self, scene_renderers):
        """
        Renders the scene from a 'planar camera' perspective, if enabled.

        If `planar_relative_to_camera` == True:
          - The planar camera always stays at (object_position + planar_camera_position_rotation[:3]) in world space.
          - Yaw/pitch = main camera's yaw/pitch + local offsets from planar_camera_position_rotation[3:].
          - The lens rotation is also combined with main camera lens rotation.
        """
        if not self.planar_camera:
            return None

        # 1) Extract main camera yaw/pitch
        main_cam_yaw = self.camera_rotation.x
        main_cam_pitch = self.camera_rotation.y

        # 2) Combine lens rotations
        combined_lens_rotation = self.main_camera_lens_rotation + self.planar_camera_lens_rotation

        # 3) Parse your planar offset + local yaw/pitch
        offset_x, offset_y, offset_z, local_yaw_offset, local_pitch_offset = self.planar_camera_position_rotation

        # 4) If planar_relative_to_camera, we keep the position from the object + offset,
        #    but track the main camera's orientation for yaw/pitch.
        if self.planar_relative_to_camera:
            # Position is object translation + offset (no rotation of offset!)
            self.planar_camera_position = self.translation + glm.vec3(offset_x, offset_y, offset_z)

            # final_yaw/pitch = main cam yaw/pitch + local offsets
            final_yaw = main_cam_yaw + local_yaw_offset
            final_pitch = main_cam_pitch + local_pitch_offset
            self.planar_camera_rotation = glm.vec2(final_yaw, final_pitch)

        else:
            # fallback to original logic if not relative to camera
            self.planar_camera_position = self.translation + glm.vec3(offset_x, offset_y, offset_z)
            # We do not attach to main camera orientation
            final_yaw = local_yaw_offset
            final_pitch = local_pitch_offset
            self.planar_camera_rotation = glm.vec2(final_yaw, final_pitch)

        # 5) Build orientation from the final yaw/pitch
        rotation_matrix = glm.mat4(1.0)
        # Yaw about Y
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(final_yaw), glm.vec3(0.0, 1.0, 0.0))
        # Pitch about X
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(final_pitch), glm.vec3(1.0, 0.0, 0.0))

        # The planar camera looks down the -Z axis after applying yaw/pitch
        forward_dir = glm.vec3(rotation_matrix * glm.vec4(0.0, 0.0, -1.0, 0.0))

        # 6) Build the lookAt
        planar_target = self.planar_camera_position + forward_dir
        up_vector = glm.vec3(0.0, 1.0, 0.0)
        self.planar_view = glm.lookAt(self.planar_camera_position, planar_target, up_vector)

        # 7) Apply combined lens rotation around forward_dir
        lens_rotation_matrix = glm.rotate(glm.mat4(1.0), glm.radians(combined_lens_rotation), forward_dir)
        self.planar_view = lens_rotation_matrix * self.planar_view

        # 8) Planar projection
        aspect_ratio = self.planar_resolution[0] / self.planar_resolution[1]
        self.planar_projection = glm.perspective(
            glm.radians(self.planar_fov),
            aspect_ratio,
            self.planar_near_plane,
            self.planar_far_plane
        )

        # 9) Render
        # Filter out self
        scene_renderers = [r for r in scene_renderers if r is not self]

        glBindFramebuffer(GL_FRAMEBUFFER, self.planar_framebuffer)
        glViewport(0, 0, self.planar_resolution[0], self.planar_resolution[1])
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for renderer in scene_renderers:
            renderer.render_with_custom_camera(self.planar_view, self.planar_projection)

        # Optional read-back for debugging
        if self.debug_mode and not self.screen_facing_planar_screenshotted:
            glBindTexture(GL_TEXTURE_2D, self.screen_texture)
            data = glReadPixels(
                0, 0,
                self.planar_resolution[0], self.planar_resolution[1],
                GL_RGB, GL_UNSIGNED_BYTE
            )
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
        self.view = view_matrix
        self.projection = projection_matrix
        self.render()

    def render_from_light(self, light_space_matrix):
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

        # Check if this renderer uses an object with mesh_list (like ModelRenderer or SurfaceRenderer)
        if hasattr(self, "object") and hasattr(self.object, "mesh_list"):
            # Try the model-like approach first:
            # Model-like meshes (from pywavefront) have 'materials'
            # Surfaces don't have 'materials', just a single mesh with vertices/faces.

            for i, mesh in enumerate(self.object.mesh_list):
                # Check if mesh has materials attribute
                if hasattr(mesh, "materials"):
                    # Model mesh: iterate over materials
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
                    # Surface-like mesh: no materials, just a single set of vertices/faces
                    if i < len(self.vaos):
                        glBindVertexArray(self.vaos[i])
                        glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
                        glBindVertexArray(0)
                    else:
                        print("Warning: VAO index out of range for mesh list.")
        else:
            # If this renderer doesn't have an object with mesh_list,
            # check if it has materials/vertex_counts
            if hasattr(self, "materials") and hasattr(self, "vertex_counts"):
                for material, vao, count in zip(self.materials, self.vaos, self.vertex_counts):
                    if count == 0:
                        continue
                    glBindVertexArray(vao)
                    glDrawArrays(GL_TRIANGLES, 0, count)
                    glBindVertexArray(0)
            else:
                # If neither approach works, print a warning or handle gracefully.
                print("No mesh_list or materials/vertex_counts to render from light.")

        if self.debug_mode:
            self.render_shadow_map_visualization()

    def init_shaders(self):
        vertex_shader_path = None
        fragment_shader_path = None
        compute_shader_path = None
        shadow_vertex_shader_path = None
        shadow_fragment_shader_path = None

        if "vertex" in self.shader_names:
            vertex_shader_path = self.shaders["vertex"].get(self.shader_names["vertex"])
        if "fragment" in self.shader_names:
            fragment_shader_path = self.shaders["fragment"].get(self.shader_names["fragment"])
        if "compute" in self.shader_names:
            compute_shader_path = self.shaders["compute"].get(self.shader_names["compute"])
        if self.shadowing_enabled:
            shadow_vertex_shader_path = self.shaders["vertex"].get("shadow_mapping")
            shadow_fragment_shader_path = self.shaders["fragment"].get("shadow_mapping")

        self.shader_engine = ShaderEngine(
            vertex_shader_path,
            fragment_shader_path,
            compute_shader_path,
            shadow_vertex_shader_path,
            shadow_fragment_shader_path,
        )

    def load_textures(self):
        """Load textures for the model."""
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
        """Helper method to load a texture and set the corresponding uniform."""
        texture_map = glGenTextures(1)
        texture_unit = texture_manager.get_texture_unit(str(self.identifier), texture_type)
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        self.load_texture(self.texture_paths[texture_type], texture_map)
        glBindTexture(GL_TEXTURE_2D, texture_map)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, uniform_name), texture_unit)

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

    def load_cubemap(self, folder_path, texture):
        faces = ["right.png", "left.png", "top.png", "bottom.png", "front.png", "back.png"]
        glBindTexture(GL_TEXTURE_CUBE_MAP, texture)
        for i, face in enumerate(faces):
            surface = pygame.image.load(folder_path + face)
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
        """Setup camera position and rotation."""
        if self.auto_camera:
            self.camera_controller = CameraController(
                self.camera_positions, lens_rotations=self.lens_rotations, move_speed=self.move_speed, loop=self.loop
            )
            self.camera_position, self.camera_rotation = self.camera_controller.update(0)
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            self.camera_controller = CameraController(self.camera_positions, lens_rotations=self.lens_rotations)
            # Take the first camera position
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            # Indices 3 and 4 are yaw/pitch
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]

        self.setup_camera_matrices()

    def setup_camera_matrices(self):
        """
        Compute view/projection from (x, y, z, yaw, pitch).
        """
        aspect_ratio = self.window_size[0] / self.window_size[1]

        # camera_rotation is (yaw, pitch)
        yaw = self.camera_rotation[0]
        pitch = self.camera_rotation[1]

        rotation_matrix = glm.mat4(1.0)

        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(yaw), glm.vec3(0.0, 1.0, 0.0))
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(pitch), glm.vec3(1.0, 0.0, 0.0))

        forward_direction = glm.vec3(rotation_matrix * glm.vec4(0.0, 0.0, -1.0, 0.0))
        up_vector = glm.vec3(0.0, 1.0, 0.0)

        self.view = glm.lookAt(self.camera_position, self.camera_position + forward_direction, up_vector)

        # Lens rotation around forward axis
        lens_rotation_matrix = glm.rotate(glm.mat4(1.0), glm.radians(self.main_camera_lens_rotation), forward_direction)
        self.view = lens_rotation_matrix * self.view

        self.projection = glm.perspective(glm.radians(self.fov), aspect_ratio, self.near_plane, self.far_plane)

    def set_light_uniforms(self, shader_program):
        self.shader_engine.use_shader_program()
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

    def rotate_euler(self, angles_deg):
        """
        angles_deg is a tuple (xDeg, yDeg, zDeg).
        Sets self.rotation to these Euler angles (in degrees).
        """
        xDeg, yDeg, zDeg = angles_deg
        # Convert each to radians
        self.rotation.x = glm.radians(xDeg)
        self.rotation.y = glm.radians(yDeg)
        self.rotation.z = glm.radians(zDeg)
        self.update_model_matrix()

    def rotate(self, angle, axis):
        """
        Existing single-axis rotation method:
        Rotate the object by 'angle' degrees around axis (x,y,z).
        """
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

    def enable_auto_rotation(self, enabled=False, axis=None, speed=None):
        """
        Enable/disable auto rotation. If 'axis' or 'speed' is provided,
        update self.rotation_axis and self.rotation_speed.
        """
        self.auto_rotation_enabled = enabled
        if axis is not None:
            self.rotation_axis = glm.vec3(*axis)
        if speed is not None:
            self.rotation_speed = speed

    def set_constant_uniforms(self):
        self.shader_engine.use_shader_program()
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "textureLodLevel"), self.texture_lod_bias)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "envMapLodLevel"), self.env_map_lod_bias)

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "applyToneMapping"), self.apply_tone_mapping
        )

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "applyGammaCorrection"), self.apply_gamma_correction
        )

    def set_shader_uniforms(self):
        self.shader_engine.use_shader_program()
        # Set model matrix uniform
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "model"),
            1,
            GL_FALSE,
            glm.value_ptr(self.model_matrix),
        )

        # Set light space matrix uniform
        if self.shadow_map_manager and self.shadowing_enabled and self.lights_enabled:
            glUniformMatrix4fv(
                glGetUniformLocation(self.shader_engine.shader_program, "lightSpaceMatrix"),
                1,
                GL_FALSE,
                glm.value_ptr(self.shadow_map_manager.light_space_matrix),
            )

        # Set the parallax mapping uniforms
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "invertDisplacementMap"),
            int(self.invert_displacement_map),
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "pomHeightScale"), self.pom_height_scale)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "pomMinSteps"), self.pom_min_steps)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "pomMaxSteps"), self.pom_max_steps)

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "ambientStrength"), self.ambient_lighting_strength
        )

        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "ambientColor"),
            1,
            glm.value_ptr(self.ambient_lighting_color),
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
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "opacity"), self.opacity)

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "shininess"), self.shininess)

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "environmentMapStrength"), self.env_map_strength
        )

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "distortionStrength"), self.distortion_strength
        )

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "reflectionStrength"), self.reflection_strength
        )

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "warped"), self.distortion_warped)

        glUniform2f(
            glGetUniformLocation(self.shader_engine.shader_program, "screenResolution"),
            self.window_size[0],
            self.window_size[1],
        )

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "flipPlanarHorizontal"),
            int(self.flip_planar_horizontally)
        )

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "flipPlanarVertical"),
            int(self.flip_planar_vertically)
        )

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "usePlanarNormalDistortion"),
            int(self.use_planar_normal_distortion)
        )

        if self.screen_texture:
            screen_texture_unit = texture_manager.get_texture_unit(str(self.identifier), "planar_camera")
            glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "screenTexture"), screen_texture_unit)

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "screenFacingPlanarTexture"),
            int(self.screen_facing_planar_texture),
        )

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "useCheckerPattern"),
            int(self.dynamic_attrs.get("use_checker_pattern", 1)),
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
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "shadowingEnabled"), int(self.shadowing_enabled)
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "surfaceDepth"),
            self.dynamic_attrs.get("surface_depth", 0.0),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "shadowStrength"),
            self.dynamic_attrs.get("shadow_strength", 1.0),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "cameraPos"), 1, glm.value_ptr(self.camera_position)
        )

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "time"), pygame.time.get_ticks() / 1000.0)

    def create_dummy_texture(self):
        dummy_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, dummy_texture)
        data = np.array([1.0], dtype=np.float32)  # White color
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, 1, 1, 0, GL_DEPTH_COMPONENT, GL_FLOAT, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return dummy_texture

    def set_shadow_shader_uniforms(self):
        self.shader_engine.use_shader_program()
        shadow_map_unit = texture_manager.get_texture_unit(str(self.identifier), "shadow_map")
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "shadowMap"), shadow_map_unit)

        glActiveTexture(GL_TEXTURE0 + shadow_map_unit)

        if self.shadow_map_manager and self.shadowing_enabled and self.lights_enabled:
            # Set light space matrix
            glUniformMatrix4fv(
                glGetUniformLocation(self.shader_engine.shader_program, "lightSpaceMatrix"),
                1,
                GL_FALSE,
                glm.value_ptr(self.shadow_map_manager.light_space_matrix),
            )

            # Set light position
            glUniform3fv(
                glGetUniformLocation(self.shader_engine.shader_program, "lightPosition"),
                1,
                glm.value_ptr(self.lights[0]["position"]),
            )

            # Bind shadow map
            glBindTexture(GL_TEXTURE_2D, self.shadow_map_manager.depth_map)
        else:
            # Bind dummy texture
            dummy_texture = texture_manager.get_dummy_texture()
            glBindTexture(GL_TEXTURE_2D, dummy_texture)

    def update_camera(self, delta_time):
        if self.auto_camera:
            self.camera_position, self.camera_rotation = self.camera_controller.update(delta_time)
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]
        self.setup_camera_matrices()

    def shutdown(self):
        """Clean up OpenGL resources used by the renderer."""
        # Check if vaos attribute exists and is non-empty
        if hasattr(self, "vaos") and len(self.vaos) > 0:
            glDeleteVertexArrays(len(self.vaos), self.vaos)

        # Check if vbos attribute exists and is non-empty
        if hasattr(self, "vbos") and len(self.vbos) > 0:
            glDeleteBuffers(len(self.vbos), self.vbos)

        self.shader_engine.delete_shader_programs()

    @abstractmethod
    def create_buffers(self):
        pass

    @abstractmethod
    def render(self):
        pass
