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
        """Create buffers for the surface."""
        vertices, faces = self._generate_surface_geometry()
        mesh = Mesh(vertices, faces)  # Create a Mesh instance with faces
        self.object = SceneObject(mesh_list=[mesh])  # Store in self.object

        # Create buffers for each mesh
        for mesh in self.object.mesh_list:
            # Create and bind VAO
            vao = glGenVertexArrays(1)
            glBindVertexArray(vao)
            self.vaos.append(vao)

            # Convert vertices to numpy array
            vertices_array = np.array(mesh.vertices, dtype=np.float32)

            # Setup VBO
            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
            self.vbos.append(vbo)

            # No EBO needed
            self.ebos.append(None)

            # Setup vertex attributes
            self._setup_vertex_attributes()

            # Unbind VAO
            glBindVertexArray(0)

    def _generate_surface_geometry(self):
        """Generate vertex and face data for the surface."""
        half_width = self.dynamic_attrs["width"] / 2.0
        half_height = self.dynamic_attrs["height"] / 2.0

        # Vertex data: positions and texcoords
        vertices = [
            # Triangle 1
            -half_width, 0.0, half_height, 0.0, 1.0,  # Vertex 0: Top-left
            half_width, 0.0, half_height, 1.0, 1.0,  # Vertex 1: Top-right
            half_width, 0.0, -half_height, 1.0, 0.0,  # Vertex 2: Bottom-right
            # Triangle 2
            half_width, 0.0, -half_height, 1.0, 0.0,  # Vertex 3: Bottom-right
            -half_width, 0.0, -half_height, 0.0, 0.0,  # Vertex 4: Bottom-left
            -half_width, 0.0, half_height, 0.0, 1.0,  # Vertex 5: Top-left
        ]

        # Faces: list of tuples of vertex indices
        faces = [(0, 1, 2), (3, 4, 5)]

        return vertices, faces

    def _setup_vertex_attributes(self):
        """Setup vertex attribute pointers."""
        float_size = 4
        vertex_stride = 5 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")

        if position_loc >= 0:
            glEnableVertexAttribArray(position_loc)
            glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        if tex_coords_loc >= 0:
            glEnableVertexAttribArray(tex_coords_loc)
            glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

    @common_funcs
    def render(self):
        """Render the surface."""
        self.shader_engine.use_shader_program()
        glUniformMatrix4fv(glGetUniformLocation(self.shader_engine.shader_program, "model"),
                           1, GL_FALSE, glm.value_ptr(self.model_matrix))
        self.set_constant_uniforms()

        for mesh in self.object.mesh_list:
            vao_index = self.object.mesh_list.index(mesh)
            glBindVertexArray(self.vaos[vao_index])
            glDrawArrays(GL_TRIANGLES, 0, len(mesh.faces) * 3)
            glBindVertexArray(0)
