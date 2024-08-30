from OpenGL.GL import *


class ShaderEngine:
    def __init__(self, vertex_shader_path=None, fragment_shader_path=None, compute_shader_path=None):
        self.shader_program = self.create_shader_program(vertex_shader_path, fragment_shader_path, compute_shader_path)

    def create_shader_program(self, vertex_shader_path=None, fragment_shader_path=None, compute_shader_path=None):
        shaders = []

        if vertex_shader_path:
            vertex_shader = self._create_and_compile_shader(vertex_shader_path, GL_VERTEX_SHADER)
            shaders.append(vertex_shader)

        if fragment_shader_path:
            fragment_shader = self._create_and_compile_shader(fragment_shader_path, GL_FRAGMENT_SHADER)
            shaders.append(fragment_shader)

        if compute_shader_path:
            compute_shader = self._create_and_compile_shader(compute_shader_path, GL_COMPUTE_SHADER)
            shaders.append(compute_shader)

        shader_program = self._link_shader_program(shaders)

        for shader in shaders:
            glDeleteShader(shader)

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
            shader_type_str = \
                {GL_VERTEX_SHADER: "vertex", GL_FRAGMENT_SHADER: "fragment", GL_COMPUTE_SHADER: "compute"}[shader_type]
            glDeleteShader(shader)
            raise RuntimeError(f"Error compiling {shader_type_str} shader: {log.decode()}")

        return shader

    def _link_shader_program(self, shaders):
        """Link the shaders into a shader program."""
        shader_program = glCreateProgram()

        for shader in shaders:
            glAttachShader(shader_program, shader)

        glLinkProgram(shader_program)

        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)
            raise RuntimeError(f"Error linking shader program: {log.decode()}")

        return shader_program
