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
        self.vaos = []
        self.vbos = []
        self.mesh_material_index_map = []

        for mesh_index, mesh in enumerate(self.object.mesh_list):
            for material in mesh.materials:
                vertices = material.vertices
                if not vertices:
                    print(f"Material '{material.name}' in mesh '{mesh.name}' has no vertices. Skipping.")
                    continue

                vertex_format = material.vertex_format  # 'T2F_N3F_V3F'
                # vertex_format is known: 2 floats (tex), 3 floats (normal), 3 floats (pos) = 8 floats total

                # Convert vertices to numpy array
                vertices_array = np.array(vertices, dtype=np.float32)
                # Reshape to [N,8] because we know it's T2F_N3F_V3F
                vertices_array = vertices_array.reshape(-1, 8)

                # Current order: (u,v, nx,ny,nz, x,y,z)
                # Desired order: (x,y,z, nx,ny,nz, u,v)
                # Reorder columns:
                # positions are currently at indices [5,6,7]
                # normals are at indices [2,3,4]
                # texcoords are at indices [0,1]

                reordered = np.column_stack((
                    vertices_array[:, 5],  # x
                    vertices_array[:, 6],  # y
                    vertices_array[:, 7],  # z
                    vertices_array[:, 2],  # nx
                    vertices_array[:, 3],  # ny
                    vertices_array[:, 4],  # nz
                    vertices_array[:, 0],  # u
                    vertices_array[:, 1]  # v
                ))

                # Now reordered data matches (position, normal, texcoords) order
                # No tangents/bitangents yet, so just 8 floats per vertex
                vbo = self.create_vbo(reordered)
                vao = self.create_vao()  # This VAO will be configured for 8-float vertices

                self.vbos.append(vbo)
                self.vaos.append(vao)
                self.mesh_material_index_map.append((mesh_index, material.name))

    def create_vbo(self, vertices_array):
        """Create a Vertex Buffer Object (VBO)."""
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self):
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        float_size = 4
        # Now the stride is 8 floats total (no tangents/bitangents yet)
        vertex_stride = 8 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")

        # We will assume tangent=location 3, bitangent=location 4
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        # position: offset 0

        # position: offset 0 (3 floats)
        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 0)
        # normal: offset 3 floats
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 3 * float_size)
        # texCoords: offset 6 floats
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 6 * float_size)
        # tangent: offset 8 floats
        if tangent_loc >= 0:
            self.enable_vertex_attrib(tangent_loc, 3, vertex_stride, 8 * float_size)
        # bitangent: offset 11 floats
        if bitangent_loc >= 0:
            self.enable_vertex_attrib(bitangent_loc, 3, vertex_stride, 11 * float_size)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        return vao

    def get_vertex_stride(self, vertex_format):
        # Example: T2F_N3F_V3F means 2 floats for texCoords, 3 for normal, 3 for vertex
        # Adjust according to your formats.
        count = 0
        format_parts = vertex_format.split('_')
        for part in format_parts:
            # part like 'T2F' or 'N3F' or 'V3F'
            letter = part[0]  # T=tex, N=normal, V=vertex
            num = int(part[1])  # number of floats
            # F just stands for float
            count += num
        return count

    def enable_vertex_attrib(self, location, size, stride, pointer_offset):
        if location >= 0:
            glEnableVertexAttribArray(location)
            glVertexAttribPointer(location, size, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(pointer_offset))

    @common_funcs
    def render(self):
        """Render the model."""
        vao_counter = 0
        for mesh_index, mesh in enumerate(self.object.mesh_list):
            for material in mesh.materials:
                vertices = material.vertices
                if not vertices:
                    continue
                self.apply_material(material)
                count = len(vertices) // self.get_vertex_stride(material.vertex_format)
                self.bind_and_draw_vao(vao_counter, count)
                vao_counter += 1

    def apply_material(self, material):
        glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
        glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

    def bind_and_draw_vao(self, vao_index, count):
        glBindVertexArray(self.vaos[vao_index])
        glDrawArrays(GL_TRIANGLES, 0, count)
        glBindVertexArray(0)

    def shutdown(self):
        """Clean up OpenGL resources used by the renderer."""
        if hasattr(self, "vaos") and len(self.vaos) > 0:
            glDeleteVertexArrays(len(self.vaos), self.vaos)

        if hasattr(self, "vbos") and len(self.vbos) > 0:
            glDeleteBuffers(len(self.vbos), self.vbos)

        if hasattr(self, "ebos") and len(self.ebos) > 0:
            glDeleteBuffers(len(self.ebos), self.ebos)

        self.shader_engine.delete_shader_programs()
