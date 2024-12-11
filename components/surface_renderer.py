import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class Mesh:
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces


class SceneObject:
    def __init__(self, mesh_list):
        self.mesh_list = mesh_list


class SurfaceRenderer(AbstractRenderer):
    def __init__(self, renderer_name, **kwargs):
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.vaos = []
        self.vbos = []
        self.ebos = []
        self.object = None  # Initialize self.object

    def supports_shadow_mapping(self):
        return True

    def create_buffers(self):
        """Create buffers for the surface with normals, tangents, and bitangents."""
        vertices, faces = self._generate_surface_geometry()
        # vertices currently: (x,y,z,u,v)
        # We will add normal(3), tangent(3), bitangent(3) = total 14 floats per vertex

        # Compute normal, tangent, bitangent for a flat surface:
        # Normal is (0,1,0) since this is a horizontal plane.
        # Tangent can be (1,0,0) along x-axis
        # Bitangent can be (0,0,-1) along z-axis (assuming a right-handed system)
        normal = (0.0, 1.0, 0.0)
        tangent = (1.0, 0.0, 0.0)
        bitangent = (0.0, 0.0, -1.0)

        # Convert vertices to array for modification
        verts = np.array(vertices, dtype=np.float32).reshape(-1, 5)  # (x,y,z,u,v)

        # Expand to (x,y,z, nx,ny,nz, u,v, tx,ty,tz, bx,by,bz)
        # We'll just assign the same tangent/bitangent for all vertices since it's a flat surface.
        expanded = []
        for v in verts:
            x, y, z, u, vtex = v
            expanded.append(
                [
                    x,
                    y,
                    z,
                    normal[0],
                    normal[1],
                    normal[2],
                    u,
                    vtex,
                    tangent[0],
                    tangent[1],
                    tangent[2],
                    bitangent[0],
                    bitangent[1],
                    bitangent[2],
                ]
            )
        expanded = np.array(expanded, dtype=np.float32)

        mesh = Mesh(expanded, faces)
        self.object = SceneObject(mesh_list=[mesh])

        # Create and bind VAO
        for mesh in self.object.mesh_list:
            vao = glGenVertexArrays(1)
            glBindVertexArray(vao)
            self.vaos.append(vao)

            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, mesh.vertices.nbytes, mesh.vertices, GL_STATIC_DRAW)
            self.vbos.append(vbo)
            self.ebos.append(None)

            self._setup_vertex_attributes()
            glBindVertexArray(0)

    def _generate_surface_geometry(self):
        """Generate vertex and face data for the surface."""
        half_width = self.dynamic_attrs["width"] / 2.0
        half_height = self.dynamic_attrs["height"] / 2.0

        # Vertex layout: x,y,z,u,v
        vertices = [
            # Triangle 1
            -half_width,
            0.0,
            half_height,
            0.0,
            1.0,  # V0 top-left
            half_width,
            0.0,
            half_height,
            1.0,
            1.0,  # V1 top-right
            half_width,
            0.0,
            -half_height,
            1.0,
            0.0,  # V2 bottom-right
            # Triangle 2
            half_width,
            0.0,
            -half_height,
            1.0,
            0.0,  # V3 bottom-right
            -half_width,
            0.0,
            -half_height,
            0.0,
            0.0,  # V4 bottom-left
            -half_width,
            0.0,
            half_height,
            0.0,
            1.0,  # V5 top-left
        ]

        faces = [(0, 1, 2), (3, 4, 5)]

        return vertices, faces

    def _setup_vertex_attributes(self):
        """Setup vertex attribute pointers for position, normal, texCoords, tangent, bitangent."""
        float_size = 4
        # 14 floats per vertex: x,y,z(3), nx,ny,nz(3), u,v(2), tx,ty,tz(3), bx,by,bz(3)
        vertex_stride = 14 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        # Position at offset 0
        if position_loc >= 0:
            glEnableVertexAttribArray(position_loc)
            glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        # Normal at offset 3 floats
        if normal_loc >= 0:
            glEnableVertexAttribArray(normal_loc)
            glVertexAttribPointer(normal_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

        # TexCoords at offset 6 floats
        if tex_coords_loc >= 0:
            glEnableVertexAttribArray(tex_coords_loc)
            glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(6 * float_size))

        # Tangent at offset 8 floats
        if tangent_loc >= 0:
            glEnableVertexAttribArray(tangent_loc)
            glVertexAttribPointer(tangent_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(8 * float_size))

        # Bitangent at offset 11 floats
        if bitangent_loc >= 0:
            glEnableVertexAttribArray(bitangent_loc)
            glVertexAttribPointer(bitangent_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(11 * float_size))

    @common_funcs
    def render(self):
        """Render the surface."""
        self.shader_engine.use_shader_program()
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "model"),
            1,
            GL_FALSE,
            glm.value_ptr(self.model_matrix),
        )
        self.set_constant_uniforms()

        for mesh in self.object.mesh_list:
            vao_index = self.object.mesh_list.index(mesh)
            glBindVertexArray(self.vaos[vao_index])
            glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
            glBindVertexArray(0)
