import time

import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ParticleRenderer(AbstractRenderer):
    def __init__(self, particles_max=100, particle_batch_size=1, particle_render_mode='transform_feedback',
                 particle_generator=False, generator_delay=0.0, particle_type='point',
                 **kwargs):
        super().__init__(**kwargs)
        self.max_particles = particles_max
        self.total_particles = self.max_particles  # Always process all particles
        self.particle_batch_size = min(particle_batch_size, particles_max)
        self.particle_render_mode = particle_render_mode
        self.particle_generator = particle_generator  # Control generator mode
        self.generator_delay = generator_delay  # Delay between particle generations in seconds
        self.generated_particles = 0  # Track total generated particles
        self.last_generation_time = time.time()  # Track the last time particles were generated
        self.particle_type = particle_type  # New parameter to control the primitive type

        self.float_size = 4  # Size of a float in bytes
        self.stride_size = 10  # Number of floats per particle (position, velocity, spawn time, lifetime, ID, lifetimePercentage)
        self.stride_size_cpu = 5  # Number of floats per particle for CPU mode (position, lifetimePercentage)

        self.vao = None
        self.vbo = None
        self.feedback_vbo = None
        self.ssbo = None
        self.particle_size = self.dynamic_attrs.get('particle_size', 2.0)  # Default particle size
        self.height = self.dynamic_attrs.get('height', 1.0)  # Default height for the particle field
        self.width = self.dynamic_attrs.get('width', 1.0)  # Default width for the particle field
        self.depth = self.dynamic_attrs.get('depth', 1.0)  # Default depth for the particle field
        self.start_time = time.time()  # Store the start time (epoch)
        self.last_time = self.start_time  # Store the last frame time for delta time calculations

        self.particle_ground_plane_height = self.dynamic_attrs.get('particle_ground_plane_height', 0.0)
        self.particle_max_velocity = self.dynamic_attrs.get('particle_max_velocity', 10.0)
        self.particle_max_lifetime = self.dynamic_attrs.get('particle_max_lifetime', 5.0)
        self.particle_spawn_time_jitter = self.dynamic_attrs.get('particle_spawn_time_jitter', False)
        self.particle_max_spawn_time_jitter = self.dynamic_attrs.get('particle_max_spawn_time_jitter', 5.0)

        self.free_slots = list(range(self.max_particles))  # All slots are initially free

        # Only used in CPU mode
        self.cpu_particles = np.zeros((self.max_particles, 10), dtype=np.float32)  # Store particle attributes
        self.particle_color = glm.vec3(*self.dynamic_attrs.get("particle_color", (1.0, 0.5, 0.2)))

        self.particle_positions = None
        self.particle_velocities = None
        self.particle_gravity = np.array(self.dynamic_attrs.get('particle_gravity', (0.0, -9.81, 0.0)),
                                         dtype=np.float32)
        self.particle_bounce_factor = self.dynamic_attrs.get('particle_bounce_factor', 0.6)
        self.particle_ground_plane_normal = np.array(
            self.dynamic_attrs.get('particle_ground_plane_normal', (0.0, 1.0, 0.0)),
            dtype=np.float32)

        self.particle_min_weight = self.dynamic_attrs.get('particle_min_weight', 0.01)
        self.particle_max_weight = self.dynamic_attrs.get('particle_max_weight', 0.1)
        self.fluid_simulation = self.dynamic_attrs.get('fluid_simulation', False)
        self.particle_pressure = self.dynamic_attrs.get('particle_pressure', 1.0)
        self.particle_viscosity = self.dynamic_attrs.get('particle_viscosity', 0.5)

        current_time = time.time()
        self.delta_time = min(current_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = current_time

    def setup(self):
        """
        Setup the particle renderer by initializing shaders and rendering mode.
        Enables point size control from the shader.
        """
        self.init_shaders()
        self.create_buffers()
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

    def create_buffers(self):
        particles = self.generate_initial_data()

        if self.particle_render_mode == 'transform_feedback':
            """
            Setup buffers for transform feedback-based particle rendering.
            This method creates a VAO and VBO for storing particle data and feedback data.
            """
            glUseProgram(self.shader_program)

            self.vao, self.vbo, self.feedback_vbo = glGenVertexArrays(1), glGenBuffers(1), glGenBuffers(1)
            glBindVertexArray(self.vao)

            buffer_size = self.max_particles * self.stride_size * 4  # Allocate enough space for max particles

            # Initialize the VBO with the initial particle data
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            glBufferData(GL_ARRAY_BUFFER, buffer_size, particles, GL_DYNAMIC_DRAW)

            # Initialize the feedback VBO
            glBindBuffer(GL_ARRAY_BUFFER, self.feedback_vbo)
            glBufferData(GL_ARRAY_BUFFER, buffer_size, None, GL_DYNAMIC_DRAW)

            # Set up vertex attribute pointers
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            self._setup_vertex_attributes()
        elif self.particle_render_mode == 'compute_shader':
            """
            Setup buffers for compute shader-based particle rendering.
            This method creates a Shader Storage Buffer Object (SSBO) for storing particle data
            and binding it to the appropriate buffer base.
            """
            # particles = self.generate_initial_data()
            self.ssbo = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
            glBufferData(GL_SHADER_STORAGE_BUFFER, particles.nbytes, particles, GL_DYNAMIC_COPY)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

            # Set up the VAO and VBO for rendering
            self.vao = glGenVertexArrays(1)
            glBindVertexArray(self.vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.ssbo)
            glBindVertexArray(0)
        elif self.particle_render_mode == 'cpu':
            """
            Setup buffers for vertex/fragment shader-based particle rendering using CPU-generated data.
            This method sets up the VAO and VBO needed for rendering particles based on CPU-calculated data.
            """

            glUseProgram(self.shader_program)

            self.cpu_particles = particles

            self.vao, self.vbo = glGenVertexArrays(1), glGenBuffers(1)
            glBindVertexArray(self.vao)

            # Upload the empty data to the GPU, will update this every frame with CPU-calculated values
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            glBufferData(GL_ARRAY_BUFFER, self.cpu_particles.nbytes, self.cpu_particles, GL_DYNAMIC_DRAW)

            self.set_cpu_uniforms()

            # Set up the vertex attributes
            self._setup_vertex_attributes_cpu()

            glBindVertexArray(0)  # Unbind VAO
        else:
            raise ValueError(f"Unknown render mode: {self.particle_render_mode}")

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

        if self.debug_mode:
            print(f"Generated Particle positions: {particle_positions}")
            print(f"Generated Particle velocities: {particle_velocities}")
            print(f"Generated Spawn times: {spawn_times}")
            print(f"Generated Lifetimes: {lifetimes}")
            print(f"Generated Particle IDs: {particle_ids}")
            print(f"Generated Lifetime percentages: {lifetime_percentages}")

        data = np.hstack((particle_positions, particle_velocities, spawn_times, lifetimes, particle_ids,
                          lifetime_percentages)).astype(np.float32)
        return data

    def _setup_vertex_attributes(self):
        """
        Setup vertex attribute pointers for position, velocity, spawn time, lifetime, and particle ID.
        Ensures that the shader program has the correct attribute locations configured.
        """
        float_size = self.float_size  # Size of a float in bytes
        vertex_stride = self.stride_size * float_size

        # Ensure the correct shader program (vertex/fragment) is active
        glUseProgram(self.shader_program)

        # Get the attribute locations
        position_loc = glGetAttribLocation(self.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_program, "particleID")

        # Ensure all attributes are found
        if position_loc == -1 or velocity_loc == -1 or spawn_time_loc == -1 or lifetime_loc == -1 or particle_id_loc == -1:
            # Print attribute locations for debugging
            print(f"position_loc: {position_loc}, velocity_loc: {velocity_loc}, spawn_time_loc: {spawn_time_loc}, "
                  f"lifetime_loc: {lifetime_loc}, particle_id_loc: {particle_id_loc}")
            raise RuntimeError(
                "Position, Velocity, Spawn Time, Lifetime, or Particle ID attribute not found in shader program."
            )

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

    def _setup_vertex_attributes_cpu(self):
        """
        Setup vertex attribute pointers for position and any other required data for rendering particles.
        """
        float_size = self.float_size  # Size of a float in bytes
        vertex_stride = self.stride_size_cpu * float_size  # We only need position data for now (3 floats per vertex)

        # Ensure the correct shader program (vertex/fragment) is active
        glUseProgram(self.shader_program)

        # Get the attribute locations
        position_loc = glGetAttribLocation(self.shader_program, "position")
        lifetime_percentage_loc = glGetAttribLocation(self.shader_program, "lifetimePercentage")
        particle_id_loc = glGetAttribLocation(self.shader_program, "particleID")

        # Ensure position attribute is found
        if position_loc == -1 or lifetime_percentage_loc == -1 or particle_id_loc == -1:
            raise RuntimeError("Position, lifetime percentage or particle ID attribute not found in shader program.")

        # Enable and set the vertex attribute array for position
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        # Enable and set the vertex attribute array for lifetime percentage
        glEnableVertexAttribArray(lifetime_percentage_loc)
        glVertexAttribPointer(lifetime_percentage_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(3 * float_size))

        # Enable and set the vertex attribute array for particle ID
        glEnableVertexAttribArray(particle_id_loc)
        glVertexAttribPointer(particle_id_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(4 * float_size))

        if self.debug_mode:
            print(
                f"Position attribute location: {position_loc}, Lifetime percentage location: {lifetime_percentage_loc}, Lifetime ID location: {particle_id_loc}")

    def set_compute_uniforms(self):
        """
        Set up the uniforms for the compute shader.
        """
        if self.debug_mode:
            print(f"deltaTime: {self.delta_time}")
            print(f"particleGenerator: {int(self.particle_generator)}")
            print(f"generatorDelay: {self.generator_delay}")
            print(f"particleBatchSize: {self.particle_batch_size}")
            print(f"maxParticles: {self.max_particles}")
            print(f"particleMaxLifetime: {self.particle_max_lifetime}")
            print(f"currentTime: {time.time() - self.start_time}")
            print(f"particleGravity: {self.shader_particle_gravity}")
            print(f"particleMaxVelocity: {self.dynamic_attrs.get('particle_max_velocity', 10.0)}")
            print(f"particleBounceFactor: {self.particle_bounce_factor}")
            print(f"particleGroundPlaneNormal: {self.particle_ground_plane_normal}")
            print(f"particleGroundPlaneHeight: {self.particle_ground_plane_height}")
            print(f"particlePressure: {self.dynamic_attrs.get('particle_pressure', 1.0)}")
            print(f"particleViscosity: {self.dynamic_attrs.get('particle_viscosity', 0.5)}")
            print(f"fluidSimulation: {self.dynamic_attrs.get('fluid_simulation', False)}")
            print(f"width: {self.width}")
            print(f"height: {self.height}")
            print(f"depth: {self.depth}")

        # New uniforms for particle batch size, generator, and max particles
        glUniform1i(glGetUniformLocation(self.shader_program, "particleGenerator"),
                    int(self.particle_generator))
        glUniform1i(glGetUniformLocation(self.compute_shader_program, "maxParticles"), self.max_particles)
        glUniform1i(glGetUniformLocation(self.compute_shader_program, "particleBatchSize"), self.particle_batch_size)
        glUniform1i(glGetUniformLocation(self.compute_shader_program, "particleGenerator"),
                    int(self.particle_generator))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "generatorDelay"),
                    np.float32(self.generator_delay))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "particleMaxLifetime"),
                    np.float32(self.particle_max_lifetime))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "deltaTime"), np.float32(self.delta_time))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "currentTime"),
                    np.float32(time.time() - self.start_time))
        glUniform3fv(
            glGetUniformLocation(self.compute_shader_program, "particleGravity"),
            1,
            glm.value_ptr(self.shader_particle_gravity),
        )
        glUniform1f(
            glGetUniformLocation(self.compute_shader_program, "particleMaxVelocity"),
            self.dynamic_attrs.get("particle_max_velocity", 10.0),
        )
        glUniform1f(
            glGetUniformLocation(self.compute_shader_program, "particleBounceFactor"),
            self.dynamic_attrs.get("particle_bounce_factor", 0.6),
        )
        glUniform3fv(
            glGetUniformLocation(self.compute_shader_program, "particleGroundPlaneNormal"),
            1,
            glm.value_ptr(self.shader_particle_ground_plane_normal),
        )
        glUniform1f(
            glGetUniformLocation(self.compute_shader_program, "particleGroundPlaneHeight"),
            self.dynamic_attrs.get("particle_ground_plane_height", 0.0),
        )
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "particlePressure"),
                    self.dynamic_attrs.get("particle_pressure", 1.0))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "particleViscosity"),
                    self.dynamic_attrs.get("particle_viscosity", 0.5))
        glUniform1i(glGetUniformLocation(self.compute_shader_program, "fluidSimulation"),
                    int(self.dynamic_attrs.get("fluid_simulation", 0)))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "width"), np.float32(self.width))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "height"), np.float32(self.height))
        glUniform1f(glGetUniformLocation(self.compute_shader_program, "depth"), np.float32(self.depth))

    def set_cpu_uniforms(self):
        """
        Set up the uniforms for the CPU-based particle rendering.
        """
        glUseProgram(self.shader_program)

        # Set other uniforms like particle size, color, etc.
        glUniform1f(glGetUniformLocation(self.shader_program, "particleSize"), self.particle_size)
        glUniform3fv(glGetUniformLocation(self.shader_program, "particleColor"), 1, glm.value_ptr(self.particle_color))

        if self.debug_mode:
            print(f"Set particle uniforms for CPU mode.")
            print(f"particleSize: {self.particle_size}")
            print(f"particleColor: {self.particle_color}")

    def update_particles(self):
        """
        Update particle data based on the selected render mode.
        Dispatches the appropriate particle update mechanism based on the render mode.
        """
        glUseProgram(self.shader_program)
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        self.delta_time = min(current_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = current_time

        # Pass the elapsed time (relative to start) to the shader
        glUniform1f(glGetUniformLocation(self.shader_program, "currentTime"), np.float32(elapsed_time))
        glUniform1f(glGetUniformLocation(self.shader_program, "deltaTime"), self.delta_time)

        # Update particles based on the selected mode
        if self.particle_render_mode == 'compute_shader':
            # Use compute shader only for particle updates
            self._update_particles_compute_shader()
        elif self.particle_render_mode == 'transform_feedback':
            self._update_particles_transform_feedback()
            if self.particle_generator:
                self._remove_expired_particles_transform_feedback()
                self._generate_new_particles_transform_feedback()
        elif self.particle_render_mode == 'cpu':
            self._update_particles_cpu()
            if self.particle_generator:
                self._generate_particles_cpu()

        if self.debug_mode and self.particle_render_mode != 'compute_shader':
            # Calculate and print the number of active particles
            num_active_particles = self.max_particles - len(self.free_slots)
            print(f"Number of active particles: {num_active_particles}")

    def _remove_expired_particles_transform_feedback(self):
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

    def _generate_new_particles_transform_feedback(self):
        # Check if sufficient time has passed since the last generation
        current_time = time.time()
        time_since_last_generation = current_time - self.last_generation_time

        if time_since_last_generation < self.generator_delay:
            return  # Not enough time has passed, do not generate new particles yet

        # Calculate how many new particles we can generate
        num_free_slots = len(self.free_slots)
        if num_free_slots <= 0:
            return  # No free slots available

        num_gen_particles = min(num_free_slots, self.particle_batch_size)

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
        self.last_generation_time = current_time  # Update the last generation time

    def _generate_particles_cpu(self):
        """
        Generate new particles if there are free slots available.
        """
        current_time = time.time()
        num_free_slots = np.sum(self.cpu_particles[:, 7] == 0)  # Count expired particles

        if num_free_slots > 0:
            num_gen_particles = min(num_free_slots, self.particle_batch_size)

            # Generate new particles
            new_particles = np.zeros((num_gen_particles, 10), dtype=np.float32)
            new_particles[:, 0:3] = np.random.uniform(-self.width, self.width, (num_gen_particles, 3))
            new_particles[:, 1] = np.random.uniform(-self.height, self.height, num_gen_particles)
            new_particles[:, 2] = np.random.uniform(-self.depth, self.depth, num_gen_particles)
            new_particles[:, 3:6] = np.random.uniform(-0.5, 0.5, (num_gen_particles, 3))
            new_particles[:, 6] = current_time  # Spawn time
            new_particles[:, 7] = np.random.uniform(0.1, self.particle_max_lifetime, num_gen_particles)  # Lifetime
            new_particles[:, 8] = np.arange(self.generated_particles,
                                            self.generated_particles + num_gen_particles)  # Particle ID

            # Insert new particles into free slots
            expired_indices = np.where(self.cpu_particles[:, 7] == 0)[0]

            for i in range(num_gen_particles):
                idx = expired_indices[i]
                self.cpu_particles[idx] = new_particles[i]

            self.generated_particles += num_gen_particles
            self.last_generation_time = current_time

    def _update_particles_cpu(self):
        """
        Update particle data on the CPU.
        Simulate particle movement, gravity, collisions, lifetime, weight, and fluid forces.
        """
        current_time = time.time() - self.start_time  # Relative time since particle system started

        if self.debug_mode:
            print(f"Number of particles: {len(self.cpu_particles)}")
            print(f"Particle data: {self.cpu_particles}")

        # Update active particles
        for i in range(len(self.cpu_particles)):
            # Explicitly copy position and velocity to avoid referencing issues
            position = self.cpu_particles[i, 0:3].copy()  # Create a copy of the position array
            velocity = self.cpu_particles[i, 3:6].copy()  # Create a copy of the velocity array
            spawn_time = self.cpu_particles[i, 6]  # No need to copy as it's a single float
            lifetime = self.cpu_particles[i, 7]  # No need to copy as it's a single float

            # Calculate the time that has passed since the particle was spawned (relative to particle system start time)
            elapsed_time = current_time - spawn_time

            if lifetime > 0.0 and elapsed_time < lifetime:  # Only process active particles that haven't expired
                # Generate a random weight for this particle (similar to shader logic)
                particle_id = self.cpu_particles[i, 8]
                weight = np.interp(np.sin(particle_id * 43758.5453) % 1.0, [0, 1],
                                   [self.particle_min_weight, self.particle_max_weight])

                # Adjust gravity by weight (heavier particles are less affected by gravity)
                adjusted_gravity = self.particle_gravity / weight
                velocity += adjusted_gravity * self.delta_time

                # Apply fluid forces if fluid simulation is enabled
                if self.fluid_simulation:
                    # Calculate fluid pressure and viscosity forces
                    pressure_force = -velocity / np.linalg.norm(velocity) * self.particle_pressure if np.linalg.norm(
                        velocity) != 0 else 0
                    viscosity_force = -velocity * self.particle_viscosity
                    velocity += (pressure_force + viscosity_force) * self.delta_time

                # Clamp velocity to the max velocity
                speed = np.linalg.norm(velocity)
                if speed > self.particle_max_velocity:
                    velocity = velocity / speed * self.particle_max_velocity

                # Update position based on velocity
                position += velocity * self.delta_time

                # Check for collision with the ground plane
                distance_to_ground = np.dot(position,
                                            self.particle_ground_plane_normal) - self.particle_ground_plane_height

                if distance_to_ground < 0.0:  # Particle is below or at the ground
                    # Reflect the velocity based on the ground plane normal
                    velocity = velocity - 2 * np.dot(velocity,
                                                     self.particle_ground_plane_normal) * self.particle_ground_plane_normal
                    velocity *= self.particle_bounce_factor  # Apply the bounce factor

                    # Prevent the particle from sinking below the ground
                    position -= self.particle_ground_plane_normal * distance_to_ground

                    # Ensure the particle bounces with a minimum upward velocity to avoid sticking
                    if abs(velocity[1]) < 0.1:  # Assuming Y-axis is up/down, adjust threshold as needed
                        velocity[1] = 0.1  # Small positive value to ensure it moves upward

                # Update lifetime percentage (now correctly calculated)
                lifetime_percentage = elapsed_time / lifetime
                lifetime_percentage = max(0.0, min(lifetime_percentage, 1.0))  # Clamp between 0.0 and 1.0
                self.cpu_particles[i, 9] = lifetime_percentage  # Write back to the particle array

                # Expire particle if its lifetime is over
                if lifetime_percentage >= 1.0:
                    self.cpu_particles[i, 7] = 0.0  # Expire particle by setting its lifetime to 0

                # Write back the updated position and velocity to the particle array
                self.cpu_particles[i, 0:3] = position
                self.cpu_particles[i, 3:6] = velocity

                # Debug output to track lifetime, weight, and velocity
                if self.debug_mode:
                    print(
                        f"Particle {i}: Position {position}, Velocity {velocity}, Weight {weight}, ID {particle_id}, Lifetime Percentage {lifetime_percentage}")

        # Upload the CPU-calculated particle data (positions, colors, etc.) to the GPU for rendering.
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)

        # Create a combined array to upload position and lifetime percentage
        particle_data_to_upload = np.hstack((
            self.cpu_particles[:, 0:3],  # Position
            self.cpu_particles[:, 9:10],  # Lifetime percentage
            self.cpu_particles[:, 8:9],  # Particle ID
        ))

        # Upload data to the GPU
        glBufferSubData(GL_ARRAY_BUFFER, 0, particle_data_to_upload.nbytes, particle_data_to_upload)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the buffer

    def _update_particles_compute_shader(self):
        """
        Update the particle system by dispatching the compute shader, respecting particle generator logic.
        """
        glUseProgram(self.compute_shader_program)

        # Set uniforms and dispatch compute shader
        self.set_compute_uniforms()

        # Dispatch compute shader
        num_workgroups = (self.max_particles + 127) // 128
        glDispatchCompute(num_workgroups, 1, 1)

        # Make sure compute shader writes are complete
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)

        glUseProgram(self.shader_program)  # Switch back to the vertex/fragment shader

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

        # Define a mapping from particle types to OpenGL primitives
        primitive_types = {
            'points': GL_POINTS,
            'lines': GL_LINES,
            'line_strip': GL_LINE_STRIP,
            'line_loop': GL_LINE_LOOP,
            'lines_adjacency': GL_LINES_ADJACENCY,
            'line_strip_adjacency': GL_LINE_STRIP_ADJACENCY,
            'triangles': GL_TRIANGLES,
            'triangle_strip': GL_TRIANGLE_STRIP,
            'triangle_fan': GL_TRIANGLE_FAN,
            'triangles_adjacency': GL_TRIANGLES_ADJACENCY,
            'triangle_strip_adjacency': GL_TRIANGLE_STRIP_ADJACENCY,
            'patches': GL_PATCHES,
        }

        # Get the primitive type from the mapping, default to GL_POINTS if not found
        primitive = primitive_types.get(self.particle_type, GL_POINTS)

        glDrawArrays(primitive, 0, self.total_particles)  # Draw all particles with the selected primitive
        glBindVertexArray(0)
