import os

from OpenGL.GL import *


class ShaderEngine:
    """
    ShaderEngine manages the creation, compilation, and linking of shaders:
    - Standard vertex/fragment programs
    - Compute shaders
    - Shadow-mapping shaders
    It also handles #include directives, referencing a 'common' GLSL include directory.
    """
    def __init__(
        self,
        vertex_shader_path,
        fragment_shader_path,
        compute_shader_path=None,
        shadow_vertex_shader_path=None,
        shadow_fragment_shader_path=None,
        shader_base_dir="shaders",
            common_dir_name="common",
    ):
        """
        Initialize the ShaderEngine.

        Args:
            vertex_shader_path (str): Path (relative to `shader_base_dir`) to the vertex shader.
            fragment_shader_path (str): Path (relative) to the fragment shader.
            compute_shader_path (str): Path to the compute shader (optional).
            shadow_vertex_shader_path (str): Path to the shadow vertex shader (optional).
            shadow_fragment_shader_path (str): Path to the shadow fragment shader (optional).
            shader_base_dir (str): Base directory for all shader files.
            common_dir_name (str): Subdirectory for common GLSL includes.
        """
        self.shader_base_dir = shader_base_dir
        self.common_dir_name = common_dir_name

        # Main rendering shaders
        self.shader_program = None
        if vertex_shader_path or fragment_shader_path:
            self.shader_program = self.create_shader_program(vertex_shader_path, fragment_shader_path)

        # Compute shader
        self.compute_shader_program = None
        if compute_shader_path:
            self.compute_shader_program = self.create_compute_shader_program(compute_shader_path)

        # Shadow shaders
        self.shadow_shader_program = None
        if shadow_vertex_shader_path or shadow_fragment_shader_path:
            self.shadow_shader_program = self.create_shader_program(
                shadow_vertex_shader_path,
                shadow_fragment_shader_path
            )

    # --------------------------------------------------------------------------
    # Public Methods for Using Programs
    # --------------------------------------------------------------------------
    def use_shader_program(self):
        """Activate the main vertex/fragment shader program."""
        if self.shader_program:
            glUseProgram(self.shader_program)

    def use_compute_shader_program(self):
        """Activate the compute shader program."""
        if self.compute_shader_program:
            glUseProgram(self.compute_shader_program)

    def use_shadow_shader_program(self):
        """Activate the shadow vertex/fragment shader program."""
        if self.shadow_shader_program:
            glUseProgram(self.shadow_shader_program)

    def delete_shader_programs(self):
        """
        Delete all shader programs to free OpenGL resources.
        """
        if self.shader_program:
            glDeleteProgram(self.shader_program)
        if self.compute_shader_program:
            glDeleteProgram(self.compute_shader_program)
        if self.shadow_shader_program:
            glDeleteProgram(self.shadow_shader_program)

    # --------------------------------------------------------------------------
    # Creation of Shader Programs
    # --------------------------------------------------------------------------
    def create_shader_program(self, vertex_shader_path, fragment_shader_path):
        """
        Create and link a standard vertex/fragment shader program.
        """
        shaders = []

        if vertex_shader_path:
            vertex_shader = self._create_and_compile_shader(vertex_shader_path, GL_VERTEX_SHADER)
            shaders.append(vertex_shader)

        if fragment_shader_path:
            fragment_shader = self._create_and_compile_shader(fragment_shader_path, GL_FRAGMENT_SHADER)
            shaders.append(fragment_shader)

        shader_program = self._link_shader_program(shaders)

        # Cleanup after linking
        for shader in shaders:
            glDeleteShader(shader)

        return shader_program

    def create_compute_shader_program(self, compute_shader_path):
        """
        Create and link a compute shader program.
        """
        compute_shader = self._create_and_compile_shader(compute_shader_path, GL_COMPUTE_SHADER)

        shader_program = glCreateProgram()
        glAttachShader(shader_program, compute_shader)
        glLinkProgram(shader_program)

        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)
            raise RuntimeError(f"Error linking compute shader program: {log.decode()}")

        glDeleteShader(compute_shader)
        return shader_program

    # --------------------------------------------------------------------------
    # Internal Utilities for Loading and Compiling Shaders
    # --------------------------------------------------------------------------
    def _create_and_compile_shader(self, shader_path, shader_type):
        """
        Load source from file, compile, and return the shader handle.
        """
        shader_source = self._load_shader_code(shader_path)
        return self._compile_shader(shader_source, shader_type)

    def _load_shader_code(self, shader_file):
        """
        Load shader code from file, then process #include directives.
        """
        full_path = os.path.join(self.shader_base_dir, shader_file)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Shader file not found: {full_path}")

        with open(full_path, "r", encoding="utf-8") as file:
            source = file.read()

        # Handle includes recursively
        source = self._process_includes(source, os.path.dirname(full_path))
        return source

    def _process_includes(self, source, current_dir):
        """
        Recursively process #include "filename" directives.

        Search order:
          1) current_dir
          2) shader_base_dir/common_dir_name
        """
        lines = source.split("\n")
        processed_lines = []

        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("#include"):
                start_idx = line_stripped.find('"')
                end_idx = line_stripped.find('"', start_idx + 1)
                if start_idx == -1 or end_idx == -1:
                    raise RuntimeError('Malformed #include directive. Must be #include "filename"')

                include_filename = line_stripped[start_idx + 1:end_idx]

                # Check local directory first
                include_path_local = os.path.join(current_dir, include_filename)
                if os.path.isfile(include_path_local):
                    use_path = include_path_local
                else:
                    # Fallback to base/common directory
                    fallback_path = os.path.join(self.shader_base_dir, self.common_dir_name, include_filename)
                    if os.path.isfile(fallback_path):
                        use_path = fallback_path
                    else:
                        raise FileNotFoundError(
                            f"Included shader file not found in either:\n  {include_path_local}\n  {fallback_path}"
                        )

                with open(use_path, "r", encoding="utf-8") as inc_file:
                    inc_source = inc_file.read()

                # Recursively process includes in the included file
                inc_source = self._process_includes(inc_source, os.path.dirname(use_path))
                processed_lines.append(inc_source)
            else:
                processed_lines.append(line)

        return "\n".join(processed_lines)

    def _compile_shader(self, source, shader_type):
        """
        Compile the GLSL source for a specific shader type (vertex, fragment, or compute).
        """
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            log = glGetShaderInfoLog(shader)
            shader_type_str = {
                GL_VERTEX_SHADER: "vertex",
                GL_FRAGMENT_SHADER: "fragment",
                GL_COMPUTE_SHADER: "compute",
            }.get(shader_type, "unknown")
            glDeleteShader(shader)
            raise RuntimeError(f"Error compiling {shader_type_str} shader: {log.decode()}")

        return shader

    def _link_shader_program(self, shaders):
        """
        Link a set of compiled shaders into a single program.
        """
        shader_program = glCreateProgram()
        for shader in shaders:
            glAttachShader(shader_program, shader)

        glLinkProgram(shader_program)

        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            log = glGetProgramInfoLog(shader_program)
            glDeleteProgram(shader_program)
            raise RuntimeError(f"Error linking shader program: {log.decode()}")

        return shader_program
