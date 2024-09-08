import time

import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ParticleRenderer(AbstractRenderer):
    def __init__(self, particle_count=1000, particle_render_mode='transform_feedback', **kwargs):
        super().__init__(**kwargs)
        self.particle_count = particle_count
        self.particle_render_mode = particle_render_mode
        self.vao = None
        self.vbo = None
        self.feedback_vbo = None
        self.ssbo = None
        self.particle_size = self.dynamic_attrs.get('particle_size', 2.0)  # Default particle size
        self.height = self.dynamic_attrs.get('height', 1.0)  # Default height for the particle field
        self.width = self.dynamic_attrs.get('width', 1.0)  # Default width for the particle field
        self.depth = self.dynamic_attrs.get('depth', 1.0)  # Default depth for the particle field
        self.start_time = time.time()  # Store the start time (epoch)
        self.last_time = time.time()  # Store the last frame time for delta time calculations

        # Only used in CPU mode
        self.particle_positions = None
        self.particle_velocities = None
        self.particle_gravity = np.array(self.dynamic_attrs.get('particle_gravity', (0.0, -9.81, 0.0)),
                                         dtype=np.float32)
        self.particle_bounce_factor = self.dynamic_attrs.get('particle_bounce_factor', 0.6)
        self.particle_ground_plane_normal = np.array(
            self.dynamic_attrs.get('particle_ground_plane_normal', (0.0, 1.0, 0.0)),
            dtype=np.float32)
        self.particle_ground_plane_height = self.dynamic_attrs.get('particle_ground_plane_height', 0.0)
        self.particle_max_velocity = self.dynamic_attrs.get('particle_max_velocity', 10.0)
        self.particle_max_lifetime = self.dynamic_attrs.get('particle_max_lifetime', 5.0)
        self.particle_spawn_time_jitter = self.dynamic_attrs.get('particle_spawn_time_jitter', False)
        self.particle_max_spawn_time_jitter = self.dynamic_attrs.get('particle_max_spawn_time_jitter', 5.0)

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
        if self.particle_render_mode == 'transform_feedback':
            # Specify the variables to capture during transform feedback
            varyings = ["tfPosition", "tfVelocity", "tfSpawnTime", "tfParticleLifetime", "tfParticleID"]
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
        if self.particle_render_mode == 'transform_feedback':
            self.create_transform_feedback_buffers()
        elif self.particle_render_mode == 'compute_shader':
            self.create_compute_shader_buffers()
        elif self.particle_render_mode == 'cpu':
            self.init_cpu_mode()
            self.create_buffers()
        else:
            raise ValueError(f"Unknown render mode: {self.particle_render_mode}")

    def set_view_projection_matrices(self):
        """
        Send the view and projection matrices to the shader.
        """
        self.setup_camera()

        # Get the uniform locations for the view and projection matrices
        view_location = glGetUniformLocation(self.shader_program, "view")
        projection_location = glGetUniformLocation(self.shader_program, "projection")
        camera_position_location = glGetUniformLocation(self.shader_program, "cameraPosition")
        model_matrix_location = glGetUniformLocation(self.shader_program, "model")

        # Pass the view and projection matrices to the shader
        glUniformMatrix4fv(view_location, 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(projection_location, 1, GL_FALSE, glm.value_ptr(self.projection))
        glUniform3fv(camera_position_location, 1, glm.value_ptr(self.camera_position))

        # Pass the model matrix (which includes scaling, rotating, translating)
        glUniformMatrix4fv(model_matrix_location, 1, GL_FALSE, glm.value_ptr(self.model_matrix))

    def init_cpu_mode(self):
        """
        Initialize the CPU mode by setting up the initial particle positions and velocities.
        """
        self.particle_positions = np.random.uniform(-self.width, self.width, (self.particle_count, 3)).astype(
            np.float32)
        self.particle_positions[:, 1] = np.random.uniform(0.0, self.height,
                                                          self.particle_count)  # Y-axis controls height
        self.particle_velocities = np.random.uniform(-0.5, 0.5, (self.particle_count, 3)).astype(np.float32)

    def create_transform_feedback_buffers(self):
        """
        Setup buffers for transform feedback-based particle rendering.
        This method sets up the Vertex Array Object (VAO) and Vertex Buffer Objects (VBOs)
        needed for capturing particle updates via transform feedback.
        """
        glUseProgram(self.shader_program)
        particle_vertices = self.generate_initial_data()  # Generates initial positions and velocities

        self.vao, self.vbo, self.feedback_vbo = glGenVertexArrays(1), glGenBuffers(1), glGenBuffers(1)

        glBindVertexArray(self.vao)

        # Bind and upload the vertex data (positions and velocities)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, particle_vertices.nbytes, particle_vertices, GL_DYNAMIC_DRAW)

        # Bind and allocate space for the feedback VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.feedback_vbo)
        glBufferData(GL_ARRAY_BUFFER, particle_vertices.nbytes, None, GL_DYNAMIC_DRAW)

        # Bind the original VBO again to set up attributes
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)

        # Set up vertex attribute pointers
        self._setup_vertex_attributes()

        # Debug: Check attribute pointer setup
        if self.debug_mode:
            self._check_vertex_attrib_pointer_setup(particle_vertices)

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

    def generate_initial_data(self):
        """
        Generate initial positions, velocities, spawn times, lifetimes, and particle IDs for particles.
        Returns an array of interleaved position, velocity, spawn time, lifetime, and particle ID data.
        """
        current_time = time.time()  # Get the current time to set as spawn time

        # Generate particle positions (3D)
        particle_positions = np.random.uniform(-self.width, self.width, (self.particle_count, 3)).astype(np.float32)
        particle_positions[:, 1] = np.random.uniform(-self.height, self.height, self.particle_count)  # Y-axis
        particle_positions[:, 2] = np.random.uniform(-self.depth, self.depth, self.particle_count)  # Z-axis

        # Generate particle velocities (3D)
        particle_velocities = np.random.uniform(-0.5, 0.5, (self.particle_count, 3)).astype(np.float32)

        # Generate particle spawn times (1D) with random jitter per particle if enabled
        if self.particle_spawn_time_jitter:
            jitter_values = np.random.uniform(0, self.particle_max_spawn_time_jitter, (self.particle_count, 1)).astype(
                np.float32)
            spawn_times = np.full((self.particle_count, 1), current_time - self.start_time,
                                  dtype=np.float32) + jitter_values
        else:
            spawn_times = np.full((self.particle_count, 1), current_time - self.start_time, dtype=np.float32)

        # Generate lifetimes (1D)
        if self.particle_max_lifetime > 0.0:
            lifetimes = np.random.uniform(0.1, self.particle_max_lifetime, (self.particle_count, 1)).astype(np.float32)
        else:
            lifetimes = np.full((self.particle_count, 1), 0.0, dtype=np.float32)

        # Generate particle IDs (1D)
        particle_ids = np.arange(self.particle_count, dtype=np.float32).reshape(-1, 1)

        # Interleave positions, velocities, spawn times, lifetimes, and particle IDs into a single array
        data = np.hstack((particle_positions, particle_velocities, spawn_times, lifetimes, particle_ids)).astype(
            np.float32)

        return data

    def _setup_vertex_attributes(self):
        """
        Setup vertex attribute pointers for position, velocity, spawn time, lifetime, and particle ID.
        Ensures that the shader program has the correct attribute locations configured.
        """
        float_size = 4  # Size of a float in bytes
        vertex_stride = 9 * float_size  # 3 floats for position + 3 floats for velocity + 1 float for spawn time + 1 float for lifetime + 1 float for particle ID

        # Get the attribute locations
        position_loc = glGetAttribLocation(self.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_program, "particleID")

        # Ensure all attributes are found
        if position_loc == -1 or velocity_loc == -1 or spawn_time_loc == -1 or lifetime_loc == -1 or particle_id_loc == -1:
            raise RuntimeError(
                "Position, Velocity, Spawn Time, Lifetime, or Particle ID attribute not found in shader program.")

        # Enable and set the vertex attribute arrays for position, velocity, spawn time, lifetime, and particle ID
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        glEnableVertexAttribArray(velocity_loc)
        glVertexAttribPointer(velocity_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(3 * float_size))

        glEnableVertexAttribArray(spawn_time_loc)
        glVertexAttribPointer(spawn_time_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(6 * float_size))

        glEnableVertexAttribArray(lifetime_loc)
        glVertexAttribPointer(lifetime_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(7 * float_size))

        glEnableVertexAttribArray(particle_id_loc)
        glVertexAttribPointer(particle_id_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(8 * float_size))

    def _check_vertex_attrib_pointer_setup(self, vertices):
        """
        Debug function to check vertex attribute pointer setup.
        """
        position_loc = glGetAttribLocation(self.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_program, "particleID")

        # Stride and offset values
        position_stride = glGetVertexAttribiv(position_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        velocity_stride = glGetVertexAttribiv(velocity_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        spawn_time_stride = glGetVertexAttribiv(spawn_time_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        lifetime_stride = glGetVertexAttribiv(lifetime_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        particle_id_stride = glGetVertexAttribiv(particle_id_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)

        position_offset = glGetVertexAttribPointerv(position_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        velocity_offset = glGetVertexAttribPointerv(velocity_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        spawn_time_offset = glGetVertexAttribPointerv(spawn_time_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        lifetime_offset = glGetVertexAttribPointerv(lifetime_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        particle_id_offset = glGetVertexAttribPointerv(particle_id_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)

        print(f"Position Attributes in _check_vertex_attrib_pointer_setup")
        print(f"Position Attribute: Location = {position_loc}, Stride = {position_stride}, Offset = {position_offset}")
        print(f"Velocity Attribute: Location = {velocity_loc}, Stride = {velocity_stride}, Offset = {velocity_offset}")
        print(
            f"Spawn Time Attribute: Location = {spawn_time_loc}, Stride = {spawn_time_stride}, Offset = {spawn_time_offset}")
        print(f"Lifetime Attribute: Location = {lifetime_loc}, Stride = {lifetime_stride}, Offset = {lifetime_offset}")
        print(
            f"Particle ID Attribute: Location = {particle_id_loc}, Stride = {particle_id_stride}, Offset = {particle_id_offset}")

        # Optionally, read back the entire buffer data to verify
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        mapped_buffer = glMapBuffer(GL_ARRAY_BUFFER, GL_READ_ONLY)
        if mapped_buffer:
            # Calculate the size of the buffer in bytes
            buffer_size = vertices.nbytes
            # Create a ctypes array from the mapped buffer pointer
            ctypes_array = (ctypes.c_byte * buffer_size).from_address(mapped_buffer)
            # Convert ctypes array to bytes and then to a numpy array
            buffer_data = np.frombuffer(ctypes_array, dtype=vertices.dtype)
            print(f"Buffer Data Readback (first 5 vertices): {buffer_data[:9].reshape(-1, vertices.shape[1])}")
            glUnmapBuffer(GL_ARRAY_BUFFER)
        else:
            print("Failed to map buffer for reading.")

    def update_particles(self):
        """
        Update particle data based on the selected render mode.
        Dispatches the appropriate particle update mechanism based on the render mode.
        """
        current_time = time.time()  # Current Unix time
        elapsed_time = current_time - self.start_time  # Time elapsed since the system started
        delta_time = min(elapsed_time - self.last_time, 0.016)  # Clamp delta time to ~60 FPS
        self.last_time = elapsed_time

        # Pass the elapsed time (relative to start) to the shader
        glUniform1f(glGetUniformLocation(self.shader_program, "currentTime"), np.float32(elapsed_time))
        glUniform1f(glGetUniformLocation(self.shader_program, "deltaTime"), delta_time)

        if self.particle_render_mode == 'compute_shader':
            self._update_particles_compute_shader()
        elif self.particle_render_mode == 'transform_feedback':
            self._update_particles_transform_feedback()
        elif self.particle_render_mode == 'cpu':
            self._update_particles_cpu()

    def _update_particles_cpu(self):
        """
        Update particles on the CPU.
        This method performs the simulation entirely on the CPU and uploads the updated data to the GPU.
        """
        current_time = time.time()
        delta_time = min(current_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = current_time

        for i in range(self.particle_count):
            # Update velocity with gravity
            self.particle_velocities[i] += self.particle_gravity * delta_time

            # Clamp the velocity to the maximum allowed value
            speed = np.linalg.norm(self.particle_velocities[i])
            if speed > self.particle_max_velocity:
                self.particle_velocities[i] = self.particle_velocities[i] / speed * self.particle_max_velocity

            # Update position
            self.particle_positions[i] += self.particle_velocities[i] * delta_time

            # Check for collision with the ground plane
            distance_to_ground = np.dot(self.particle_positions[i],
                                        self.particle_ground_plane_normal) - self.particle_ground_plane_height
            if distance_to_ground < 0.0:
                self.particle_velocities[i] = np.reflect(self.particle_velocities[i],
                                                         self.particle_ground_plane_normal) * self.particle_bounce_factor
                self.particle_positions[i] -= self.particle_ground_plane_normal * distance_to_ground

        # Upload updated positions and velocities to the GPU
        particle_data = np.hstack((self.particle_positions, self.particle_velocities)).astype(np.float32)
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

        # Enable rasterizer discard to avoid rendering particles to the screen
        glEnable(GL_RASTERIZER_DISCARD)

        # Bind the feedback VBO to capture transform feedback output
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, self.feedback_vbo)

        # Start capturing transform feedback
        glBeginTransformFeedback(GL_POINTS)
        glDrawArrays(GL_POINTS, 0, self.particle_count)
        glEndTransformFeedback()

        # Disable rasterizer discard
        glDisable(GL_RASTERIZER_DISCARD)

        # Ensure that the buffer is synchronized before the next frame
        glMemoryBarrier(GL_TRANSFORM_FEEDBACK_BARRIER_BIT)

        # Swap the VBOs (this swaps the input and feedback buffers for the next frame)
        self.vbo, self.feedback_vbo = self.feedback_vbo, self.vbo

    @common_funcs
    def render(self):
        """
        Render particles.
        This method binds the VAO and issues a draw call to render the particles as points.
        """
        self.set_view_projection_matrices()
        self.update_particles()
        glBindVertexArray(self.vao)

        # Issue the draw call
        glDrawArrays(GL_POINTS, 0, self.particle_count)

        glBindVertexArray(0)
