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
        # create_materials=True and collect_faces=True ensure we have materials and faces data
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

                # vertex_format: 'T2F_N3F_V3F' => uv(2), normal(3), position(3) = 8 floats total
                vertices_array = np.array(vertices, dtype=np.float32).reshape(-1, 8)

                # Current order: (u,v, nx,ny,nz, x,y,z)
                # Desired order: (x,y,z, nx,ny,nz, u,v)
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

                # Now we have (x,y,z, nx,ny,nz, u,v) per vertex
                # Compute tangent and bitangent
                # We'll assume the vertices are arranged as triangles (every 3 vertices is a triangle)
                reordered = self.compute_tangents_and_bitangents(reordered)

                # Now reordered has (x,y,z, nx,ny,nz, u,v, tx,ty,tz, bx,by,bz) = 14 floats/vertex
                vbo = self.create_vbo(reordered)
                vao = self.create_vao(with_tangents=True)

                self.vbos.append(vbo)
                self.vaos.append(vao)
                self.mesh_material_index_map.append((mesh_index, material.name))

    def compute_tangents_and_bitangents(self, verts):
        # verts: N x 8 array: (x,y,z, nx,ny,nz, u,v)
        # We want to add tangent and bitangent: final will be N x 14
        # Initialize tangent and bitangent arrays
        tangent = np.zeros((verts.shape[0], 3), dtype=np.float32)
        bitangent = np.zeros((verts.shape[0], 3), dtype=np.float32)

        # Assume every 3 vertices form a triangle
        num_triangles = verts.shape[0] // 3
        for i in range(num_triangles):
            i0 = i * 3
            i1 = i * 3 + 1
            i2 = i * 3 + 2

            v0 = verts[i0]
            v1 = verts[i1]
            v2 = verts[i2]

            pos0 = v0[0:3]
            pos1 = v1[0:3]
            pos2 = v2[0:3]

            uv0 = v0[6:8]
            uv1 = v1[6:8]
            uv2 = v2[6:8]

            deltaPos1 = pos1 - pos0
            deltaPos2 = pos2 - pos0
            deltaUV1 = uv1 - uv0
            deltaUV2 = uv2 - uv0

            r = 1.0 / (deltaUV1[0] * deltaUV2[1] - deltaUV1[1] * deltaUV2[0] + 1e-8)
            T = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1]) * r
            B = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0]) * r

            tangent[i0] += T
            tangent[i1] += T
            tangent[i2] += T

            bitangent[i0] += B
            bitangent[i1] += B
            bitangent[i2] += B

        # Normalize tangent/bitangent
        # Also ensure tangent is orthogonal to normal if necessary.
        for i in range(verts.shape[0]):
            n = verts[i, 3:6]  # normal
            t = tangent[i]
            b = bitangent[i]

            # Gram-Schmidt orthogonalization
            # t = t - n*(n·t)
            t = t - n * np.dot(n, t)
            # Normalize t
            if np.linalg.norm(t) > 1e-8:
                t = t / np.linalg.norm(t)

            # b = b - n*(n·b) - t*(t·b)
            b = b - n * np.dot(n, b) - t * np.dot(t, b)
            # Normalize b
            if np.linalg.norm(b) > 1e-8:
                b = b / np.linalg.norm(b)

            tangent[i] = t
            bitangent[i] = b

        # Combine data into a single array: now (x,y,z, nx,ny,nz, u,v, tx,ty,tz, bx,by,bz)
        final_array = np.hstack((verts, tangent, bitangent)).astype(np.float32)
        return final_array

    def create_vbo(self, vertices_array):
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self, with_tangents=False):
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        float_size = 4
        if with_tangents:
            # (x,y,z, nx,ny,nz, u,v, tx,ty,tz, bx,by,bz) = 14 floats
            vertex_stride = 14 * float_size
        else:
            # Without tangents, we had 8 floats
            vertex_stride = 8 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        # Position: (x,y,z) at offset 0
        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 0)
        # Normal: (nx,ny,nz) at offset 3 floats
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 3 * float_size)
        # UV: (u,v) at offset 6 floats
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 6 * float_size)
        if with_tangents:
            # Tangent: at offset 8 floats
            if tangent_loc >= 0:
                self.enable_vertex_attrib(tangent_loc, 3, vertex_stride, 8 * float_size)
            # Bitangent: at offset 11 floats
            if bitangent_loc >= 0:
                self.enable_vertex_attrib(bitangent_loc, 3, vertex_stride, 11 * float_size)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        return vao

    def get_vertex_stride(self, vertex_format):
        count = 0
        format_parts = vertex_format.split('_')
        for part in format_parts:
            num = int(part[1])  # number of floats
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
        if hasattr(self, "vaos") and len(self.vaos) > 0:
            glDeleteVertexArrays(len(self.vaos), self.vaos)

        if hasattr(self, "vbos") and len(self.vbos) > 0:
            glDeleteBuffers(len(self.vbos), self.vbos)

        if hasattr(self, "ebos") and len(self.ebos) > 0:
            glDeleteBuffers(len(self.ebos), self.ebos)

        self.shader_engine.delete_shader_programs()
