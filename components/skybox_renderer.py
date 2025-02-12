import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, with_gl_render_state


class SkyboxRenderer(AbstractRenderer):
    """
    Renders a skybox by drawing a cube around the scene.
    The shader transforms the vertices in a way that achieves the illusion
    of a surrounding environment.
    """

    def __init__(self, renderer_name, **kwargs):
        """
        Initialize the skybox renderer with a name and possible additional kwargs.
        """
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.skybox_vao = None
        self.skybox_vbo = None

    def supports_shadow_mapping(self):
        """
        Skyboxes do not typically receive or cast shadows.
        """
        return False

    def create_buffers(self):
        """
        Generate and bind the necessary buffers (VAO, VBO) for skybox vertices.
        """
        vertices = self._generate_skybox_vertices()
        vertices_array = np.array(vertices, dtype=np.float32)

        self.skybox_vao = glGenVertexArrays(1)
        self.skybox_vbo = glGenBuffers(1)

        glBindVertexArray(self.skybox_vao)
        self._setup_vertex_buffer(vertices_array)
        glBindVertexArray(0)

    def _generate_skybox_vertices(self):
        """
        Return a list of 36 (x,y,z) coords representing the 6 faces of a unit cube.
        """
        return [
            # Positions of each triangle forming a cube around the origin
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
        """
        Upload skybox vertices to the GPU and configure the vertex attribute pointers.
        """
        glBindBuffer(GL_ARRAY_BUFFER, self.skybox_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            0,  # attribute location
            3,  # number of components per vertex
            GL_FLOAT,  # data type
            GL_FALSE,  # normalize?
            3 * vertices_array.itemsize,  # stride
            ctypes.c_void_p(0),
        )

    @with_gl_render_state
    def render(self):
        """
        Render the skybox cube. The depth function is adjusted so drawing
        the cube only affects pixels at the far depth range.
        """
        # Render the skybox with depth function <= so it doesn't clip
        glDepthFunc(GL_LEQUAL)

        # Update matrices in the shader
        self._set_shader_matrices()

        # Draw
        glBindVertexArray(self.skybox_vao)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)

        # Revert depth function
        glDepthFunc(GL_LESS)

    def _set_shader_matrices(self):
        """
        For the skybox, we remove the translation from the view matrix,
        so the skybox appears infinitely far away.
        """
        # Drop the translation component from the view matrix
        view_matrix = glm.mat4(glm.mat3(self.view))
        projection_matrix = self.projection

        # Update the shader uniforms
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "view"), 1, GL_FALSE, glm.value_ptr(view_matrix)
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_engine.shader_program, "projection"),
            1,
            GL_FALSE,
            glm.value_ptr(projection_matrix),
        )

        # Additional custom uniforms for up-scaling or post-effects
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
