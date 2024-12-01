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
        for mesh_name, mesh in self.object.meshes.items():
            # Each mesh may have multiple materials
            for material in mesh.materials:
                # Access the vertices associated with this material
                vertices = material.vertices
                vertex_format = material.vertex_format  # e.g., 'T2F_N3F_V3F'
                vertex_stride = self.get_vertex_stride(vertex_format)
                vertex_count = len(vertices) // vertex_stride

                # Build the indices list from mesh.faces
                # Each face in mesh.faces is a list of indices
                indices = []
                for face in mesh.faces:
                    indices.extend(face)

                # Now, calculate tangents and bitangents
                vertices_with_tangents = self.calculate_tangents(vertices, indices, vertex_stride)
                vertices_array = np.array(vertices_with_tangents, dtype=np.float32)

                vbo = self.create_vbo(vertices_array)
                vao = self.create_vao()

                self.vbos.append(vbo)
                self.vaos.append(vao)

    def get_vertex_stride(self, vertex_format):
        """Calculate the number of floats per vertex based on the vertex format."""
        format_mappings = {
            'T2F': 2,  # Texture coordinates
            'N3F': 3,  # Normals
            'V3F': 3  # Vertex positions
        }
        components = vertex_format.split('_')
        stride = 0
        for component in components:
            stride += format_mappings.get(component, 0)
        return stride

    def calculate_tangents(self, vertices, indices, vertex_stride):
        """Calculate tangent and bitangent vectors for the mesh."""
        vertex_count = len(vertices) // vertex_stride

        # Initialize per-vertex tangents and bitangents
        tangents = [np.zeros(3) for _ in range(vertex_count)]
        bitangents = [np.zeros(3) for _ in range(vertex_count)]

        # Offsets based on vertex format (T2F_N3F_V3F)
        texCoord_offset = 0  # Starts at 0
        normal_offset = texCoord_offset + 2
        position_offset = normal_offset + 3

        for i in range(0, len(indices), 3):
            # Get indices of the triangle
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]

            # Extract vertex positions and texture coordinates
            v0 = np.array(vertices[i0 * vertex_stride + position_offset: i0 * vertex_stride + position_offset + 3])
            v1 = np.array(vertices[i1 * vertex_stride + position_offset: i1 * vertex_stride + position_offset + 3])
            v2 = np.array(vertices[i2 * vertex_stride + position_offset: i2 * vertex_stride + position_offset + 3])

            uv0 = np.array(vertices[i0 * vertex_stride + texCoord_offset: i0 * vertex_stride + texCoord_offset + 2])
            uv1 = np.array(vertices[i1 * vertex_stride + texCoord_offset: i1 * vertex_stride + texCoord_offset + 2])
            uv2 = np.array(vertices[i2 * vertex_stride + texCoord_offset: i2 * vertex_stride + texCoord_offset + 2])

            # Compute delta positions and UVs
            deltaPos1 = v1 - v0
            deltaPos2 = v2 - v0
            deltaUV1 = uv1 - uv0
            deltaUV2 = uv2 - uv0

            # Calculate tangent and bitangent
            denominator = (deltaUV1[0] * deltaUV2[1] - deltaUV2[0] * deltaUV1[1])
            if denominator == 0.0:
                r = 0.0
            else:
                r = 1.0 / denominator
            tangent = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1]) * r
            bitangent = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0]) * r

            # Accumulate the tangents and bitangents
            tangents[i0] += tangent
            tangents[i1] += tangent
            tangents[i2] += tangent

            bitangents[i0] += bitangent
            bitangents[i1] += bitangent
            bitangents[i2] += bitangent

        # Normalize tangents and bitangents and append them to vertices
        vertices_with_tangents = []
        for i in range(vertex_count):
            offset = i * vertex_stride

            texCoords = vertices[offset + texCoord_offset: offset + texCoord_offset + 2]
            normal = vertices[offset + normal_offset: offset + normal_offset + 3]
            position = vertices[offset + position_offset: offset + position_offset + 3]
            tangent = tangents[i]
            bitangent = bitangents[i]

            # Normalize and handle zero-length vectors
            tangent_norm = np.linalg.norm(tangent)
            if tangent_norm != 0:
                tangent = tangent / tangent_norm

            bitangent_norm = np.linalg.norm(bitangent)
            if bitangent_norm != 0:
                bitangent = bitangent / bitangent_norm

            # Append position, normal, texCoords, tangent, bitangent
            vertices_with_tangents.extend(position)
            vertices_with_tangents.extend(normal)
            vertices_with_tangents.extend(texCoords)
            vertices_with_tangents.extend(tangent)
            vertices_with_tangents.extend(bitangent)

        return vertices_with_tangents

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

        vertex_stride = 14 * self.float_size  # 14 floats per vertex

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 0)
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 3 * self.float_size)
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 6 * self.float_size)
        if tangent_loc >= 0:
            self.enable_vertex_attrib(tangent_loc, 3, vertex_stride, 8 * self.float_size)
        if bitangent_loc >= 0:
            self.enable_vertex_attrib(bitangent_loc, 3, vertex_stride, 11 * self.float_size)

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
        for i, mesh in enumerate(self.object.mesh_list):
            # Skip meshes with no materials
            if not mesh.materials:
                continue

            material = mesh.materials[0]  # Assuming one material per mesh

            # Skip meshes with no faces
            if not mesh.faces:
                continue

            self.apply_material(material)
            vao_index = i
            count = len(mesh.faces) * 3  # Each face is a triangle
            self.bind_and_draw_vao(vao_index, count)

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
