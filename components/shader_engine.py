from OpenGL.GL import *


class ShaderEngine:
    def __init__(self, vertex_shader_path, fragment_shader_path):
        self.shader_program = self.create_shader_program(vertex_shader_path, fragment_shader_path)

    def create_shader_program(self, vertex_shader_path, fragment_shader_path):
        vertex_shader = self.compile_shader(self.load_shader_code(vertex_shader_path), GL_VERTEX_SHADER)
        fragment_shader = self.compile_shader(self.load_shader_code(fragment_shader_path), GL_FRAGMENT_SHADER)

        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)
        glLinkProgram(shader_program)

        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)
            glDeleteShader(vertex_shader)
            glDeleteShader(fragment_shader)
            raise RuntimeError(f"Error linking shader program: {log.decode()}")

        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

        return shader_program

    def load_shader_code(self, shader_file):
        with open(shader_file, 'r') as file:
            return file.read()

    def compile_shader(self, source, shader_type):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            log = glGetShaderInfoLog(shader)
            shader_type_str = 'vertex' if shader_type == GL_VERTEX_SHADER else 'fragment'
            glDeleteShader(shader)
            raise RuntimeError(f"Error compiling {shader_type_str} shader: {log.decode()}")

        return shader
