import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class SurfaceRenderer(AbstractRenderer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vao = None
        self.vbo = None
        self.ebo = None

    def supports_shadow_mapping(self):
        return True

    def create_buffers(self):
        """Create buffers for the surface."""
        vertices, indices = self._generate_surface_geometry()
        vertices_array = np.array(vertices, dtype=np.float32)
        indices_array = np.array(indices, dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self._setup_vertex_buffer(vertices_array)
        self._setup_index_buffer(indices_array)

        self._setup_vertex_attributes()

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def _generate_surface_geometry(self):
        """Generate vertex and index data for the surface."""
        half_width = self.dynamic_attrs["width"] / 2.0
        half_height = self.dynamic_attrs["height"] / 2.0
        vertices = [
            -half_width,
            0.0,
            half_height,
            0.0,
            1.0,  # Top-left
            half_width,
            0.0,
            half_height,
            1.0,
            1.0,  # Top-right
            half_width,
            0.0,
            -half_height,
            1.0,
            0.0,  # Bottom-right
            -half_width,
            0.0,
            -half_height,
            0.0,
            0.0,  # Bottom-left
        ]
        indices = [0, 1, 2, 2, 3, 0]  # Two triangles forming the quad
        return vertices, indices

    def _setup_vertex_buffer(self, vertices_array):
        """Setup the vertex buffer object."""
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

    def _setup_index_buffer(self, indices_array):
        """Setup the index buffer object."""
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices_array.nbytes, indices_array, GL_STATIC_DRAW)

    def _setup_vertex_attributes(self):
        """Setup vertex attribute pointers."""
        float_size = 4
        vertex_stride = 5 * float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")

        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        glEnableVertexAttribArray(tex_coords_loc)
        glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

    @common_funcs
    def render(self):
        """Render the surface."""
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
