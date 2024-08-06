import glm
import numpy as np
import pywavefront
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ModelRenderer(AbstractRenderer):
    def __init__(self, obj_path, texture_paths, shader_name, **kwargs):
        super().__init__(shader_name=shader_name, **kwargs)
        self.obj_path = obj_path
        self.texture_paths = texture_paths
        self.object = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

    def create_buffers(self):
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
        self.diffuseMap = glGenTextures(1)
        self.load_texture(self.texture_paths['diffuse'], self.diffuseMap)

        self.normalMap = glGenTextures(1)
        self.load_texture(self.texture_paths['normal'], self.normalMap)

        self.displacementMap = glGenTextures(1)
        self.load_texture(self.texture_paths['displacement'], self.displacementMap)

        self.environmentMap = glGenTextures(1)
        if self.cubemap_folder:
            self.load_cubemap(self.cubemap_folder, self.environmentMap)

        glUseProgram(self.shader_program)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'diffuseMap'), 0)

        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.normalMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'normalMap'), 1)

        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.displacementMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'displacementMap'), 2)

        glActiveTexture(GL_TEXTURE3)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'environmentMap'), 3)

    @common_funcs
    def render(self):
        viewPosition = self.camera_position
        glUniform3fv(glGetUniformLocation(self.shader_program, 'viewPosition'), 1, glm.value_ptr(viewPosition))
        glUniform1f(glGetUniformLocation(self.shader_program, 'textureLodLevel'), self.texture_lod_bias)
        glUniform1f(glGetUniformLocation(self.shader_program, 'envMapLodLevel'), self.env_map_lod_bias)
        glUniform1i(glGetUniformLocation(self.shader_program, 'applyToneMapping'), self.apply_tone_mapping)
        glUniform1i(glGetUniformLocation(self.shader_program, 'applyGammaCorrection'), self.apply_gamma_correction)

        for mesh in self.object.mesh_list:
            material = self.object.materials['Material']
            glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
            glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
            glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

            glBindVertexArray(self.vaos[self.object.mesh_list.index(mesh)])
            glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
            glBindVertexArray(0)
