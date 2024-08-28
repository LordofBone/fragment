from OpenGL.GL import *


class ShaderEngine:
    def __init__(self, vertex_shader_path, fragment_shader_path):
        self.shader_program = self.create_shader_program(vertex_shader_path, fragment_shader_path)

    def create_shader_program(self, vertex_shader_path, fragment_shader_path):
        vertex_shader = self._create_and_compile_shader(vertex_shader_path, GL_VERTEX_SHADER)
        fragment_shader = self._create_and_compile_shader(fragment_shader_path, GL_FRAGMENT_SHADER)

        shader_program = self._link_shader_program(vertex_shader, fragment_shader)

        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

        return shader_program

    def _create_and_compile_shader(self, shader_path, shader_type):
        """Load, compile, and return a shader."""
        shader_source = self._load_shader_code(shader_path)
        return self._compile_shader(shader_source, shader_type)

    def _load_shader_code(self, shader_file):
        """Load the shader code from a file."""
        with open(shader_file, "r") as file:
            return file.read()

    def _compile_shader(self, source, shader_type):
        """Compile the shader source code."""
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            log = glGetShaderInfoLog(shader)
            shader_type_str = "vertex" if shader_type == GL_VERTEX_SHADER else "fragment"
            glDeleteShader(shader)
            raise RuntimeError(f"Error compiling {shader_type_str} shader: {log.decode()}")

        return shader

    def _link_shader_program(self, vertex_shader, fragment_shader):
        """Link the vertex and fragment shaders into a shader program."""
        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)
        glLinkProgram(shader_program)

        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)
            raise RuntimeError(f"Error linking shader program: {log.decode()}")

        return shader_program
