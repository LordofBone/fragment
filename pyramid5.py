import pygame
from pygame.locals import QUIT
import pygame.display
import pywavefront
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
import glm


class ModelRenderer:
    def __init__(self, obj_path, window_size=(800, 600)):
        self.obj_path = obj_path
        self.window_size = window_size
        self.scene = None

        self.setup_pygame()
        self.init_shaders()
        self.load_model()

    def setup_pygame(self):
        pygame.init()
        pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL)

    def init_shaders(self):

        self.vertex_shader_code_0 = """
            #version 330 core
            layout(location = 0) in vec2 textureCoords;
            layout(location = 1) in vec3 normal;
            layout(location = 2) in vec3 position;

            uniform mat4 model;
            uniform mat4 view;
            uniform mat4 projection;

            out vec2 TexCoords;
            out vec3 FragPos;
            out vec3 Normal;

            void main() {
                gl_Position = projection * view * model * vec4(position, 1.0);
                TexCoords = textureCoords;
                FragPos = vec3(model * vec4(position, 1.0));
                Normal = mat3(transpose(inverse(model))) * normal;  // Transform normals to world space
            }

        """

        self.fragment_shader_code_0 = """
        #version 330 core
        in vec2 TexCoords;
        in vec3 FragPos;
        in vec3 Normal;

        uniform sampler2D diffuseMap;
        uniform sampler2D normalMap;
        uniform vec3 lightPosition;  // Ensure you set this from your Python code

        out vec4 FragColor;

        void main() {
            // Normalize the fragment normal
            vec3 normal = normalize(Normal);

            // Fetch the normal from the normal map and convert it from [0,1] to [-1,1]
            vec3 mapNormal = texture(normalMap, TexCoords).rgb;
            mapNormal = mapNormal * 2.0 - 1.0; // This assumes the normal map is in tangent space

            // Adjust the normal using the normal map (this is a simplified version assuming normal map is in world space)
            normal = normalize(normal + mapNormal);

            // Compute lighting
            vec3 lightDir = normalize(lightPosition - FragPos);
            float diff = max(dot(normal, lightDir), 0.0);
            vec3 diffuse = diff * texture(diffuseMap, TexCoords).rgb;

            // Combine results
            vec3 ambient = 0.1 * texture(diffuseMap, TexCoords).rgb;  // Simple ambient lighting
            vec3 result = ambient + diffuse;
            FragColor = vec4(result, 1.0);
        }

        """

        self.linked_shaders = self.link_shaders()

    def link_shaders(self):
        """Compiles and links the vertex and fragment shaders."""
        shader = compileProgram(
            compileShader(self.vertex_shader_code_0, GL_VERTEX_SHADER),
            compileShader(self.fragment_shader_code_0, GL_FRAGMENT_SHADER)
        )
        return shader

    def load_model(self):
        self.scene = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

    def load_texture(self, path, texture):
        """Load and bind a texture from a file to a texture unit."""
        surface = pygame.image.load(path)
        img_data = pygame.image.tostring(surface, "RGB", True)
        width, height = surface.get_size()
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, texture)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

    def draw_model(self):

        # Rotate the pyramid
        self.model = glm.mat4(1)
        self.model = glm.rotate(self.model, pygame.time.get_ticks() / 2000, glm.vec3(0, 3, 0))

        # Pass transformation matrices to the vertex shader
        glUniformMatrix4fv(glGetUniformLocation(self.linked_shaders, 'model'), 1, GL_FALSE, glm.value_ptr(self.model))
        glUniformMatrix4fv(glGetUniformLocation(self.linked_shaders, 'view'), 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(glGetUniformLocation(self.linked_shaders, 'projection'), 1, GL_FALSE,
                           glm.value_ptr(self.projection))

        # Pass light position
        glUniform3fv(glGetUniformLocation(self.linked_shaders, 'lightPosition'), 1,
                     glm.value_ptr(glm.vec3(0.9, 0.5, 2.0)))

        for mesh in self.scene.mesh_list:
            material = self.scene.materials['Material']

            glMaterialfv(GL_FRONT, GL_AMBIENT, material.ambient)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, material.diffuse)
            glMaterialfv(GL_FRONT, GL_SPECULAR, material.specular)
            clamped_shininess = min(128, material.shininess)
            glMaterialf(GL_FRONT, GL_SHININESS, clamped_shininess)

            # Bind VAO and draw
            for vao in self.vaos:
                glBindVertexArray(vao)
                glDrawArrays(GL_TRIANGLES, 0, len(self.vertices) // 8)

            glBindVertexArray(0)  # Unbind VAO

    def mainloop(self):
        clock = pygame.time.Clock()
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glUseProgram(self.linked_shaders)

        # Prepare to store VBOs and VAOs
        self.vbos = []
        self.vaos = []

        for name, material in self.scene.materials.items():
            # Extract vertex data
            self.vertices = material.vertices  # This is a list

            # print(self.vertices)

            vertices_array = np.array(self.vertices, dtype=np.float32)  # Convert to a NumPy array

            # Create a VBO
            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)

            self.vbos.append(vbo)
            # Create a VAO
            self.vao = glGenVertexArrays(1)
            glBindVertexArray(self.vao)

            float_size = 4  # size of a float in bytes

            vertex_stride = 8 * float_size  # the total size of attributes per vertex

            # printed order is: [vt, vt, vn, vn, vn, v, v, v] (texture, normal, vertex)
            # [0.586146, 0.02769, -0.0, -1.0, -0.0, 0.0, 0.02602, 2.448633]

            vertexLocation = glGetAttribLocation(self.linked_shaders, "position")
            textureLocation = glGetAttribLocation(self.linked_shaders, "textureCoords")
            normalLocation = glGetAttribLocation(self.linked_shaders, "normal")

            print(
                f"positionLocation: {vertexLocation} "
                f"normalLocation: {normalLocation} "
                f"textureLocation: {textureLocation}"
            )

            # Texture coordinates (location = 0)
            glEnableVertexAttribArray(textureLocation)
            glVertexAttribPointer(index=textureLocation,
                                  size=2,
                                  type=GL_FLOAT,
                                  normalized=GL_FALSE,
                                  stride=vertex_stride,
                                  pointer=ctypes.c_void_p(0))

            # Normals (location = 1)
            glEnableVertexAttribArray(normalLocation)
            glVertexAttribPointer(index=normalLocation,
                                  size=3,
                                  type=GL_FLOAT,
                                  normalized=GL_FALSE,
                                  stride=vertex_stride,
                                  pointer=ctypes.c_void_p(2 * float_size))

            # Vertex coordinates (location = 2)
            glEnableVertexAttribArray(vertexLocation)
            glVertexAttribPointer(index=vertexLocation,
                                  size=3,
                                  type=GL_FLOAT,
                                  normalized=GL_FALSE,
                                  stride=vertex_stride,
                                  pointer=ctypes.c_void_p((3 + 2) * float_size))

        self.vaos.append(self.vao)
        # Unbind VBO/VAO
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        # Camera and transformation matrices
        self.camera_pos = glm.vec3(0, 3, 6)
        self.view = glm.lookAt(self.camera_pos, glm.vec3(0, 0, 0), glm.vec3(0, 1, 0))
        self.projection = glm.perspective(glm.radians(45), 800 / 600, 0.1, 100)

        self.diffuseMap = glGenTextures(1)
        self.normalMap = glGenTextures(1)
        self.load_texture('textures/diffuse/crystal.png', self.diffuseMap)
        self.load_texture('textures/normals/crystal.png', self.normalMap)

        # # Bind the diffuse texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        glUniform1i(glGetUniformLocation(self.linked_shaders, 'diffuseMap'), 0)

        # # The normal map would be used in the shader, adjust shader code accordingly
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.normalMap)
        glUniform1i(glGetUniformLocation(self.linked_shaders, 'normalMap'), 1)

        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    sys.exit()

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            self.draw_model()

            pygame.display.flip()
            clock.tick(60)


if __name__ == "__main__":
    model_renderer = ModelRenderer("objects/pyramid.obj")
    model_renderer.mainloop()
