from OpenGL.GL import *


class ShaderEngine:
    def __init__(self, vertex_shader_path, fragment_shader_path):
        """
        Initialize the ShaderEngine with the paths of the vertex shader and fragment shader.
        """
        self.vertex_shader_path = vertex_shader_path
        self.fragment_shader_path = fragment_shader_path
        self.shader_program = None  # Will hold the compiled shader program

    def load_shader_code(self, shader_file):
        """
        Load shader code from a file.
        """
        try:
            with open(shader_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError(f"Shader file not found: {shader_file}")

    def compile_shader(self, source, shader_type):
        """
        Compile the shader code.
        """
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        # Check the compilation status
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            log = glGetShaderInfoLog(shader)
            shader_type_str = 'vertex' if shader_type == GL_VERTEX_SHADER else 'fragment'
            glDeleteShader(shader)  # Clean up shader resource on error
            raise RuntimeError(f"Error compiling {shader_type_str} shader: {log.decode()}")

        return shader

    def create_shader_program(self, vertex_shader_code, fragment_shader_code):
        """
        Create and link a shader program from vertex and fragment shader codes.
        """
        vertex_shader = self.compile_shader(vertex_shader_code, GL_VERTEX_SHADER)
        fragment_shader = self.compile_shader(fragment_shader_code, GL_FRAGMENT_SHADER)

        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)
        glLinkProgram(shader_program)

        # Check the linking status
        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)  # Clean up program resource on error
            glDeleteShader(vertex_shader)
            glDeleteShader(fragment_shader)
            raise RuntimeError(f"Error linking shader program: {log.decode()}")

        # Shaders can be deleted after linking to the program
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

        return shader_program

    def init_shaders(self):
        """
        Initialize shaders by loading, compiling, and linking them into a shader program.
        """
        vertex_shader_code = self.load_shader_code(self.vertex_shader_path)
        fragment_shader_code = self.load_shader_code(self.fragment_shader_path)

        self.shader_program = self.create_shader_program(vertex_shader_code, fragment_shader_code)

    def use(self):
        """
        Use the compiled shader program.
        """
        if self.shader_program:
            glUseProgram(self.shader_program)
        else:
            raise RuntimeError("Shader program not initialized. Call init_shaders() first.")
