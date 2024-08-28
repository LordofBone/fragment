import numpy as np
import pywavefront
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs
from components.texture_manager import TextureManager

texture_manager = TextureManager()


class ModelRenderer(AbstractRenderer):
    def __init__(self, obj_path, texture_paths, **kwargs):
        super().__init__(**kwargs)
        self.obj_path = obj_path
        self.texture_paths = texture_paths
        self.object = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

    def create_buffers(self):
        """Create buffers for the model."""
        for name, material in self.object.materials.items():
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

    def load_textures(self):
        glUseProgram(self.shader_program)

        """Load textures for the model."""
        self.diffuseMap = glGenTextures(1)
        self.load_texture(self.texture_paths["diffuse"], self.diffuseMap)

        self.normalMap = glGenTextures(1)
        self.load_texture(self.texture_paths["normal"], self.normalMap)

        self.displacementMap = glGenTextures(1)
        self.load_texture(self.texture_paths["displacement"], self.displacementMap)

        self.environmentMap = glGenTextures(1)
        env_map_unit = texture_manager.get_texture_unit(self.identifier, "environment")
        glActiveTexture(GL_TEXTURE0 + env_map_unit)

        if self.cubemap_folder:
            self.load_cubemap(self.cubemap_folder, self.environmentMap)

        diffuse_unit = texture_manager.get_texture_unit(self.identifier, "diffuse")
        glActiveTexture(GL_TEXTURE0 + diffuse_unit)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)

        glUniform1i(glGetUniformLocation(self.shader_program, "diffuseMap"), diffuse_unit)

        normal_unit = texture_manager.get_texture_unit(self.identifier, "normal")
        glActiveTexture(GL_TEXTURE0 + normal_unit)
        glBindTexture(GL_TEXTURE_2D, self.normalMap)

        glUniform1i(glGetUniformLocation(self.shader_program, "normalMap"), normal_unit)

        displacement_unit = texture_manager.get_texture_unit(self.identifier, "displacement")
        glActiveTexture(GL_TEXTURE0 + displacement_unit)
        glBindTexture(GL_TEXTURE_2D, self.displacementMap)

        glUniform1i(glGetUniformLocation(self.shader_program, "displacementMap"), displacement_unit)

        glActiveTexture(GL_TEXTURE0 + env_map_unit)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_program, "environmentMap"), env_map_unit)

    @common_funcs
    def render(self):
        """Render the model."""
        env_map_unit = texture_manager.get_texture_unit(self.identifier, "environment")
        glActiveTexture(GL_TEXTURE0 + env_map_unit)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)

        for mesh in self.object.mesh_list:
            material = self.object.materials["Material"]
            glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
            glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
            glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

            glBindVertexArray(self.vaos[self.object.mesh_list.index(mesh)])
            glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
            glBindVertexArray(0)
