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
        self.vertex_counts = []
        self.materials = []
        self.vbos = []
        self.vaos = []

        # Optional: If you need to flip the green channel of the normal map,
        # set this uniform accordingly. Ensure your shader uses this uniform.
        self.flip_green_channel = kwargs.get("flip_green_channel", False)

    def supports_shadow_mapping(self):
        return True

    def create_buffers(self):
        """Create buffers for the model."""
        for mesh in self.object.mesh_list:
            for material in mesh.materials:
                vertices = material.vertices
                if not vertices:
                    print(f"Material '{material.name}' has no vertices. Skipping.")
                    continue  # Skip materials with no vertices

                vertex_format = material.vertex_format  # e.g., 'T2F_N3F_V3F'
                vertex_stride = self.get_vertex_stride(vertex_format)
                vertex_count = len(vertices) // vertex_stride

                # Now, calculate tangents and bitangents
                vertices_with_tangents = self.calculate_tangents(vertices, vertex_stride)
                vertices_array = np.array(vertices_with_tangents, dtype=np.float32)

                vbo = self.create_vbo(vertices_array)
                vao = self.create_vao(vbo)  # Pass the VBO to create_vao

                vertex_count = len(vertices_with_tangents) // 12

                # Store counts and buffers
                self.vertex_counts.append(vertex_count)
                self.vbos.append(vbo)
                self.vaos.append(vao)
                self.materials.append(material)

        # Note: Proper handling of normalMatrix occurs in the vertex shader.
        # Ensure that your vertex shader uses the normalMatrix to correctly
        # transform normals and tangents for non-uniform scaling.

        # UV Seams: If you encounter artifacts at UV seams, consider ensuring
        # the model data splits vertices at seams or verifying tangent calculation
        # across those seams.

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

    def calculate_tangents(self, vertices, vertex_stride):
        """Calculate tangent and bitangent vectors for the mesh."""
        vertex_count = len(vertices) // vertex_stride

        # Initialize per-vertex tangents and bitangents
        tangents = [np.zeros(3) for _ in range(vertex_count)]
        bitangents = [np.zeros(3) for _ in range(vertex_count)]

        # Offsets based on vertex format (T2F_N3F_V3F)
        texCoord_offset = 0  # Starts at 0
        normal_offset = texCoord_offset + 2
        position_offset = normal_offset + 3

        # Process vertices in groups of 3 (per triangle)
        for i in range(0, vertex_count, 3):
            i0, i1, i2 = i, i + 1, i + 2

            v0 = np.array(vertices[i0 * vertex_stride + position_offset: i0 * vertex_stride + position_offset + 3])
            v1 = np.array(vertices[i1 * vertex_stride + position_offset: i1 * vertex_stride + position_offset + 3])
            v2 = np.array(vertices[i2 * vertex_stride + position_offset: i2 * vertex_stride + position_offset + 3])

            uv0 = np.array(vertices[i0 * vertex_stride + texCoord_offset: i0 * vertex_stride + texCoord_offset + 2])
            uv1 = np.array(vertices[i1 * vertex_stride + texCoord_offset: i1 * vertex_stride + texCoord_offset + 2])
            uv2 = np.array(vertices[i2 * vertex_stride + texCoord_offset: i2 * vertex_stride + texCoord_offset + 2])

            deltaPos1 = v1 - v0
            deltaPos2 = v2 - v0
            deltaUV1 = uv1 - uv0
            deltaUV2 = uv2 - uv0

            denominator = (deltaUV1[0] * deltaUV2[1] - deltaUV2[0] * deltaUV1[1])
            epsilon = 1e-6  # Small value to prevent division by zero
            if abs(denominator) < epsilon:
                r = 0.0
            else:
                r = 1.0 / denominator

            tangent = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1]) * r
            bitangent = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0]) * r

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

            # Gram-Schmidt Orthogonalization
            n = normal / np.linalg.norm(normal)
            t = tangent - n * np.dot(n, tangent)
            t_norm = np.linalg.norm(t)
            if t_norm > 0.0:
                t = t / t_norm
            else:
                t = np.array([1.0, 0.0, 0.0])

            # Compute handedness
            b = np.cross(n, t)
            handedness = 1.0 if np.dot(b, bitangent) > 0.0 else -1.0

            # Append position, normal, texCoords, tangent (including handedness)
            # 3 (pos) + 3 (normal) + 2 (texCoords) + 3 (tangent) + 1 (handedness) = 12 floats
            vertices_with_tangents.extend(position)
            vertices_with_tangents.extend(normal)
            vertices_with_tangents.extend(texCoords)
            vertices_with_tangents.extend(t)
            vertices_with_tangents.append(handedness)

        return vertices_with_tangents

    def create_vbo(self, vertices_array):
        """Create a Vertex Buffer Object (VBO)."""
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self, vbo):
        """Create a Vertex Array Object (VAO) and configure vertex attributes."""
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)  # Use the provided VBO

        # 12 floats per vertex (not 13)
        vertex_stride = 12 * self.float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        handedness_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangentHandedness")

        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 0)
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 3 * self.float_size)
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 6 * self.float_size)
        if tangent_loc >= 0:
            self.enable_vertex_attrib(tangent_loc, 3, vertex_stride, 8 * self.float_size)
        if handedness_loc >= 0:
            self.enable_vertex_attrib(handedness_loc, 1, vertex_stride, 11 * self.float_size)

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

        # Set a uniform to handle normal map flipping if needed
        # Ensure your fragment shader has a uniform bool "flipGreenChannel"
        if self.flip_green_channel:
            flip_uniform_loc = glGetUniformLocation(self.shader_engine.shader_program, "flipGreenChannel")
            if flip_uniform_loc != -1:
                glUniform1i(flip_uniform_loc, 1)
        else:
            flip_uniform_loc = glGetUniformLocation(self.shader_engine.shader_program, "flipGreenChannel")
            if flip_uniform_loc != -1:
                glUniform1i(flip_uniform_loc, 0)

        # Instead of legacy fixed-function pipeline for materials,
        # pass material properties as uniforms to the shader.
        # This is a placeholder. You must ensure your shader supports these uniforms.
        for material, vao, count in zip(self.materials, self.vaos, self.vertex_counts):
            material_ambient_loc = glGetUniformLocation(self.shader_engine.shader_program, "materialAmbient")
            material_diffuse_loc = glGetUniformLocation(self.shader_engine.shader_program, "materialDiffuse")
            material_specular_loc = glGetUniformLocation(self.shader_engine.shader_program, "materialSpecular")
            material_shininess_loc = glGetUniformLocation(self.shader_engine.shader_program, "materialShininess")

            if material_ambient_loc != -1:
                glUniform3f(material_ambient_loc, material.ambient[0], material.ambient[1], material.ambient[2])
            if material_diffuse_loc != -1:
                glUniform3f(material_diffuse_loc, material.diffuse[0], material.diffuse[1], material.diffuse[2])
            if material_specular_loc != -1:
                glUniform3f(material_specular_loc, material.specular[0], material.specular[1], material.specular[2])
            if material_shininess_loc != -1:
                glUniform1f(material_shininess_loc, min(128.0, material.shininess))

            glBindVertexArray(vao)
            glDrawArrays(GL_TRIANGLES, 0, count)
            glBindVertexArray(0)

    def bind_and_draw_vao(self, vao_index, count):
        """Bind a VAO and issue a draw call."""
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
