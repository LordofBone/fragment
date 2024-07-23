import glm
import numpy as np
import pygame
import pywavefront
from OpenGL.GL import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT

from components.shader_engine import ShaderEngine


class ModelRenderer:
    def __init__(self, obj_path, vertex_shader_path, fragment_shader_path, texture_paths, cubemap_folder,
                 window_size=(800, 600), lod_level=1.0, camera_position=(4, 2, 4), camera_target=(0, 0, 0),
                 up_vector=(0, 1, 0), fov=45, near_plane=0.1, far_plane=100,
                 light_positions=[(3.0, 3.0, 3.0)], light_colors=[(1.0, 1.0, 1.0)], light_strengths=[0.8],
                 anisotropy=16.0, rotation_speed=2000.0, rotation_axis=(0, 3, 0),
                 apply_tone_mapping=True, apply_gamma_correction=True):
        self.obj_path = obj_path
        self.vertex_shader_path = vertex_shader_path
        self.fragment_shader_path = fragment_shader_path
        self.texture_paths = texture_paths
        self.cubemap_folder = cubemap_folder
        self.window_size = window_size
        self.lod_level = lod_level
        self.camera_position = glm.vec3(*camera_position)
        self.camera_target = glm.vec3(*camera_target)
        self.up_vector = glm.vec3(*up_vector)
        self.fov = fov
        self.near_plane = near_plane
        self.far_plane = far_plane
        self.light_positions = [glm.vec3(*pos) for pos in light_positions]
        self.light_colors = [glm.vec3(*col) for col in light_colors]
        self.light_strengths = light_strengths
        self.anisotropy = anisotropy
        self.rotation_speed = rotation_speed
        self.rotation_axis = glm.vec3(*rotation_axis)
        self.apply_tone_mapping = apply_tone_mapping
        self.apply_gamma_correction = apply_gamma_correction
        self.scene = None
        self.shader_program = None
        self.vbos = []
        self.vaos = []
        self.model = glm.mat4(1)
        self.view = None
        self.projection = None
        self.diffuseMap = None
        self.normalMap = None
        self.heightMap = None
        self.environmentMap = None

        self.scene = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

        # Initialize shaders now that the OpenGL context is created
        self.init_shaders()

        # Setup camera after shaders are initialized
        self.setup_camera()

        # Load textures and create buffers
        self.load_textures()
        self.create_buffers()

    def init_shaders(self):
        shader_engine = ShaderEngine(self.vertex_shader_path, self.fragment_shader_path)
        shader_engine.init_shaders()
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

    def draw_model(self):
        self.model = glm.rotate(glm.mat4(1), pygame.time.get_ticks() / self.rotation_speed, self.rotation_axis)
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'model'), 1, GL_FALSE, glm.value_ptr(self.model))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'view'), 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'projection'), 1, GL_FALSE,
                           glm.value_ptr(self.projection))

        # Set the light and view positions
        viewPosition = self.camera_position
        for i in range(len(self.light_positions)):
            glUniform3fv(glGetUniformLocation(self.shader_program, f'lightPositions[{i}]'), 1,
                         glm.value_ptr(self.light_positions[i]))
            glUniform3fv(glGetUniformLocation(self.shader_program, f'lightColors[{i}]'), 1,
                         glm.value_ptr(self.light_colors[i]))
            glUniform1f(glGetUniformLocation(self.shader_program, f'lightStrengths[{i}]'), self.light_strengths[i])
        glUniform3fv(glGetUniformLocation(self.shader_program, 'viewPosition'), 1, glm.value_ptr(viewPosition))
        glUniform1f(glGetUniformLocation(self.shader_program, 'lodLevel'), self.lod_level)
        glUniform1i(glGetUniformLocation(self.shader_program, 'applyToneMapping'), self.apply_tone_mapping)
        glUniform1i(glGetUniformLocation(self.shader_program, 'applyGammaCorrection'), self.apply_gamma_correction)

        for mesh in self.scene.mesh_list:
            material = self.scene.materials['Material']
            glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
            glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
            glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

            for vao in self.vaos:
                glBindVertexArray(vao)
                glDrawArrays(GL_TRIANGLES, 0, len(self.vertices) // 8)
            glBindVertexArray(0)

    def create_buffers(self):
        for name, material in self.scene.materials.items():
            self.vertices = material.vertices
            vertices_array = np.array(self.vertices, dtype=np.float32)

            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
            self.vbos.append(vbo)

            vao = glGenVertexArrays(1)
            glBindVertexArray(vao)

            float_size = 4
            vertex_stride = 8 * float_size

            position_loc = glGetAttribLocation(self.shader_program, "position")
            tex_coords_loc = glGetAttribLocation(self.shader_program, "textureCoords")
            normal_loc = glGetAttribLocation(self.shader_program, "normal")

            glEnableVertexAttribArray(position_loc)
            glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(5 * float_size))

            glEnableVertexAttribArray(tex_coords_loc)
            glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

            glEnableVertexAttribArray(normal_loc)
            glVertexAttribPointer(normal_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(2 * float_size))

            self.vaos.append(vao)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindVertexArray(0)

    def setup_camera(self):
        self.view = glm.lookAt(self.camera_position, self.camera_target, self.up_vector)
        self.projection = glm.perspective(glm.radians(self.fov), self.window_size[0] / self.window_size[1],
                                          self.near_plane, self.far_plane)

    def load_textures(self):
        self.diffuseMap = glGenTextures(1)
        self.load_texture(self.texture_paths['diffuse'], self.diffuseMap)

        self.normalMap = glGenTextures(1)
        self.load_texture(self.texture_paths['normal'], self.normalMap)

        self.heightMap = glGenTextures(1)
        self.load_texture(self.texture_paths['height'], self.heightMap)

        self.environmentMap = glGenTextures(1)
        self.load_cubemap(self.cubemap_folder, self.environmentMap)

        glUseProgram(self.shader_program)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'diffuseMap'), 0)

        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.normalMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'normalMap'), 1)

        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.heightMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'heightMap'), 2)

        glActiveTexture(GL_TEXTURE3)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'environmentMap'), 3)

    def render(self):
        glUseProgram(self.shader_program)
        glEnable(GL_DEPTH_TEST)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_model()
