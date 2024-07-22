import glm
import numpy as np
import pygame
import pywavefront
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.raw.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT
from pygame.locals import QUIT

from path_config import vertex_shader_path, fragment_shader_path
from shader_engine import ShaderEngine


class ModelRenderer:
    def __init__(self, obj_path, vertex_shader_path, fragment_shader_path, window_size=(800, 600)):
        self.obj_path = obj_path
        self.vertex_shader_path = vertex_shader_path
        self.fragment_shader_path = fragment_shader_path
        self.window_size = window_size
        self.scene = None
        self.shader_program = None
        self.vbos = []
        self.vaos = []
        self.model = glm.mat4(1)
        self.view = None
        self.projection = None
        self.diffuseMap = None
        self.normalMap = None
        self.heightMap = None
        self.environmentMap = None

        self.setup_pygame()
        self.init_shaders()
        self.load_model()

    def setup_pygame(self):
        pygame.init()
        pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)

    def draw_fps(self, clock):
        """Renders the FPS counter at the top right corner."""
        fps = str(int(clock.get_fps()))
        fps_surface = self.font.render(fps, True, pygame.Color('white'))
        fps_data = pygame.image.tostring(fps_surface, "RGBA", True)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glWindowPos2i(self.window_size[0] - fps_surface.get_width() - 10, 20)
        glDrawPixels(fps_surface.get_width(), fps_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, fps_data)

        glDisable(GL_BLEND)

    def init_shaders(self):
        shader_engine = ShaderEngine(self.vertex_shader_path, self.fragment_shader_path)
        shader_engine.init_shaders()
        self.shader_program = shader_engine.shader_program

    def load_model(self):
        self.scene = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

    def load_texture(self, path, texture):
        """Load and bind a texture from a file to a texture unit."""
        surface = pygame.image.load(path)
        img_data = pygame.image.tostring(surface, "RGB", True)
        width, height = surface.get_size()
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, 16.0)

    def load_cubemap(self, folder_path, texture):
        """Load and bind a cubemap texture from a folder."""
        faces = ['right.png', 'left.png', 'top.png', 'bottom.png', 'front.png', 'back.png']
        glBindTexture(GL_TEXTURE_CUBE_MAP, texture)
        for i, face in enumerate(faces):
            surface = pygame.image.load(folder_path + face)
            img_data = pygame.image.tostring(surface, "RGB", True)
            width, height = surface.get_size()
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE,
                         img_data)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAX_ANISOTROPY_EXT, 16.0)
        glGenerateMipmap(GL_TEXTURE_CUBE_MAP)

    def draw_model(self):
        self.model = glm.rotate(glm.mat4(1), pygame.time.get_ticks() / 2000.0, glm.vec3(0, 3, 0))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'model'), 1, GL_FALSE, glm.value_ptr(self.model))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'view'), 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(glGetUniformLocation(self.shader_program, 'projection'), 1, GL_FALSE,
                           glm.value_ptr(self.projection))

        # Set the light and view positions
        lightPosition = glm.vec3(3.0, 3.0, 3.0)  # New light position
        lightStrength = 0.8  # Reduce light strength
        viewPosition = self.camera_pos
        glUniform3fv(glGetUniformLocation(self.shader_program, 'lightPosition'), 1, glm.value_ptr(lightPosition))
        glUniform3fv(glGetUniformLocation(self.shader_program, 'viewPosition'), 1, glm.value_ptr(viewPosition))
        glUniform1f(glGetUniformLocation(self.shader_program, 'lightStrength'), lightStrength)

        for mesh in self.scene.mesh_list:
            material = self.scene.materials['Material']
            glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
            glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
            glMaterialf(GL_FRONT, GL_SHININESS, min(128, material.shininess))

            for vao in self.vaos:
                glBindVertexArray(vao)
                glDrawArrays(GL_TRIANGLES, 0, len(self.vertices) // 8)
            glBindVertexArray(0)

    def mainloop(self):
        clock = pygame.time.Clock()
        glEnable(GL_DEPTH_TEST)
        glUseProgram(self.shader_program)

        self.create_buffers()
        self.setup_camera()
        self.load_textures()

        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            self.draw_model()
            self.draw_fps(clock)

            pygame.display.flip()
            clock.tick(60)

    def create_buffers(self):
        for name, material in self.scene.materials.items():
            self.vertices = material.vertices
            vertices_array = np.array(self.vertices, dtype=np.float32)

            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
            self.vbos.append(vbo)

            vao = glGenVertexArrays(1)
            glBindVertexArray(vao)

            float_size = 4
            vertex_stride = 8 * float_size

            position_loc = glGetAttribLocation(self.shader_program, "position")
            tex_coords_loc = glGetAttribLocation(self.shader_program, "textureCoords")
            normal_loc = glGetAttribLocation(self.shader_program, "normal")

            glEnableVertexAttribArray(position_loc)
            glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(5 * float_size))

            glEnableVertexAttribArray(tex_coords_loc)
            glVertexAttribPointer(tex_coords_loc, 2, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

            glEnableVertexAttribArray(normal_loc)
            glVertexAttribPointer(normal_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(2 * float_size))

            self.vaos.append(vao)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindVertexArray(0)

    def setup_camera(self):
        """
        Set up the camera with a more zoomed out and elevated position.
        """
        self.camera_pos = glm.vec3(4, 2, 4)  # Increased y-coordinate to move the camera up
        self.view = glm.lookAt(self.camera_pos, glm.vec3(0, 0, 0), glm.vec3(0, 1, 0))
        self.projection = glm.perspective(glm.radians(45), self.window_size[0] / self.window_size[1], 0.1, 100)

    def load_textures(self):
        # Load and bind diffuse map
        self.diffuseMap = glGenTextures(1)
        self.load_texture('textures/diffuse/crystal.png', self.diffuseMap)

        # Load and bind normal map
        self.normalMap = glGenTextures(1)
        self.load_texture('textures/normals/crystal.png', self.normalMap)

        # Load and bind height map
        self.heightMap = glGenTextures(1)
        self.load_texture('textures/height/crystal.png', self.heightMap)

        # Load and bind environment map (assumed to be a cubemap)
        self.environmentMap = glGenTextures(1)
        self.load_cubemap('textures/cube/mountain_lake/', self.environmentMap)

        glUseProgram(self.shader_program)

        # Bind the diffuse texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'diffuseMap'), 0)

        # Bind the normal map
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.normalMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'normalMap'), 1)

        # Bind the height map
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.heightMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'heightMap'), 2)

        # Bind the environment map
        glActiveTexture(GL_TEXTURE3)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.environmentMap)
        glUniform1i(glGetUniformLocation(self.shader_program, 'environmentMap'), 3)


if __name__ == "__main__":
    vertex_shader_path = vertex_shader_path
    fragment_shader_path = fragment_shader_path
    model_renderer = ModelRenderer("models/pyramid.obj", vertex_shader_path, fragment_shader_path)
    model_renderer.mainloop()
