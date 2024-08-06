from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class AdvancedSurfaceRenderer(AbstractRenderer):
    def __init__(self, shader_name, **kwargs):
        super().__init__(shader_name=shader_name, **kwargs)
        self.shader_name = shader_name
        self.environmentMap = None
        self.vao = None

    def create_buffers(self):
        # Create a simple quad (two triangles) that will be tessellated
        vertices = [
            -1.0, -1.0, 0.0,
            1.0, -1.0, 0.0,
            1.0, 1.0, 0.0,
            -1.0, 1.0, 0.0
        ]
        indices = [0, 1, 2, 2, 3, 0]
        vertices_array = np.array(vertices, dtype=np.float32)
        indices_array = np.array(indices, dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices_array.nbytes, indices_array, GL_STATIC_DRAW)

        position_loc = 0
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, 3 * 4, ctypes.c_void_p(0))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def load_textures(self):
        self.environmentMap = glGenTextures(1)
        if self.cubemap_folder:
            self.load_cubemap(self.cubemap_folder, self.environmentMap)

    @common_funcs
    def render(self):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_programs[self.shader_name], 'environmentMap'), 0)

        glBindVertexArray(self.vao)
        glPatchParameteri(GL_PATCH_VERTICES, 4)  # Set the number of vertices per patch
        glDrawElements(GL_PATCHES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
