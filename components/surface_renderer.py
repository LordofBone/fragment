import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, with_gl_render_state


class Mesh:
    """
    Simple container for vertices and faces.
    Faces are typically tuples of (i1, i2, i3) indexes into the vertices array.
    """

    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces


class SceneObject:
    """
    Wraps a list of Mesh objects to represent a single object in the scene.
    """

    def __init__(self, mesh_list):
        self.mesh_list = mesh_list


class SurfaceRenderer(AbstractRenderer):
    """
    Renders a flat surface (plane) in the scene. The surface can be assigned
    normals, tangents, and bitangents for shading or parallax effects.
    """

    def __init__(self, renderer_name, **kwargs):
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.vaos = []
        self.vbos = []
        self.ebos = []
        self.object = None  # Will hold a SceneObject with one or more Meshes

    def supports_shadow_mapping(self):
        """
        Surfaces can receive shadows, so shadow mapping is supported.
        """
        return True

    def create_buffers(self):
        """
        Generate the geometry for the plane, compute per-vertex data (normals, tangents, etc.),
        and upload it to the GPU.
        """
        vertices, faces = self._generate_surface_geometry()

        # For a flat surface, normal is (0,1,0), tangent is (1,0,0), bitangent is (0,0,-1).
        normal = (0.0, 1.0, 0.0)
        tangent = (1.0, 0.0, 0.0)
        bitangent = (0.0, 0.0, -1.0)

        # Layout: (x, y, z, u, v)
        # We'll expand each vertex to include normal, tangent, and bitangent.
        verts = np.array(vertices, dtype=np.float32).reshape(-1, 5)
        expanded = []

        for v in verts:
            x, y, z, u, vtex = v
            expanded.append(
                [
                    x,
                    y,
                    z,  # position
                    normal[0],
                    normal[1],
                    normal[2],
                    u,
                    vtex,  # texCoords
                    tangent[0],
                    tangent[1],
                    tangent[2],
                    bitangent[0],
                    bitangent[1],
                    bitangent[2],
                ]
            )

        expanded = np.array(expanded, dtype=np.float32)

        # Create a single Mesh and SceneObject
        mesh = Mesh(expanded, faces)
        self.object = SceneObject(mesh_list=[mesh])

        # Create VAOs/VBOs for each mesh in the object
        for mesh_obj in self.object.mesh_list:
            vao = glGenVertexArrays(1)
            glBindVertexArray(vao)
            self.vaos.append(vao)

            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, mesh_obj.vertices.nbytes, mesh_obj.vertices, GL_STATIC_DRAW)
            self.vbos.append(vbo)

            # No EBO usage here since we do a simple glDrawArrays, but you could handle indices.
            self.ebos.append(None)

            self._setup_vertex_attributes()
            glBindVertexArray(0)

    def _generate_surface_geometry(self):
        """
        Create vertices and faces for a rectangular surface.

        Returns:
            (vertices, faces):
                vertices is a flat list of (x,y,z,u,v),
                faces is a list of face tuples like (0,1,2).
        """
        half_width = self.dynamic_attrs["width"] / 2.0
        half_height = self.dynamic_attrs["height"] / 2.0

        # Create two triangles forming a plane
        vertices = [
            # Triangle 1
            -half_width,
            0.0,
            half_height,
            0.0,
            1.0,
            half_width,
            0.0,
            half_height,
            1.0,
            1.0,
            half_width,
            0.0,
            -half_height,
            1.0,
            0.0,
            # Triangle 2
            half_width,
            0.0,
            -half_height,
            1.0,
            0.0,
            -half_width,
            0.0,
            -half_height,
            0.0,
            0.0,
            -half_width,
            0.0,
            half_height,
            0.0,
            1.0,
        ]
        faces = [(0, 1, 2), (3, 4, 5)]
        return vertices, faces

    def _setup_vertex_attributes(self):
        """
        Configure the vertex attribute pointers for position, normal,
        texCoords, tangent, and bitangent.
        """
        float_size = 4
        # 14 floats per vertex -> position(3), normal(3), texCoords(2), tangent(3), bitangent(3)
        vertex_stride = 14 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        # position -> offset 0
        if position_loc >= 0:
            glEnableVertexAttribArray(position_loc)
            glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        # normal -> offset 3 floats
        if normal_loc >= 0:
            glEnableVertexAttribArray(normal_loc)
            glVertexAttribPointer(normal_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

        # texCoords -> offset 6 floats
        if tex_coords_loc >= 0:
            glEnableVertexAttribArray(tex_coords_loc)
            glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(6 * float_size))

        # tangent -> offset 8 floats
        if tangent_loc >= 0:
            glEnableVertexAttribArray(tangent_loc)
            glVertexAttribPointer(tangent_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(8 * float_size))

        # bitangent -> offset 11 floats
        if bitangent_loc >= 0:
            glEnableVertexAttribArray(bitangent_loc)
            glVertexAttribPointer(bitangent_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(11 * float_size))

    @with_gl_render_state
    def render(self):
        """
        Render the surface using the currently bound shader and the model matrix.
        """
        self.shader_engine.use_shader_program()

        # Upload model transform
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "model"),
            1,
            GL_FALSE,
            glm.value_ptr(self.model_matrix),
        )

        self.set_constant_uniforms()

        # Indicate to the shader that we are rendering a surface
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "surfaceMapping"), 1)

        # Draw the plane as two triangles
        for mesh_obj in self.object.mesh_list:
            vao_index = self.object.mesh_list.index(mesh_obj)
            glBindVertexArray(self.vaos[vao_index])
            glDrawArrays(GL_TRIANGLES, 0, len(mesh_obj.faces) * 3)
            glBindVertexArray(0)
