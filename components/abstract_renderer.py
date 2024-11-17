import os
import time
from abc import ABC, abstractmethod

import glm
import pygame
from OpenGL.GL import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT
from PIL import Image

from components.camera_control import CameraController
from components.shader_engine import ShaderEngine
from components.texture_manager import TextureManager

# Get the singleton instance of TextureManager
texture_manager = TextureManager()


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
        glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "viewPosition"), 1,
                     glm.value_ptr(view_position))
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

        self.set_shader_uniforms()
        check_gl_error("set_shader_uniforms", self.debug_mode)

        # self.set_shadow_shader_uniforms()
        # check_gl_error("set_shadow_shader_uniforms", self.debug_mode)

        if self.lights_enabled:
            self.set_light_uniforms(self.shader_engine.shader_program)
        check_gl_error("set_light_uniforms", self.debug_mode)

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
        shader_names,
        shaders=None,
        texture_paths=None,
        cubemap_folder=None,
        camera_positions=None,
        camera_target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov=45,
        near_plane=0.1,
        far_plane=100,
        ambient_lighting_strength=(0.0, 0.0, 0.0),
        lights=None,
        rotation_speed=2000.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        texture_lod_bias=0.0,
        env_map_lod_bias=0.0,
        alpha_blending=False,
        depth_testing=True,
        culling=True,
        msaa_level=8,
        anisotropy=16,
        auto_camera=False,
        move_speed=1.0,
        loop=True,
        front_face_winding="CCW",
        window_size=(800, 600),
        phong_shading=False,
        opacity=1.0,
        shininess=1.0,
        distortion_strength=0.3,
        reflection_strength=0.0,
        distortion_warped=False,
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
        # Use the memory address of the instance as a unique identifier
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

        self.opacity = opacity
        self.shininess = shininess
        self.distortion_strength = distortion_strength
        self.reflection_strength = reflection_strength
        self.distortion_warped = distortion_warped

        self.screen_texture = screen_texture
        self.planar_resolution = planar_resolution
        self.planar_fov = planar_fov
        self.planar_near_plane = planar_near_plane
        self.planar_far_plane = planar_far_plane

        # Planar camera attributes combined
        self.planar_camera_position_rotation = planar_camera_position_rotation
        self.planar_relative_to_camera = planar_relative_to_camera
        self.planar_camera_lens_rotation = planar_camera_lens_rotation

        # New parameter for lens rotations
        self.lens_rotations = lens_rotations or [planar_camera_lens_rotation]

        # New attribute
        self.screen_facing_planar_texture = screen_facing_planar_texture
        self.screen_facing_planar_screenshotted = False

        self.vbos = []
        self.vaos = []

        self.shader_engine = None

        self.shadowing_enabled = True

        # Shadow map resolution
        self.shadow_width = 128
        self.shadow_height = 128

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
        self.setup_shadow_map()
        self.set_constant_uniforms()

    def setup_shadow_map(self):
        if self.shadowing_enabled:
            # Generate framebuffer
            self.depth_map_fbo = glGenFramebuffers(1)

            # Create depth texture
            self.depth_map = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.depth_map)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
                         self.shadow_width, self.shadow_height, 0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
            border_color = [1.0, 1.0, 1.0, 1.0]
            glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, border_color)

            # Attach depth texture as FBO's depth buffer
            glBindFramebuffer(GL_FRAMEBUFFER, self.depth_map_fbo)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.depth_map, 0)
            glDrawBuffer(GL_NONE)
            glReadBuffer(GL_NONE)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def calculate_light_space_matrix(self):
        # Define the orthographic projection matrix for the light's perspective
        near_plane = 1.0
        far_plane = 50.0
        light_projection = glm.ortho(-10.0, 10.0, -10.0, 10.0, near_plane, far_plane)
        light_view = glm.lookAt(self.lights[0]["position"], glm.vec3(0.0, 0.0, 0.0), glm.vec3(0.0, 1.0, 0.0))
        self.light_space_matrix = light_projection * light_view

    def render_shadow_map(self, scene_renderers):
        if self.shadowing_enabled and self.lights_enabled:
            # First render pass: Render scene from light's perspective
            self.calculate_light_space_matrix()

            # Use the shadow map shaders
            self.shader_engine.use_shader_program()
            glViewport(0, 0, self.shadow_width, self.shadow_height)
            glBindFramebuffer(GL_FRAMEBUFFER, self.depth_map_fbo)
            glClear(GL_DEPTH_BUFFER_BIT)

            for renderer in scene_renderers:
                renderer.render_from_light(self.light_space_matrix)

            glBindFramebuffer(GL_FRAMEBUFFER, 0)

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

    def render_planar_view(self, scene_renderers):
        if not self.planar_camera:
            return None

        # Calculate the main camera's forward direction
        main_camera_forward = glm.normalize(self.camera_target - self.camera_position)

        if self.planar_relative_to_camera:
            # Ensure the planar camera's lens rotation matches relative to the main camera's lens rotation
            lens_rotation = self.planar_camera_lens_rotation + self.main_camera_lens_rotation

            # Calculate the direction to camera
            direction_to_camera = glm.normalize(self.camera_position - self.translation)

            # Planar camera position is relative to the object's position and adjusted direction based on camera distance
            self.planar_camera_position = (
                self.translation + glm.vec3(*self.planar_camera_position_rotation[:3])
            ) + direction_to_camera * self.dynamic_attrs.get("camera_distance", 2.0)

            # Calculate the relative rotation based on the main camera's orientation
            self.planar_camera_rotation = glm.vec2(self.planar_camera_position_rotation[3:]) + glm.vec2(
                self.camera_rotation
            )

            rotation_matrix = glm.rotate(
                glm.mat4(1.0), glm.radians(self.planar_camera_rotation.x), glm.vec3(1.0, 0.0, 0.0)
            )
            rotation_matrix = glm.rotate(
                rotation_matrix, glm.radians(self.planar_camera_rotation.y), glm.vec3(0.0, 1.0, 0.0)
            )
            adjusted_direction = glm.vec3(rotation_matrix * glm.vec4(main_camera_forward, 0.0))

            planar_target = self.planar_camera_position + adjusted_direction

            # Flip the up vector to correct any inversion that might occur
            up_vector = glm.vec3(0.0, -1.0, 0.0)

            # Create the view matrix for the planar camera
            self.planar_view = glm.lookAt(self.planar_camera_position, planar_target, up_vector)
        else:
            # Ensure the planar camera's lens rotation is set static to the specified value
            lens_rotation = self.planar_camera_lens_rotation

            # Fixed planar camera position relative to the object
            self.planar_camera_position = self.translation + glm.vec3(*self.planar_camera_position_rotation[:3])
            self.planar_camera_rotation = glm.vec2(self.planar_camera_position_rotation[3:])
            direction_to_target = glm.vec3(0.0, 0.0, -1.0)

            rotation_matrix = glm.rotate(
                glm.mat4(1.0), glm.radians(self.planar_camera_rotation.x), glm.vec3(1.0, 0.0, 0.0)
            )
            rotation_matrix = glm.rotate(
                rotation_matrix, glm.radians(self.planar_camera_rotation.y), glm.vec3(0.0, 1.0, 0.0)
            )
            adjusted_direction = glm.vec3(rotation_matrix * glm.vec4(direction_to_target, 0.0))

            planar_target = self.planar_camera_position + adjusted_direction

            # Flip the up vector to correct the inversion
            up_vector = glm.vec3(0.0, -1.0, 0.0)

            # Create the view matrix for the planar camera
            self.planar_view = glm.lookAt(self.planar_camera_position, planar_target, up_vector)

        # Apply lens rotation by rotating around the forward axis
        lens_rotation_matrix = glm.rotate(
            glm.mat4(1.0), glm.radians(lens_rotation), glm.vec3(0.0, 0.0, 1.0)
        )  # Rotation around the forward axis
        self.planar_view = lens_rotation_matrix * self.planar_view

        # Calculate the aspect ratio and create the projection matrix
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

        if self.debug_mode:
            if not self.screen_facing_planar_screenshotted:
                # Read the texture data from the framebuffer
                glBindTexture(GL_TEXTURE_2D, self.screen_texture)
                data = glReadPixels(
                    0, 0, self.planar_resolution[0], self.planar_resolution[1], GL_RGB, GL_UNSIGNED_BYTE
                )
                image = Image.frombytes("RGB", self.planar_resolution, data)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)  # Flip the image vertically

                # Create the screenshots directory if it doesn't exist
                screenshots_dir = "screenshots"
                if not os.path.exists(screenshots_dir):
                    os.makedirs(screenshots_dir)

                # Generate the filename with a timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screen_texture_output_{timestamp}.png"

                # Save the image in the screenshots directory
                image.save(os.path.join(screenshots_dir, filename))
                self.screen_facing_planar_screenshotted = True

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # Reset the viewport back to the window size
        glViewport(0, 0, self.window_size[0], self.window_size[1])

        glBindTexture(GL_TEXTURE_2D, 0)

    def render_with_custom_camera(self, view_matrix, projection_matrix):
        self.view = view_matrix
        self.projection = projection_matrix
        self.render()

    def render_from_light(self, light_space_matrix):
        self.shader_engine.use_shadow_shader_program()
        glUniformMatrix4fv(glGetUniformLocation(self.shader_engine.shadow_shader_program, "model"),
                           1, GL_FALSE, glm.value_ptr(self.model_matrix))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_engine.shadow_shader_program, "lightSpaceMatrix"),
                           1, GL_FALSE, glm.value_ptr(light_space_matrix))

        for mesh in self.object.mesh_list:
            vao_index = self.object.mesh_list.index(mesh)
            glBindVertexArray(self.vaos[vao_index])
            glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
            glBindVertexArray(0)

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
        if "shadow_vertex" in self.shader_names:
            shadow_vertex_shader_path = self.shaders["vertex"].get(self.shader_names["shadow_vertex"])
        if "shadow_fragment" in self.shader_names:
            shadow_fragment_shader_path = self.shaders["fragment"].get(self.shader_names["shadow_fragment"])

        self.shader_engine = ShaderEngine(vertex_shader_path, fragment_shader_path, compute_shader_path,
                                          shadow_vertex_shader_path, shadow_fragment_shader_path)

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
        faces = ["right.png", "left.png", "bottom.png", "top.png", "front.png", "back.png"]
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
            self.camera_position, self.camera_rotation = self.camera_controller.update(0)
            self.camera_target = self.camera_controller.get_current_target()
            self.main_camera_lens_rotation = self.camera_controller.get_current_lens_rotation()
        else:
            self.camera_position = glm.vec3(*self.camera_positions[0][:3])
            self.camera_rotation = glm.vec2(*self.camera_positions[0][3:])
            self.main_camera_lens_rotation = self.camera_controller.lens_rotations[0]
        self.setup_camera_matrices()

    def setup_camera_matrices(self):
        aspect_ratio = self.window_size[0] / self.window_size[1]

        # Apply rotations to the camera direction
        direction_to_target = glm.vec3(0, 0, -1.0)  # Assuming default forward direction is along -Z axis
        rotation_matrix = glm.rotate(glm.mat4(1.0), glm.radians(self.camera_rotation.x), glm.vec3(1.0, 0.0, 0.0))
        rotation_matrix = glm.rotate(rotation_matrix, glm.radians(self.camera_rotation.y), glm.vec3(0.0, 1.0, 0.0))
        adjusted_direction = glm.vec3(rotation_matrix * glm.vec4(direction_to_target, 0.0))

        # Create the view matrix
        self.view = glm.lookAt(self.camera_position, self.camera_position + adjusted_direction, self.up_vector)

        # Apply lens rotation by rotating around the forward axis
        lens_rotation_matrix = glm.rotate(
            glm.mat4(1.0), glm.radians(self.main_camera_lens_rotation), adjusted_direction
        )
        self.view = lens_rotation_matrix * self.view

        # Create the projection matrix
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
        self.shader_engine.use_shader_program()
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "textureLodLevel"), self.texture_lod_bias)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "envMapLodLevel"), self.env_map_lod_bias)

        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "applyToneMapping"),
                    self.apply_tone_mapping)

        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "applyGammaCorrection"),
                    self.apply_gamma_correction)

    def set_shader_uniforms(self):
        self.shader_engine.use_shader_program()

        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "ambientColor"), 1,
            glm.value_ptr(self.ambient_lighting_strength)
        )

        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "model"), 1, GL_FALSE,
            glm.value_ptr(self.model_matrix)
        )

        glUniformMatrix4fv(glGetUniformLocation(self.shader_engine.shader_program, "view"), 1, GL_FALSE,
                           glm.value_ptr(self.view))

        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "projection"), 1, GL_FALSE,
            glm.value_ptr(self.projection)
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "opacity"), self.opacity)

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "shininess"), self.shininess)

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "distortionStrength"),
                    self.distortion_strength)

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "reflectionStrength"),
                    self.reflection_strength)

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "warped"), self.distortion_warped)

        glUniform2f(
            glGetUniformLocation(self.shader_engine.shader_program, "screenResolution"), self.window_size[0],
            self.window_size[1]
        )

        if self.screen_texture:
            screen_texture_unit = texture_manager.get_texture_unit(str(self.identifier), "planar_camera")
            glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "screenTexture"), screen_texture_unit)

        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "screenFacingPlanarTexture"),
            int(self.screen_facing_planar_texture),
        )

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "waveSpeed"),
                    self.dynamic_attrs.get("wave_speed", 10.0))

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "waveAmplitude"),
            self.dynamic_attrs.get("wave_amplitude", 0.1)
        )

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "randomness"),
                    self.dynamic_attrs.get("randomness", 0.8))

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "texCoordFrequency"),
            self.dynamic_attrs.get("tex_coord_frequency", 100.0),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "texCoordAmplitude"),
            self.dynamic_attrs.get("tex_coord_amplitude", 0.1),
        )
        glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "cameraPos"), 1,
                     glm.value_ptr(self.camera_position))

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "time"), pygame.time.get_ticks() / 1000.0)

    def set_shadow_shader_uniforms(self):
        if self.shader_engine.shadow_shader_program and self.shadowing_enabled:
            # self.shader_engine.use_shadow_shader_program()
            self.shader_engine.use_shader_program()
            # Set light space matrix
            glUniformMatrix4fv(glGetUniformLocation(self.shader_engine.shader_program, "lightSpaceMatrix"),
                               1, GL_FALSE, glm.value_ptr(self.light_space_matrix))

            # Set light position (uses only the first light in the list to determine shadow)
            glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "lightPosition"),
                         1, glm.value_ptr(self.lights[0]["position"]))

            # Bind shadow map
            shadow_map_unit = texture_manager.get_texture_unit(str(self.identifier), "shadow_map")
            glActiveTexture(GL_TEXTURE0 + shadow_map_unit)
            glBindTexture(GL_TEXTURE_2D, self.depth_map)
            glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "shadowMap"), shadow_map_unit)

    def update_camera(self, delta_time):
        if self.auto_camera:
            self.camera_position, self.camera_rotation = self.camera_controller.update(delta_time)
            self.camera_target = self.camera_controller.get_current_target()
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
