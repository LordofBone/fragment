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
        """
        Create buffers for each mesh material in the object's mesh list.

        This method iterates through each mesh in the object's mesh list and processes its materials.
        For each material, it extracts vertex data and performs transformations to reorder and enhance
        vertex attributes. The method constructs vertex buffer objects (VBOs) and vertex array objects
        (VAOs) for handling the vertex data in OpenGL. It accounts for tangents and bitangents calculations
        necessary for advanced shading techniques. The method appends created VBOs, VAOs, and a mapping
        relation for each material to the respective internal lists.

        Attributes
        ----------
        vaos : list
            A list to store vertex array objects for the processed meshes.
        vbos : list
            A list to store vertex buffer objects for the processed meshes.
        mesh_material_index_map : list
            A list to store the mapping between mesh index and material names for the
            processed materials.

        Parameters
        ----------
        self : object
            The instance of the object containing mesh_list attribute which holds
            the meshes to be processed.

        """
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
                reordered = np.column_stack(
                    (
                        vertices_array[:, 5],  # x
                        vertices_array[:, 6],  # y
                        vertices_array[:, 7],  # z
                        vertices_array[:, 2],  # nx
                        vertices_array[:, 3],  # ny
                        vertices_array[:, 4],  # nz
                        vertices_array[:, 0],  # u
                        vertices_array[:, 1],  # v
                    )
                )

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
        """
        Computes the tangent and bitangent vectors for a given set of vertices. The input
        vertices are expected to be in the format of N x 8 array, where each row consists
        of position (x, y, z), normal (nx, ny, nz), and texture coordinates (u, v). The
        method appends calculated tangent and bitangent vectors to each vertex, resulting
        in an output array of N x 14.

        Parameters:
            verts (np.ndarray): An array of shape (N, 8) containing vertices data which
                                include positions, normals, and texture coordinates.

        Returns:
            np.ndarray: An array of shape (N, 14), where each row is composed of the original
                        input data followed by calculated tangent (tx, ty, tz) and bitangent
                        (bx, by, bz) vectors.
        """
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
        """
        Creates a Vertex Buffer Object (VBO) using the provided array of vertices.
        The VBO is generated, bound to the GL_ARRAY_BUFFER target, and loaded
        with the vertex data from the given array. The data is specified to be
        static and drawn frequently.

        Parameters:
            vertices_array: numpy.ndarray
                An array of vertex data used to populate the VBO.

        Returns:
            int: An integer representing the generated VBO handle.
        """
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self, with_tangents=False):
        """
        Creates a Vertex Array Object (VAO) and sets up vertex attributes for
        rendering. The attributes can include position, normal, texture coordinates,
        and optionally tangent and bitangent vectors if specified.

        The method initializes a new VAO, binds it, and then retrieves attribute
        locations from the shader program. It enables vertex attributes based on
        whether tangents are included or not, with specific offsets for each type
        of attribute data within the vertex layout.

        Parameters:
        with_tangents: bool
            Flag indicating whether tangent and bitangent attributes should be
            included in the vertex layout. If True, the VAO includes these
            attributes; otherwise, it does not.

        Returns:
        int
            The ID of the created VAO used for rendering operations.
        """
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
        """
        Calculate the total vertex stride from a given vertex format.

        The method parses the input vertex format string, which is expected to be
        composed of parts separated by underscores, with each part containing a
        single character specification followed by an integer. The integer indicates
        the number of floats in that portion of the vertex. It totals these numbers
        to compute the total stride count.

        Args:
            vertex_format (str): A string representing the format of the vertex.

        Returns:
            int: The total vertex stride calculated from the format.
        """
        count = 0
        format_parts = vertex_format.split("_")
        for part in format_parts:
            num = int(part[1])  # number of floats
            count += num
        return count

    def enable_vertex_attrib(self, location, size, stride, pointer_offset):
        """
        Enables a vertex attribute array and defines an array of generic vertex
        attribute data. This function is primarily used in OpenGL to specify the
        organization of data in the vertex buffer and to pass it to the vertex
        shader.

        Parameters:
        location (int): The location of the vertex attribute to be enabled.
        size (int): The number of components per attribute. Must be 1, 2, 3, or 4.
        stride (int): The byte offset between consecutive vertex attributes.
        pointer_offset (int): The offset of the first component of the first
        generic vertex attribute in the buffer.
        """
        if location >= 0:
            glEnableVertexAttribArray(location)
            glVertexAttribPointer(location, size, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(pointer_offset))

    @common_funcs
    def render(self):
        """
        Render all meshes of the object with their corresponding materials.

        This method iterates over each mesh in the object's mesh list. For each
        material in the mesh, it checks if the material has associated vertices. If
        vertices are present, it applies the material to the context and calculates
        the number of vertices to draw based on the vertex stride of the material.
        Then, it binds and draws the vertex array object for that material. The
        vao_counter is incremented after each draw call to ensure uniqueness for
        each material's vertex array object.

        Raises:
            Any exceptions pertaining to applying material or drawing a vertex
            array may be raised during execution.
        """
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
        """
        Old material method; to be removed.
        """
        glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
        glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

    def bind_and_draw_vao(self, vao_index, count):
        """
        Binds a Vertex Array Object (VAO) and issues a draw call for rendering.

        This method activates a specific VAO from a list of VAOs and performs a
        drawing operation using OpenGL's glDrawArrays function. After drawing,
        it unbinds the VAO. This is typically used in rendering pipelines
        where objects are drawn using vertex data stored in a VAO.

        Parameters:
            vao_index: int
                The index of the VAO to bind from the list of available VAOs.
            count: int
                The number of vertices to render.
        """
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
