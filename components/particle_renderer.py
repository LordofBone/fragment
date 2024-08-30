import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ParticleRenderer(AbstractRenderer):
    def __init__(self, particle_count=1000, render_mode='transform_feedback', compute_shader_program=None, **kwargs):
        super().__init__(**kwargs)
        self.particle_count = particle_count
        self.render_mode = render_mode
        self.vao = None
        self.vbo = None
        self.feedback_vbo = None
        self.ssbo = None
        self.compute_shader_program = compute_shader_program
        self.init_render_mode()

    def init_render_mode(self):
        """Initialize the buffers and settings based on the selected render mode."""
        if self.render_mode == 'transform_feedback':
            self.create_transform_feedback_buffers()
        elif self.render_mode == 'compute_shader':
            self.create_compute_shader_buffers()
        elif self.render_mode == 'standard':
            self.create_buffers()
        else:
            raise ValueError(f"Unknown render mode: {self.render_mode}")

    def create_transform_feedback_buffers(self):
        """Setup buffers for transform feedback-based particle rendering."""
        vertices = self.generate_initial_data()

        # Create and bind VAO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        # Create and bind VBO for initial particle data
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)

        # Create a second VBO for transform feedback
        self.feedback_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.feedback_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, None, GL_DYNAMIC_DRAW)

        # Setup vertex attributes
        self._setup_vertex_attributes()

    def create_compute_shader_buffers(self):
        """Setup buffers for compute shader-based particle rendering."""
        particles = self.generate_initial_data()

        # Create Shader Storage Buffer Object (SSBO)
        self.ssbo = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
        glBufferData(GL_SHADER_STORAGE_BUFFER, particles.nbytes, particles, GL_DYNAMIC_COPY)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

    def create_buffers(self):
        """Setup buffers for standard vertex/fragment shader-based particle rendering."""
        vertices = self.generate_initial_data()

        # Create and bind VAO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        # Create and bind VBO
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        # Setup vertex attributes
        self._setup_vertex_attributes()

    def generate_initial_data(self):
        """Generate initial positions and velocities for particles."""
        data = []
        for _ in range(self.particle_count):
            position = np.random.uniform(-1.0, 1.0, 3)
            velocity = np.random.uniform(-0.5, 0.5, 3)
            data.extend(position)
            data.extend(velocity)
        return np.array(data, dtype=np.float32)

    def _setup_vertex_attributes(self):
        """Setup vertex attribute pointers."""
        float_size = 4
        vertex_stride = 6 * float_size

        position_loc = glGetAttribLocation(self.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_program, "velocity")

        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        glEnableVertexAttribArray(velocity_loc)
        glVertexAttribPointer(velocity_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def update_particles(self):
        """Update particle data based on the render mode."""
        if self.render_mode == 'compute_shader':
            self._update_particles_compute_shader()
        elif self.render_mode == 'transform_feedback':
            self._update_particles_transform_feedback()

    def _update_particles_compute_shader(self):
        """Update particles using compute shader."""
        glUseProgram(self.compute_shader_program)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)

        # Dispatch compute shader
        work_groups = (self.particle_count // 128 + 1, 1, 1)  # Example work group size
        glDispatchCompute(*work_groups)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

    def _update_particles_transform_feedback(self):
        """Update particles using transform feedback."""
        glBindVertexArray(self.vao)
        glEnable(GL_RASTERIZER_DISCARD)
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, self.feedback_vbo)

        glBeginTransformFeedback(GL_POINTS)
        glDrawArrays(GL_POINTS, 0, self.particle_count)
        glEndTransformFeedback()

        glDisable(GL_RASTERIZER_DISCARD)
        self.vbo, self.feedback_vbo = self.feedback_vbo, self.vbo

    @common_funcs
    def render(self):
        """Render particles."""
        self.update_particles()

        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, self.particle_count)
        glBindVertexArray(0)
