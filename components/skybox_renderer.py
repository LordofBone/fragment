import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs
from components.texture_manager import TextureManager

# Get the singleton instance of TextureManager
texture_manager = TextureManager()


class SkyboxRenderer(AbstractRenderer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.skybox_vao = None
        self.skybox_vbo = None

    def create_buffers(self):
        """Create buffers for the skybox."""
        vertices = [
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

        vertices_array = np.array(vertices, dtype=np.float32)

        self.skybox_vao = glGenVertexArrays(1)
        self.skybox_vbo = glGenBuffers(1)

        glBindVertexArray(self.skybox_vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.skybox_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * vertices_array.itemsize, ctypes.c_void_p(0))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def load_textures(self):
        """Load the skybox cubemap."""
        if self.cubemap_folder:
            self.environmentMap = glGenTextures(1)
            env_map_unit = texture_manager.get_texture_unit(self.identifier, "skybox_cubemap")
            glActiveTexture(GL_TEXTURE0 + env_map_unit)
            self.load_cubemap(self.cubemap_folder, self.environmentMap)

    @common_funcs
    def render(self):
        glDepthFunc(
            GL_LEQUAL
        )  # Change depth function so depth test passes when values are equal to depth buffer's content
        """Render the skybox."""
        # Set the view and projection matrices
        view_matrix = glm.mat4(glm.mat3(self.view))  # Remove translation from the view matrix
        projection_matrix = self.projection

        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, "view"), 1, GL_FALSE, glm.value_ptr(view_matrix))
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "projection"), 1, GL_FALSE, glm.value_ptr(projection_matrix)
        )

        glBindVertexArray(self.skybox_vao)
        texture_unit = texture_manager.get_texture_unit(self.identifier, "skybox_cubemap")
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_program, "skybox"), texture_unit)

        glDrawArrays(GL_TRIANGLES, 0, 36)

        glBindVertexArray(0)
        glDepthFunc(GL_LESS)  # Set depth function back to default
