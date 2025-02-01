import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, with_gl_render_state


class SkyboxRenderer(AbstractRenderer):
    def __init__(self, renderer_name, **kwargs):
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.skybox_vao = None
        self.skybox_vbo = None

    def supports_shadow_mapping(self):
        return False

    def create_buffers(self):
        """Create buffers for the skybox."""
        vertices = self._generate_skybox_vertices()
        vertices_array = np.array(vertices, dtype=np.float32)

        self.skybox_vao = glGenVertexArrays(1)
        self.skybox_vbo = glGenBuffers(1)

        glBindVertexArray(self.skybox_vao)
        self._setup_vertex_buffer(vertices_array)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def _generate_skybox_vertices(self):
        """Generate the vertex data for the skybox."""
        return [
            -1.0,
            1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            -1.0,
            1.0,
            -1.0,
            -1.0,
            -1.0,
            -1.0,
            1.0,
            1.0,
            -1.0,
            1.0,
        ]

    def _setup_vertex_buffer(self, vertices_array):
        """Setup the vertex buffer object."""
        glBindBuffer(GL_ARRAY_BUFFER, self.skybox_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * vertices_array.itemsize, ctypes.c_void_p(0))

    @with_gl_render_state
    def render(self):
        glDepthFunc(
            GL_LEQUAL
        )  # Change depth function so depth test passes when values are equal to depth buffer's content
        self._set_shader_matrices()

        glBindVertexArray(self.skybox_vao)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)
        glDepthFunc(GL_LESS)  # Set depth function back to default

    def _set_shader_matrices(self):
        """Set the view and projection matrices for the skybox shader."""
        view_matrix = glm.mat4(glm.mat3(self.view))  # Remove translation from the view matrix
        projection_matrix = self.projection

        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "view"), 1, GL_FALSE, glm.value_ptr(view_matrix)
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "projection"),
            1,
            GL_FALSE,
            glm.value_ptr(projection_matrix),
        )

        # Additional uniforms for the skybox shader up-scaling
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "uOffset"),
            self.dynamic_attrs.get("upscale_offset", 0.005),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "uLobes"),
            self.dynamic_attrs.get("upscale_lobes", 3.0),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "uSampleRadius"),
            self.dynamic_attrs.get("upscale_sample_radius", 2),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "uStepSize"),
            self.dynamic_attrs.get("upscale_step_size", 0.5),
        )
