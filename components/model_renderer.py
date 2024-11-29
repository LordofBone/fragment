import numpy as np
import pywavefront
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs
from components.texture_manager import TextureManager

texture_manager = TextureManager()


class ModelRenderer(AbstractRenderer):
    def __init__(self, renderer_name, obj_path, **kwargs):
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.obj_path = obj_path
        self.object = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

    def supports_shadow_mapping(self):
        return True

    def create_buffers(self):
        """Create buffers for the model."""
        for name, material in self.object.materials.items():
            self.vertices = material.vertices
            vertices_array = np.array(self.vertices, dtype=np.float32)

            vbo = self.create_vbo(vertices_array)
            vao = self.create_vao()

            self.vbos.append(vbo)
            self.vaos.append(vao)

    def create_vbo(self, vertices_array):
        """Create a Vertex Buffer Object (VBO)."""
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self):
        """Create a Vertex Array Object (VAO) and configure vertex attributes."""
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        float_size = 4
        vertex_stride = 8 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")

        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 5 * float_size)
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 0)
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 2 * float_size)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        return vao

    def enable_vertex_attrib(self, location, size, stride, pointer_offset):
        """Enable a vertex attribute and define its data layout."""
        if location >= 0:
            glEnableVertexAttribArray(location)
            glVertexAttribPointer(location, size, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(pointer_offset))

    @common_funcs
    def render(self):
        """Render the model."""
        for mesh in self.object.mesh_list:
            self.apply_material(self.object.materials["Material"])
            vao_index = self.object.mesh_list.index(mesh)
            self.bind_and_draw_vao(vao_index, len(mesh.faces) * 3)

    def apply_material(self, material):
        """Apply material properties to the shader."""
        glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
        glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

    def bind_and_draw_vao(self, vao_index, count):
        """Bind a VAO and issue a draw call."""
        glBindVertexArray(self.vaos[vao_index])
        glDrawArrays(GL_TRIANGLES, 0, count)
        glBindVertexArray(0)
