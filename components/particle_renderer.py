import time

import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ParticleRenderer(AbstractRenderer):
    def __init__(self, max_particles=1000, particle_batch_size=1000, particle_render_mode='transform_feedback',
                 particle_generator=False,
                 **kwargs):
        super().__init__(**kwargs)
        self.max_particles = max_particles
        self.total_particles = self.max_particles  # Always process all particles
        self.particle_batch_size = min(particle_batch_size, max_particles)
        self.particle_render_mode = particle_render_mode
        self.particle_generator = particle_generator  # Control generator mode
        self.generated_particles = 0  # Track total generated particles

        self.stride_size = 10  # Number of floats per particle (position, velocity, spawn time, lifetime, ID, lifetimePercentage)

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

        self.free_slots = list(range(self.max_particles))  # All slots are initially free

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
            # Add lifetimePercentage to the list of variables to capture
            varyings = ["tfPosition", "tfVelocity", "tfSpawnTime", "tfParticleLifetime", "tfParticleID",
                        "tfLifetimePercentage"]
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
        self.particle_positions = np.random.uniform(-self.width, self.width, (self.particle_batch_size, 3)).astype(
            np.float32)
        self.particle_positions[:, 1] = np.random.uniform(0.0, self.height,
                                                          self.particle_batch_size)  # Y-axis controls height
        self.particle_velocities = np.random.uniform(-0.5, 0.5, (self.particle_batch_size, 3)).astype(np.float32)

    def create_transform_feedback_buffers(self):
        glUseProgram(self.shader_program)
        particle_vertices = self.generate_initial_data()

        self.vao, self.vbo, self.feedback_vbo = glGenVertexArrays(1), glGenBuffers(1), glGenBuffers(1)
        glBindVertexArray(self.vao)

        buffer_size = self.max_particles * self.stride_size * 4  # Allocate enough space for max particles

        # Initialize the VBO with the initial particle data
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, buffer_size, particle_vertices, GL_DYNAMIC_DRAW)

        # Initialize the feedback VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.feedback_vbo)
        glBufferData(GL_ARRAY_BUFFER, buffer_size, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        self._setup_vertex_attributes()

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
        # Ensure we don't generate more particles than max_particles
        self.particle_batch_size = min(self.particle_batch_size, self.max_particles)

        current_time = time.time()
        particle_positions = np.random.uniform(-self.width, self.width, (self.particle_batch_size, 3)).astype(
            np.float32)
        particle_positions[:, 1] = np.random.uniform(-self.height, self.height, self.particle_batch_size)
        particle_positions[:, 2] = np.random.uniform(-self.depth, self.depth, self.particle_batch_size)

        particle_velocities = np.random.uniform(-0.5, 0.5, (self.particle_batch_size, 3)).astype(np.float32)

        if self.particle_spawn_time_jitter:
            jitter_values = np.random.uniform(0, self.particle_max_spawn_time_jitter,
                                              (self.particle_batch_size, 1)).astype(np.float32)
            spawn_times = np.full((self.particle_batch_size, 1), current_time - self.start_time,
                                  dtype=np.float32) + jitter_values
        else:
            spawn_times = np.full((self.particle_batch_size, 1), current_time - self.start_time, dtype=np.float32)

        if self.particle_max_lifetime > 0.0:
            lifetimes = np.random.uniform(0.1, self.particle_max_lifetime, (self.particle_batch_size, 1)).astype(
                np.float32)
        else:
            lifetimes = np.full((self.particle_batch_size, 1), 0.0, dtype=np.float32)

        particle_ids = np.arange(self.generated_particles, self.generated_particles + self.particle_batch_size,
                                 dtype=np.float32).reshape(-1, 1)
        lifetime_percentages = np.zeros((self.particle_batch_size, 1), dtype=np.float32)

        data = np.hstack((particle_positions, particle_velocities, spawn_times, lifetimes, particle_ids,
                          lifetime_percentages)).astype(np.float32)
        return data

    def _setup_vertex_attributes(self):
        """
        Setup vertex attribute pointers for position, velocity, spawn time, lifetime, and particle ID.
        Ensures that the shader program has the correct attribute locations configured.
        """
        float_size = 4  # Size of a float in bytes
        vertex_stride = self.stride_size * float_size

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

        if self.debug_mode:
            self._check_vertex_attrib_pointer_setup()

    def _check_vertex_attrib_pointer_setup(self):
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

    def update_particles(self):
        """
        Update particle data based on the selected render mode.
        Dispatches the appropriate particle update mechanism based on the render mode.
        """
        glUseProgram(self.shader_program)
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        delta_time = min(elapsed_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = elapsed_time

        # Pass the elapsed time (relative to start) to the shader
        glUniform1f(glGetUniformLocation(self.shader_program, "currentTime"), np.float32(elapsed_time))
        glUniform1f(glGetUniformLocation(self.shader_program, "deltaTime"), delta_time)

        # Update particles based on the selected mode
        if self.particle_render_mode == 'compute_shader':
            self._update_particles_compute_shader()
        elif self.particle_render_mode == 'transform_feedback':
            self._update_particles_transform_feedback()
        elif self.particle_render_mode == 'cpu':
            self._update_particles_cpu()

        if self.particle_generator:
            self._remove_expired_particles()  # Update free slots before generating new particles
            self._generate_new_particles()

        if self.debug_mode:
            # Calculate and print the number of active particles
            num_active_particles = self.max_particles - len(self.free_slots)
            print(f"Number of active particles: {num_active_particles}")

    def _remove_expired_particles(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.feedback_vbo)
        buffer_size = self.max_particles * self.stride_size * 4  # Total buffer size in bytes
        particle_data = glGetBufferSubData(GL_ARRAY_BUFFER, 0, buffer_size)
        particle_data_np = np.frombuffer(particle_data, dtype=np.float32).reshape(-1, self.stride_size)
        # Extract lifetimePercentage column
        lifetime_percentages = particle_data_np[:, 9]
        # Find indices of expired particles
        expired_indices = np.where(lifetime_percentages >= 1.0)[0]
        # Add expired indices to free_slots, avoid duplicates
        for idx in expired_indices:
            if idx not in self.free_slots:
                self.free_slots.append(idx)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _generate_new_particles(self):
        # Calculate how many new particles we can generate
        num_free_slots = len(self.free_slots)
        if num_free_slots <= 0:
            return  # No free slots available

        num_gen_particles = min(num_free_slots, self.particle_batch_size)

        current_time = time.time()

        # Generate new particles
        gen_positions = np.random.uniform(-self.width, self.width, (num_gen_particles, 3)).astype(np.float32)
        gen_positions[:, 1] = np.random.uniform(-self.height, self.height, num_gen_particles)
        gen_positions[:, 2] = np.random.uniform(-self.depth, self.depth, num_gen_particles)
        gen_velocities = np.random.uniform(-0.5, 0.5, (num_gen_particles, 3)).astype(np.float32)

        if self.particle_spawn_time_jitter:
            jitter_values = np.random.uniform(0, self.particle_max_spawn_time_jitter,
                                              (num_gen_particles, 1)).astype(np.float32)
            gen_spawn_times = np.full((num_gen_particles, 1), current_time - self.start_time,
                                      dtype=np.float32) + jitter_values
        else:
            gen_spawn_times = np.full((num_gen_particles, 1), current_time - self.start_time, dtype=np.float32)

        if self.particle_max_lifetime > 0.0:
            gen_lifetimes = np.random.uniform(0.1, self.particle_max_lifetime, (num_gen_particles, 1)).astype(
                np.float32)
        else:
            gen_lifetimes = np.full((num_gen_particles, 1), 0.0, dtype=np.float32)

        gen_ids = np.arange(self.generated_particles, self.generated_particles + num_gen_particles,
                            dtype=np.float32).reshape(-1, 1)
        gen_lifetime_percentages = np.zeros((num_gen_particles, 1), dtype=np.float32)

        new_particles = np.hstack((
            gen_positions, gen_velocities, gen_spawn_times,
            gen_lifetimes, gen_ids, gen_lifetime_percentages
        )).astype(np.float32)

        # Write new particles into the buffer at the positions of free slots
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        float_size = 4
        particle_stride = self.stride_size * float_size

        for i in range(num_gen_particles):
            slot_index = self.free_slots.pop(0)
            offset = slot_index * particle_stride
            particle_data = new_particles[i]
            glBufferSubData(GL_ARRAY_BUFFER, offset, particle_data.nbytes, particle_data)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Update particle counts
        self.generated_particles += num_gen_particles

    def _update_particles_cpu(self):
        """
        Update particles on the CPU.
        This method performs the simulation entirely on the CPU and uploads the updated data to the GPU.
        """
        current_time = time.time()
        delta_time = min(current_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = current_time

        for i in range(self.particle_batch_size):
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
        glDispatchCompute(self.particle_batch_size // 128 + 1, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

    def _update_particles_transform_feedback(self):
        glBindVertexArray(self.vao)

        # Enable rasterizer discard to avoid rendering particles to the screen
        glEnable(GL_RASTERIZER_DISCARD)

        # Bind the feedback VBO to capture transform feedback output
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, self.feedback_vbo)

        # Start capturing transform feedback
        glBeginTransformFeedback(GL_POINTS)
        glDrawArrays(GL_POINTS, 0, self.total_particles)  # Process all particles
        glEndTransformFeedback()

        # Disable rasterizer discard
        glDisable(GL_RASTERIZER_DISCARD)

        # Ensure that the buffer is synchronized before the next frame
        glMemoryBarrier(GL_TRANSFORM_FEEDBACK_BARRIER_BIT)

        # Swap the VBOs (this swaps the input and feedback buffers for the next frame)
        self.vbo, self.feedback_vbo = self.feedback_vbo, self.vbo

    @common_funcs
    def render(self):
        self.set_view_projection_matrices()
        self.update_particles()
        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, self.total_particles)  # Draw all particles
        glBindVertexArray(0)
