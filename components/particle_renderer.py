import time

import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ParticleRenderer(AbstractRenderer):
    def __init__(self, particle_count=1000, render_mode='transform_feedback', **kwargs):
        super().__init__(**kwargs)
        self.particle_count = particle_count
        self.render_mode = render_mode
        self.vao = None
        self.vbo = None
        self.feedback_vbo = None
        self.ssbo = None
        self.particle_size = self.dynamic_attrs.get('particle_size', 2.0)  # Default particle size
        self.height = self.dynamic_attrs.get('height', 1.0)  # Default height for the particle field
        self.width = self.dynamic_attrs.get('width', 1.0)  # Default width for the particle field
        self.last_time = time.time()  # Store the last frame time for delta time calculations

        # Only used in CPU mode
        self.positions = None
        self.velocities = None
        self.gravity = np.array(self.dynamic_attrs.get('gravity', (0.0, -9.81, 0.0)), dtype=np.float32)
        self.bounce_factor = self.dynamic_attrs.get('bounce_factor', 0.6)
        self.ground_plane_normal = np.array(self.dynamic_attrs.get('ground_plane_normal', (0.0, 1.0, 0.0)),
                                            dtype=np.float32)
        self.ground_plane_height = self.dynamic_attrs.get('ground_plane_height', 0.0)
        self.max_velocity = self.dynamic_attrs.get('max_velocity', 10.0)

    def setup(self):
        """
        Setup the particle renderer by initializing shaders and rendering mode.
        Enables point size control from the shader.
        """
        self.init_shaders()
        self.init_render_mode()
        glEnable(GL_PROGRAM_POINT_SIZE)  # Enable point size control from the shader

    def init_shaders(self):
        """
        Initialize shaders for the renderer.
        Handles shader linking and setup for transform feedback if that mode is enabled.
        """
        super().init_shaders()
        if self.render_mode == 'transform_feedback':
            # Specify the variables to capture during transform feedback
            varyings = ["tf_position", "tf_velocity"]
            varyings_c = (ctypes.POINTER(ctypes.c_char) * len(varyings))(
                *[ctypes.create_string_buffer(v.encode('utf-8')) for v in varyings])
            glTransformFeedbackVaryings(self.shader_program, len(varyings), varyings_c, GL_INTERLEAVED_ATTRIBS)
            glLinkProgram(self.shader_program)

            # Check for successful shader program linking
            if not glGetProgramiv(self.shader_program, GL_LINK_STATUS):
                log = glGetProgramInfoLog(self.shader_program)
                raise RuntimeError(f"Shader program linking failed: {log.decode()}")

    def init_render_mode(self):
        """
        Initialize the buffers and settings based on the selected render mode.
        Chooses between transform feedback, compute shader, and CPU-based rendering modes.
        """
        if self.render_mode == 'transform_feedback':
            self.create_transform_feedback_buffers()
        elif self.render_mode == 'compute_shader':
            self.create_compute_shader_buffers()
        elif self.render_mode == 'cpu':
            self.init_cpu_mode()
            self.create_buffers()
        else:
            raise ValueError(f"Unknown render mode: {self.render_mode}")

    def init_cpu_mode(self):
        """
        Initialize the CPU mode by setting up the initial particle positions and velocities.
        """
        self.positions = np.random.uniform(-self.width, self.width, (self.particle_count, 3)).astype(np.float32)
        self.positions[:, 1] = np.random.uniform(0.0, self.height, self.particle_count)  # Y-axis controls height
        self.velocities = np.random.uniform(-0.5, 0.5, (self.particle_count, 3)).astype(np.float32)

    def create_transform_feedback_buffers(self):
        """
        Setup buffers for transform feedback-based particle rendering.
        This method sets up the Vertex Array Object (VAO) and Vertex Buffer Objects (VBOs)
        needed for capturing particle updates via transform feedback.
        """
        vertices = self.generate_initial_data()
        self.vao, self.vbo, self.feedback_vbo = glGenVertexArrays(1), glGenBuffers(1), glGenBuffers(1)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self.feedback_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, None, GL_DYNAMIC_DRAW)
        self._setup_vertex_attributes()
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, self.feedback_vbo)
        glBindVertexArray(0)

    def create_compute_shader_buffers(self):
        """
        Setup buffers for compute shader-based particle rendering.
        This method creates a Shader Storage Buffer Object (SSBO) for storing particle data
        and binding it to the appropriate buffer base.
        """
        particles = self.generate_initial_data()
        self.ssbo = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
        glBufferData(GL_SHADER_STORAGE_BUFFER, particles.nbytes, particles, GL_DYNAMIC_COPY)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

    def create_buffers(self):
        """
        Setup buffers for vertex/fragment shader-based particle rendering.
        This method sets up the VAO and VBO needed for rendering particles using a shader pipeline.
        """
        vertices = self.generate_initial_data()
        self.vao, self.vbo = glGenVertexArrays(1), glGenBuffers(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
        self._setup_vertex_attributes()
        glBindVertexArray(0)

    def generate_initial_data(self):
        """
        Generate initial positions and velocities for particles.
        Returns an array of interleaved position and velocity data.
        """
        positions = np.random.uniform(-self.width, self.width, (self.particle_count, 3)).astype(np.float32)
        positions[:, 1] = np.random.uniform(0.0, self.height, self.particle_count)  # Y-axis controls height
        velocities = np.random.uniform(-0.5, 0.5, (self.particle_count, 3)).astype(np.float32)
        data = np.hstack((positions, velocities)).astype(np.float32)
        return data

    def _setup_vertex_attributes(self):
        """
        Setup vertex attribute pointers for position and velocity.
        Ensures that the shader program has the correct attribute locations configured.
        """
        float_size = 4
        vertex_stride = 6 * float_size
        position_loc, velocity_loc = glGetAttribLocation(self.shader_program, "position"), glGetAttribLocation(
            self.shader_program, "velocity")

        if position_loc == -1 or velocity_loc == -1:
            raise RuntimeError("Position or Velocity attribute not found in shader program.")

        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(velocity_loc)
        glVertexAttribPointer(velocity_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def update_particles(self):
        """
        Update particle data based on the selected render mode.
        Dispatches the appropriate particle update mechanism based on the render mode.
        """
        if self.render_mode == 'compute_shader':
            self._update_particles_compute_shader()
        elif self.render_mode == 'transform_feedback':
            self._update_particles_transform_feedback()
        elif self.render_mode == 'cpu':
            self._update_particles_cpu()

    def _update_particles_cpu(self):
        """
        Update particles on the CPU.
        This method performs the simulation entirely on the CPU and uploads the updated data to the GPU.
        """
        current_time = time.time()
        delta_time = current_time - self.last_time
        self.last_time = current_time

        for i in range(self.particle_count):
            # Update velocity with gravity
            self.velocities[i] += self.gravity * delta_time

            # Clamp the velocity to the maximum allowed value
            speed = np.linalg.norm(self.velocities[i])
            if speed > self.max_velocity:
                self.velocities[i] = self.velocities[i] / speed * self.max_velocity

            # Update position
            self.positions[i] += self.velocities[i] * delta_time

            # Check for collision with the ground plane
            distance_to_ground = np.dot(self.positions[i], self.ground_plane_normal) - self.ground_plane_height
            if distance_to_ground < 0.0:
                self.velocities[i] = np.reflect(self.velocities[i], self.ground_plane_normal) * self.bounce_factor
                self.positions[i] -= self.ground_plane_normal * distance_to_ground

        # Upload updated positions and velocities to the GPU
        particle_data = np.hstack((self.positions, self.velocities)).astype(np.float32)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, particle_data.nbytes, particle_data)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _update_particles_compute_shader(self):
        """
        Update particles using a compute shader.
        Dispatches the compute shader and ensures memory barriers are respected.
        """
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
        glDispatchCompute(self.particle_count // 128 + 1, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

    def _update_particles_transform_feedback(self):
        """
        Update particles using transform feedback.
        Captures the output of the vertex shader back into a buffer and swaps the buffers for the next frame.
        """
        glBindVertexArray(self.vao)
        glEnable(GL_RASTERIZER_DISCARD)
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, self.feedback_vbo)
        glBeginTransformFeedback(GL_POINTS)
        glDrawArrays(GL_POINTS, 0, self.particle_count)
        glEndTransformFeedback()
        glDisable(GL_RASTERIZER_DISCARD)

        # Ensure buffer data is synchronized before the next draw call
        glMemoryBarrier(GL_TRANSFORM_FEEDBACK_BARRIER_BIT)

        # Swap the VBOs for the next iteration
        self.vbo, self.feedback_vbo = self.feedback_vbo, self.vbo

    @common_funcs
    def render(self):
        """
        Render particles.
        This method binds the VAO and issues a draw call to render the particles as points.
        """
        self.update_particles()
        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, self.particle_count)
        glBindVertexArray(0)
