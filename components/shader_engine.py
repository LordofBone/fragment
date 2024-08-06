from OpenGL.GL import *


class ShaderEngine:
    def __init__(self, vertex_shader_path, fragment_shader_path, tess_control_shader_path=None,
                 tess_eval_shader_path=None):
        """
        Initialize the ShaderEngine with the paths of the vertex, fragment, tessellation control, and tessellation evaluation shaders.
        """
        self.vertex_shader_path = vertex_shader_path
        self.fragment_shader_path = fragment_shader_path
        self.tess_control_shader_path = tess_control_shader_path
        self.tess_eval_shader_path = tess_eval_shader_path
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
            shader_type_str = {
                GL_VERTEX_SHADER: 'vertex',
                GL_FRAGMENT_SHADER: 'fragment',
                GL_TESS_CONTROL_SHADER: 'tessellation control',
                GL_TESS_EVALUATION_SHADER: 'tessellation evaluation'
            }.get(shader_type, 'unknown')
            glDeleteShader(shader)  # Clean up shader resource on error
            raise RuntimeError(f"Error compiling {shader_type_str} shader: {log.decode()}")

        return shader

    def create_shader_program(self, vertex_shader_code, fragment_shader_code, tess_control_shader_code=None,
                              tess_eval_shader_code=None):
        """
        Create and link a shader program from vertex, fragment, and optionally tessellation control and evaluation shader codes.
        """
        vertex_shader = self.compile_shader(vertex_shader_code, GL_VERTEX_SHADER)
        fragment_shader = self.compile_shader(fragment_shader_code, GL_FRAGMENT_SHADER)

        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)

        if tess_control_shader_code:
            tess_control_shader = self.compile_shader(tess_control_shader_code, GL_TESS_CONTROL_SHADER)
            glAttachShader(shader_program, tess_control_shader)

        if tess_eval_shader_code:
            tess_eval_shader = self.compile_shader(tess_eval_shader_code, GL_TESS_EVALUATION_SHADER)
            glAttachShader(shader_program, tess_eval_shader)

        glLinkProgram(shader_program)

        # Check the linking status
        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)  # Clean up program resource on error
            glDeleteShader(vertex_shader)
            glDeleteShader(fragment_shader)
            if tess_control_shader_code:
                glDeleteShader(tess_control_shader)
            if tess_eval_shader_code:
                glDeleteShader(tess_eval_shader)
            raise RuntimeError(f"Error linking shader program: {log.decode()}")

        # Shaders can be deleted after linking to the program
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        if tess_control_shader_code:
            glDeleteShader(tess_control_shader)
        if tess_eval_shader_code:
            glDeleteShader(tess_eval_shader)

        return shader_program

    def init_shaders(self):
        """
        Initialize shaders by loading, compiling, and linking them into a shader program.
        """
        vertex_shader_code = self.load_shader_code(self.vertex_shader_path)
        fragment_shader_code = self.load_shader_code(self.fragment_shader_path)

        tess_control_shader_code = self.load_shader_code(
            self.tess_control_shader_path) if self.tess_control_shader_path else None
        tess_eval_shader_code = self.load_shader_code(
            self.tess_eval_shader_path) if self.tess_eval_shader_path else None

        self.shader_program = self.create_shader_program(
            vertex_shader_code,
            fragment_shader_code,
            tess_control_shader_code,
            tess_eval_shader_code
        )

    def use(self):
        """
        Use the compiled shader program.
        """
        if self.shader_program:
            glUseProgram(self.shader_program)
        else:
            raise RuntimeError("Shader program not initialized. Call init_shaders() first.")
