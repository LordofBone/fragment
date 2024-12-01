import time

import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs


class ParticleRenderer(AbstractRenderer):
    # Define maximum particles for each render mode (to prevent slowdowns)
    DEFAULT_MAX_PARTICLES_MAPPING = {"cpu": 2000, "transform_feedback": 200000, "compute_shader": 2000000}

    def __init__(
        self,
        renderer_name,
        max_particles_map=None,
        particles_max=100,
        particle_batch_size=1,
        particle_render_mode="transform_feedback",
        particle_shader_override=False,
        particle_generator=False,
        generator_delay=0.0,
        particle_type="point",
        particle_size=2.0,
        particle_smooth_edges=False,
        max_height=1.0,
        max_width=1.0,
        max_depth=1.0,
        min_height=1.0,
        min_width=1.0,
        min_depth=1.0,
        particle_ground_plane_height=0.0,
        min_initial_velocity_x=-0.5,
        max_initial_velocity_x=0.5,
        min_initial_velocity_y=-0.5,
        max_initial_velocity_y=0.5,
        min_initial_velocity_z=-0.5,
        max_initial_velocity_z=0.5,
        particle_max_velocity=10.0,
        particle_max_lifetime=5.0,
        particle_spawn_time_jitter=False,
        particle_max_spawn_time_jitter=0.0,
        particle_color=(1.0, 0.5, 0.2),
        particle_fade_to_color=False,
        shader_particle_fade_color=(0.0, 1.0, 0.0),
        particle_gravity=(0.0, -9.81, 0.0),
        particle_bounce_factor=0.6,
        particle_ground_plane_normal=(0.0, 1.0, 0.0),
        particle_min_weight=0.5,
        particle_max_weight=1.0,
        fluid_simulation=False,
        fluid_force_multiplier=1.0,
        particle_pressure=1.0,
        particle_viscosity=0.5,
        **kwargs,
    ):
        """
        Initialize the ParticleRenderer with various parameters.

        :param particles_max: Maximum number of particles that can be generated and managed.
        :param particle_batch_size: Number of particles to generate in each batch.
        :param particle_render_mode: Mode used to render particles ('compute_shader', 'transform_feedback', or 'cpu').
        :param particle_generator: Boolean indicating whether the particle system is in generator mode.
        :param generator_delay: Delay between particle generations in seconds.
        :param particle_type: Type of primitive used for particles (e.g., 'points').
        :param kwargs: Additional keyword arguments for customization.
        """
        super().__init__(renderer_name=renderer_name, **kwargs)

        # Handle the max_particles_map override
        if max_particles_map is not None:
            if not isinstance(max_particles_map, dict):
                raise TypeError("max_particles_map must be a dictionary.")
            # Ensure that all keys in max_particles_map are valid render modes
            invalid_keys = set(max_particles_map.keys()) - set(self.DEFAULT_MAX_PARTICLES_MAPPING.keys())
            if invalid_keys:
                raise ValueError(f"Invalid render modes in max_particles_map: {invalid_keys}")
            self.max_particles_mapping = max_particles_map
        else:
            self.max_particles_mapping = self.DEFAULT_MAX_PARTICLES_MAPPING

        self.particle_render_mode = particle_render_mode
        # Set max_particles based on the render mode
        self.max_particles = min(particles_max, self.max_particles_mapping[self.particle_render_mode])
        self.particle_batch_size = min(particle_batch_size, self.max_particles)
        self.active_particles = 0  # Number of currently active particles
        self.particles_to_render = 0  # Number of particles to render
        self.total_particles = self.max_particles  # Always process all particles

        self.particle_shader_override = particle_shader_override
        self.particle_generator = particle_generator  # Control generator mode
        self.generator_delay = generator_delay  # Delay between particle generations in seconds
        self.generated_particles = 0  # Track total generated particles
        self.last_generation_time = time.time()  # Track the last time particles were generated
        self.particle_type = particle_type  # Primitive type for rendering

        # Control flag for particle generation in compute shader and CPU modes
        if self.generator_delay == 0.0:
            self.should_generate = True
        else:
            self.should_generate = False

        # Set up specific particle attributes for transform feedback mode, these are computed in the stack_initial_data method
        self.stride_length_tf_compute = None
        self.particle_byte_size_tf_compute = None
        self.buffer_size_tf_compute = None

        self.total_floats_per_particle = None  # Total number of floats per particle

        # Set up specific particle attributes for CPU mode
        self.stride_length_cpu = 6  # Number of floats per particle for CPU mode (position, lifetimePercentage)
        self.particle_byte_size_cpu = self.stride_length_cpu * self.float_size
        self.buffer_size_cpu = self.max_particles * self.particle_byte_size_cpu  # Total buffer size in bytes

        self.current_vbo_index = int
        self.latest_vbo_index = int
        self.vao = None
        self.vbo = None
        self.feedback_vbo = None
        self.ssbo = None
        self.generation_data_buffer = None
        self.particle_size = particle_size  # Default particle size
        self.particle_smooth_edges = particle_smooth_edges  # Smooth edges for particles

        self.max_height = max_height  # Default height for the particle field
        self.max_width = max_width  # Default width for the particle field
        self.max_depth = max_depth  # Default depth for the particle field
        self.min_height = min_height  # Default height for the particle field
        self.min_width = min_width  # Default width for the particle field
        self.min_depth = min_depth  # Default depth for the particle field
        self.start_time = time.time()  # Store the start time (epoch)
        self.last_time = self.start_time  # Store the last frame time for delta time calculations

        self.particle_ground_plane_height = particle_ground_plane_height

        # Set up particle initial velocity ranges
        self.min_initial_velocity_x = min_initial_velocity_x
        self.max_initial_velocity_x = max_initial_velocity_x
        self.min_initial_velocity_y = min_initial_velocity_y
        self.max_initial_velocity_y = max_initial_velocity_y
        self.min_initial_velocity_z = min_initial_velocity_z
        self.max_initial_velocity_z = max_initial_velocity_z

        # Set up particle absolute max velocity
        self.particle_max_velocity = particle_max_velocity
        self.particle_max_lifetime = particle_max_lifetime
        self.particle_spawn_time_jitter = particle_spawn_time_jitter
        self.particle_max_spawn_time_jitter = particle_max_spawn_time_jitter

        self.free_slots = []

        # this option is to allow for overriding of shaders for the particle system from the scenario calling code
        if self.particle_shader_override is True:
            pass
        elif self.particle_render_mode == "transform_feedback":
            self.shader_names = {
                "vertex": "particles_transform_feedback",
                "fragment": "particles",
                "compute": None,
            }
        elif self.particle_render_mode == "compute_shader":
            self.shader_names = {
                "vertex": "particles_compute_shader",
                "fragment": "particles",
                "compute": "particles",
            }
        elif self.particle_render_mode == "cpu":
            self.shader_names = {
                "vertex": "particles_cpu",
                "fragment": "particles",
                "compute": None,
            }

        self.cpu_particles = np.zeros((self.max_particles, 10), dtype=np.float32)
        self.cpu_particle_gravity = np.array(particle_gravity, dtype=np.float32)

        self.particle_color = glm.vec3(*particle_color)
        self.particle_fade_to_color = particle_fade_to_color
        self.shader_particle_fade_color = glm.vec3(*shader_particle_fade_color)
        self.particle_positions = None
        self.particle_velocities = None
        self.particle_gravity = glm.vec3(particle_gravity)
        self.particle_bounce_factor = particle_bounce_factor
        self.particle_ground_plane_normal = glm.vec3(particle_ground_plane_normal)
        self.particle_min_weight = particle_min_weight
        self.particle_max_weight = particle_max_weight
        self.fluid_simulation = fluid_simulation
        # Currently fluid force multiplier is only used in CPU mode
        self.fluid_force_multiplier = fluid_force_multiplier
        self.particle_pressure = particle_pressure
        self.particle_viscosity = particle_viscosity

        self.current_time = time.time()
        self.delta_time = min(self.current_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = self.current_time

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
        if self.particle_render_mode == "transform_feedback":
            # Add lifetimePercentage to the list of variables to capture
            varyings = [
                "tfPosition",
                "tfVelocity",
                "tfSpawnTime",
                "tfParticleLifetime",
                "tfParticleID",
                "tfParticleWeight",
                "tfLifetimePercentage",
            ]
            varyings_c = (ctypes.POINTER(ctypes.c_char) * len(varyings))(
                *[ctypes.create_string_buffer(v.encode("utf-8")) for v in varyings]
            )
            glTransformFeedbackVaryings(
                self.shader_engine.shader_program, len(varyings), varyings_c, GL_INTERLEAVED_ATTRIBS
            )
            glLinkProgram(self.shader_engine.shader_program)

            # Check for successful shader program linking
            if not glGetProgramiv(self.shader_engine.shader_program, GL_LINK_STATUS):
                log = glGetProgramInfoLog(self.shader_engine.shader_program)
                raise RuntimeError(f"Shader program linking failed: {log.decode()}")

    def supports_shadow_mapping(self):
        return False

    def set_view_projection_matrices(self):
        """
        Send the view and projection matrices to the shader.
        """
        self.setup_camera()

        # Get the uniform locations for the view and projection matrices
        view_location = glGetUniformLocation(self.shader_engine.shader_program, "view")
        projection_location = glGetUniformLocation(self.shader_engine.shader_program, "projection")
        camera_position_location = glGetUniformLocation(self.shader_engine.shader_program, "cameraPosition")
        model_matrix_location = glGetUniformLocation(self.shader_engine.shader_program, "model")

        # Pass the view and projection matrices to the shader
        glUniformMatrix4fv(view_location, 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(projection_location, 1, GL_FALSE, glm.value_ptr(self.projection))
        glUniform3fv(camera_position_location, 1, glm.value_ptr(self.camera_position))

        # Pass the model matrix (which includes scaling, rotating, translating)
        glUniformMatrix4fv(model_matrix_location, 1, GL_FALSE, glm.value_ptr(self.model_matrix))

    def create_buffers(self):
        """
        Create buffers based on the particle render mode (transform_feedback, compute_shader, or cpu).
        """
        # Initialize the current VBO index
        self.current_vbo_index = 0
        self.latest_vbo_index = 0

        initial_batch_size = self.particle_batch_size if self.particle_generator else self.max_particles
        particles = self.stack_initial_data(
            initial_batch_size, pad_to_multiple_of_16=(self.particle_render_mode == "compute_shader")
        )
        # Initialize the particle buffer
        particle_data = self.initialize_particle_data(initial_batch_size, particles)

        if self.particle_render_mode == "transform_feedback":
            self.setup_transform_feedback_buffers(particle_data)
        elif self.particle_render_mode == "compute_shader":
            self.setup_compute_shader_buffers(particle_data)
        elif self.particle_render_mode == "cpu":
            self.setup_cpu_buffers(particle_data)
        else:
            raise ValueError(f"Unknown render mode: {self.particle_render_mode}")

        if self.debug_mode:
            print(f"Initial Particle data: {particles}")

    def initialize_particle_data(self, initial_batch_size, particles):
        """
        Initialize particle data for the selected render mode.
        """
        particle_data = np.zeros((self.max_particles, self.stride_length_tf_compute), dtype=np.float32)

        # Assign particle IDs based on slot indices
        particle_data[:, 10] = np.arange(self.max_particles, dtype=np.float32)

        # Set lifetimePercentage to 1.0 for inactive particles
        particle_data[:, 12] = 1.0  # Inactive particles

        # Optionally, set positions of inactive particles off-screen
        particle_data[:, 0:3] = 10000.0  # Set x, y, z positions to a large value

        # Insert the initial particles into the buffer
        particle_data[:initial_batch_size, :10] = particles[:, :10]  # Copy attributes up to 'particleID'
        particle_data[:initial_batch_size, 11] = particles[:, 11]  # Copy weight
        particle_data[:initial_batch_size, 12] = 0.0  # Active particles

        self.active_particles = initial_batch_size
        self.generated_particles += self.active_particles
        return particle_data

    def setup_transform_feedback_buffers(self, particle_data):
        """
        Setup buffers for transform feedback-based particle rendering.
        """
        self.shader_engine.use_shader_program()

        # Create two VBOs for ping-pong buffering
        self.vbos = glGenBuffers(2)

        # Initialize both VBOs with the particle data
        for vbo in self.vbos:
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, self.buffer_size_tf_compute, particle_data, GL_DYNAMIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Create the VAO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        # Bind the first VBO to set up vertex attributes
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[0])
        self._setup_vertex_attributes()

        glBindVertexArray(0)

    def setup_compute_shader_buffers(self, particle_data):
        """
        Setup buffers for compute shader-based particle rendering.
        """
        self.shader_engine.use_compute_shader_program()

        # Create the SSBO for particle data
        self.ssbo = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
        glBufferData(GL_SHADER_STORAGE_BUFFER, particle_data.nbytes, particle_data, GL_DYNAMIC_COPY)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

        # Create the SSBO for generation data (particlesGenerated)
        generation_data = np.zeros(1, dtype=np.uint32)  # Only 'particlesGenerated' needed
        self.generation_data_buffer = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.generation_data_buffer)
        glBufferData(GL_SHADER_STORAGE_BUFFER, generation_data.nbytes, generation_data, GL_DYNAMIC_DRAW)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.generation_data_buffer)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

        # Set up the VAO for rendering
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.ssbo)
        glBindVertexArray(0)

    def setup_cpu_buffers(self, particle_data):
        """
        Setup buffers for CPU-based particle rendering.
        """
        self.cpu_particles = particle_data

        self.shader_engine.use_shader_program()

        self.vao, self.vbo = glGenVertexArrays(1), glGenBuffers(1)
        glBindVertexArray(self.vao)

        # Allocate buffer for the maximum number of particles
        buffer_size = self.max_particles * self.particle_byte_size_cpu
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, buffer_size, None, GL_DYNAMIC_DRAW)

        self.set_cpu_uniforms()

        # Set up the vertex attributes
        self._setup_vertex_attributes_cpu()

        glBindVertexArray(0)

    def generate_initial_data(self, num_particles=0):
        """
        Generate initial particle data arrays.

        :param num_particles: Number of particles to generate data for.
        :return: Tuple containing particle positions, velocities, spawn times, lifetimes, IDs, lifetime percentages, and weights.
        """
        self.current_time = time.time()

        particle_positions = np.zeros((num_particles, 4), dtype=np.float32)
        particle_positions[:, 0] = np.random.uniform(self.min_width, self.max_width, num_particles)
        particle_positions[:, 1] = np.random.uniform(self.min_height, self.max_height, num_particles)
        particle_positions[:, 2] = np.random.uniform(self.min_depth, self.max_depth, num_particles)
        particle_positions[:, 3] = (
            1.0  # Set w-component to 1.0 (required for calculations for worldPosition vec4 in vertex shaders)
        )

        particle_velocities = np.zeros((num_particles, 4), dtype=np.float32)
        particle_velocities[:, 0] = np.random.uniform(
            self.min_initial_velocity_x, self.max_initial_velocity_x, num_particles
        )
        particle_velocities[:, 1] = np.random.uniform(
            self.min_initial_velocity_y, self.max_initial_velocity_y, num_particles
        )
        particle_velocities[:, 2] = np.random.uniform(
            self.min_initial_velocity_z, self.max_initial_velocity_z, num_particles
        )

        if self.particle_spawn_time_jitter:
            jitter_values = np.random.uniform(0, self.particle_max_spawn_time_jitter, (num_particles, 1)).astype(
                np.float32
            )
            spawn_times = (
                np.full((num_particles, 1), self.current_time - self.start_time, dtype=np.float32) + jitter_values
            )
        else:
            spawn_times = np.full((num_particles, 1), self.current_time - self.start_time, dtype=np.float32)

        if self.particle_max_lifetime > 0.0:
            lifetimes = np.random.uniform(0.1, self.particle_max_lifetime, (num_particles, 1)).astype(np.float32)
        else:
            lifetimes = np.full((num_particles, 1), 0.0, dtype=np.float32)

        particle_ids = np.arange(
            self.generated_particles, self.generated_particles + num_particles, dtype=np.float32
        ).reshape(-1, 1)
        weights = np.random.uniform(self.particle_min_weight, self.particle_max_weight, (num_particles, 1)).astype(
            np.float32
        )
        lifetime_percentages = np.zeros((num_particles, 1), dtype=np.float32)

        if self.debug_mode:
            print(f"Generated Particle positions: {particle_positions}")
            print(f"Generated Particle velocities: {particle_velocities}")
            print(f"Generated Spawn times: {spawn_times}")
            print(f"Generated Lifetimes: {lifetimes}")
            print(f"Generated Particle IDs: {particle_ids}")
            print(f"Generated Weights: {weights}")
            print(f"Generated Lifetime percentages: {lifetime_percentages}")

        return (
            particle_positions,
            particle_velocities,
            spawn_times,
            lifetimes,
            particle_ids,
            weights,
            lifetime_percentages,
        )

    def stack_initial_data(self, num_particles=0, pad_to_multiple_of_16=False):
        particle_positions, particle_velocities, spawn_times, lifetimes, particle_ids, weights, lifetime_percentages = (
            self.generate_initial_data(num_particles)
        )

        # Gather the arrays to be concatenated
        arrays_to_stack = [
            particle_positions,
            particle_velocities,
            spawn_times,
            lifetimes,
            particle_ids,
            weights,
            lifetime_percentages,
        ]

        # Compute the total number of floats per particle so far
        # Each array contributes a certain number of floats per particle
        self.total_floats_per_particle = sum(arr.shape[1] for arr in arrays_to_stack)

        if pad_to_multiple_of_16:
            # Each 16 bytes is 4 floats (since 1 float = 4 bytes)
            # Find the smallest multiple of 4 floats greater than or equal to total_floats_per_particle
            floats_per_particle_padded = ((self.total_floats_per_particle + 3) // 4) * 4
            padding_floats_needed = floats_per_particle_padded - self.total_floats_per_particle

            if padding_floats_needed > 0:
                padding = np.zeros((num_particles, padding_floats_needed), dtype=np.float32)
                arrays_to_stack.append(padding)
        else:
            padding_floats_needed = 0

        # Update stride length and buffer size
        self.stride_length_tf_compute = self.total_floats_per_particle + padding_floats_needed
        self.particle_byte_size_tf_compute = self.stride_length_tf_compute * self.float_size
        self.buffer_size_tf_compute = self.max_particles * self.particle_byte_size_tf_compute

        data = np.hstack(arrays_to_stack).astype(np.float32)
        return data

    def _setup_vertex_attributes(self):
        """
        Setup vertex attribute pointers for position and lifetimePercentage.
        """
        vertex_stride = self.stride_length_tf_compute * self.float_size

        self.shader_engine.use_shader_program()

        # Get the attribute locations
        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_engine.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_engine.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleID")
        weight_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleWeight")
        lifetime_percentage_loc = glGetAttribLocation(self.shader_engine.shader_program, "lifetimePercentage")

        # Ensure all attributes are found
        if (
            position_loc == -1
            or velocity_loc == -1
            or spawn_time_loc == -1
            or lifetime_loc == -1
            or particle_id_loc == -1
            or weight_loc == -1
            or lifetime_percentage_loc == -1
        ):
            # Print attribute locations for debugging
            print(
                f"position_loc: {position_loc}, velocity_loc: {velocity_loc}, spawn_time_loc: {spawn_time_loc}, "
                f"lifetime_loc: {lifetime_loc}, particle_id_loc: {particle_id_loc}, weight_loc: {weight_loc}, particle_percentage_id_loc: {lifetime_percentage_loc}"
            )
            raise RuntimeError(
                "Position, Velocity, Spawn Time, Lifetime, Particle ID, Particle Lifetime Percentage or Weight attribute not found in shader program."
            )

        # Enable and set the vertex attribute arrays for position, velocity, spawn time, lifetime, particle ID, and weight
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 4, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        glEnableVertexAttribArray(velocity_loc)
        glVertexAttribPointer(velocity_loc, 4, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(4 * self.float_size))

        glEnableVertexAttribArray(spawn_time_loc)
        glVertexAttribPointer(
            spawn_time_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(8 * self.float_size)
        )

        glEnableVertexAttribArray(lifetime_loc)
        glVertexAttribPointer(lifetime_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(9 * self.float_size))

        glEnableVertexAttribArray(particle_id_loc)
        glVertexAttribPointer(
            particle_id_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(10 * self.float_size)
        )

        glEnableVertexAttribArray(weight_loc)
        glVertexAttribPointer(weight_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(11 * self.float_size))

        glEnableVertexAttribArray(lifetime_percentage_loc)
        glVertexAttribPointer(
            lifetime_percentage_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(12 * self.float_size)
        )

        if self.debug_mode:
            self._check_vertex_attrib_pointer_setup()

    def _check_vertex_attrib_pointer_setup(self):
        """
        Debug function to check vertex attribute pointer setup.
        """
        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_engine.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_engine.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleID")
        particle_weight_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleWeight")
        particle_lifetime_percentage_loc = glGetAttribLocation(self.shader_engine.shader_program, "lifetimePercentage")

        # Stride and offset values
        position_stride = glGetVertexAttribiv(position_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        velocity_stride = glGetVertexAttribiv(velocity_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        spawn_time_stride = glGetVertexAttribiv(spawn_time_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        lifetime_stride = glGetVertexAttribiv(lifetime_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        particle_id_stride = glGetVertexAttribiv(particle_id_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        particle_weight_stride = glGetVertexAttribiv(particle_weight_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        particle_lifetime_percentage_stride = glGetVertexAttribiv(
            particle_lifetime_percentage_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE
        )

        position_offset = glGetVertexAttribPointerv(position_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        velocity_offset = glGetVertexAttribPointerv(velocity_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        spawn_time_offset = glGetVertexAttribPointerv(spawn_time_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        lifetime_offset = glGetVertexAttribPointerv(lifetime_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        particle_id_offset = glGetVertexAttribPointerv(particle_id_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        particle_weight_offset = glGetVertexAttribPointerv(particle_weight_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        particle_lifetime_percentage_offset = glGetVertexAttribPointerv(
            particle_lifetime_percentage_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER
        )

        print("Position Attributes in _check_vertex_attrib_pointer_setup")
        print(f"Position Attribute: Location = {position_loc}, Stride = {position_stride}, Offset = {position_offset}")
        print(f"Velocity Attribute: Location = {velocity_loc}, Stride = {velocity_stride}, Offset = {velocity_offset}")
        print(
            f"Spawn Time Attribute: Location = {spawn_time_loc}, Stride = {spawn_time_stride}, Offset = {spawn_time_offset}"
        )
        print(f"Lifetime Attribute: Location = {lifetime_loc}, Stride = {lifetime_stride}, Offset = {lifetime_offset}")
        print(
            f"Particle ID Attribute: Location = {particle_id_loc}, Stride = {particle_id_stride}, Offset = {particle_id_offset}"
        )
        print(
            f"Particle Weight Attribute: Location = {particle_weight_loc}, Stride = {particle_weight_stride}, Offset = {particle_weight_offset}"
        )
        print(
            f"Particle Lifetime Percentage Attribute: Location = {particle_lifetime_percentage_loc}, Stride = {particle_lifetime_percentage_stride}, Offset = {particle_lifetime_percentage_offset}"
        )

    def _setup_vertex_attributes_cpu(self):
        """
        Setup vertex attribute pointers for position and any other required data for rendering particles.
        """
        vertex_stride = self.stride_length_cpu * self.float_size

        self.shader_engine.use_shader_program()

        # Get the attribute locations
        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        lifetime_percentage_loc = glGetAttribLocation(self.shader_engine.shader_program, "lifetimePercentage")
        particle_id_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleID")

        # Ensure attributes are found
        if position_loc == -1 or lifetime_percentage_loc == -1 or particle_id_loc == -1:
            raise RuntimeError("Position, Lifetime Percentage, or Particle ID attribute not found in shader program.")

        # Enable and set the vertex attribute arrays
        glEnableVertexAttribArray(position_loc)
        # This is strange as the position is a vec4 but only works when 3 floats are set here for the size
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))

        # Enable and set the vertex attribute array for lifetime percentage
        glEnableVertexAttribArray(lifetime_percentage_loc)
        glVertexAttribPointer(
            lifetime_percentage_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(4 * self.float_size)
        )

        # Enable and set the vertex attribute array for particle ID
        glEnableVertexAttribArray(particle_id_loc)
        glVertexAttribPointer(
            particle_id_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(5 * self.float_size)
        )

        if self.debug_mode:
            print(
                f"Position attribute location: {position_loc}, Lifetime percentage location: {lifetime_percentage_loc}, Lifetime ID location: {particle_id_loc}"
            )

    def set_general_shader_uniforms(self):
        """
        Set up general uniforms for the particle renderer.
        """
        self.shader_engine.use_shader_program()

        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "particleSize"),
            self.particle_size,
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "particleFadeToColor"),
            int(self.particle_fade_to_color),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "particleFadeColor"),
            1,
            glm.value_ptr(self.shader_particle_fade_color),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "smoothEdges"), int(self.particle_smooth_edges)
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "minWeight"),
            self.particle_min_weight,
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "maxWeight"),
            self.particle_max_weight,
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "particleMaxVelocity"),
            self.particle_max_velocity,
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "particleBounceFactor"),
            self.particle_bounce_factor,
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "particleGroundPlaneHeight"),
            self.particle_ground_plane_height,
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "particleColor"),
            1,
            glm.value_ptr(self.particle_color),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "particleGravity"),
            1,
            glm.value_ptr(self.particle_gravity),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.shader_program, "fluidSimulation"), int(self.fluid_simulation)
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "particlePressure"), self.particle_pressure)
        glUniform1f(
            glGetUniformLocation(self.shader_engine.shader_program, "particleViscosity"), self.particle_viscosity
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "particleGroundPlaneNormal"),
            1,
            glm.value_ptr(self.particle_ground_plane_normal),
        )

    def set_compute_uniforms(self):
        """
        Set up the uniforms for the compute shader.
        """
        self.shader_engine.use_compute_shader_program()

        # Determine 'shouldGenerate' based on timing logic
        glUniform1i(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "shouldGenerate"), int(self.should_generate)
        )

        # Set other uniforms
        current_time_sec = time.time() - self.start_time
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "currentTime"), np.float32(current_time_sec)
        )

        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "deltaTime"), np.float32(self.delta_time)
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxLifetime"),
            np.float32(self.particle_max_lifetime),
        )

        glUniform1i(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxParticles"), self.max_particles)
        glUniform1ui(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleBatchSize"),
            np.uint32(self.particle_batch_size),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGenerator"),
            int(self.particle_generator),
        )

        # Set spawn time jitter uniforms
        glUniform1i(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleSpawnTimeJitter"),
            int(self.particle_spawn_time_jitter),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxSpawnTimeJitter"),
            np.float32(self.particle_max_spawn_time_jitter),
        )

        # Set particle properties
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMinWeight"),
            np.float32(self.particle_min_weight),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxWeight"),
            np.float32(self.particle_max_weight),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGravity"),
            1,
            glm.value_ptr(self.particle_gravity),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxVelocity"),
            np.float32(self.particle_max_velocity),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleBounceFactor"),
            np.float32(self.particle_bounce_factor),
        )
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGroundPlaneNormal"),
            1,
            glm.value_ptr(self.particle_ground_plane_normal),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGroundPlaneHeight"),
            np.float32(self.particle_ground_plane_height),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particlePressure"),
            np.float32(self.particle_pressure),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "particleViscosity"),
            np.float32(self.particle_viscosity),
        )
        glUniform1i(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "fluidSimulation"),
            int(self.fluid_simulation),
        )

        # Pass min and max position values to the compute shader
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minX"), np.float32(self.min_width))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxX"), np.float32(self.max_width))
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "minY"), np.float32(self.min_height)
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "maxY"), np.float32(self.max_height)
        )
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minZ"), np.float32(self.min_depth))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxZ"), np.float32(self.max_depth))

        # Set min and max initial velocity values
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "minInitialVelocityX"),
            np.float32(self.min_initial_velocity_x),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "maxInitialVelocityX"),
            np.float32(self.max_initial_velocity_x),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "minInitialVelocityY"),
            np.float32(self.min_initial_velocity_y),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "maxInitialVelocityY"),
            np.float32(self.max_initial_velocity_y),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "minInitialVelocityZ"),
            np.float32(self.min_initial_velocity_z),
        )
        glUniform1f(
            glGetUniformLocation(self.shader_engine.compute_shader_program, "maxInitialVelocityZ"),
            np.float32(self.max_initial_velocity_z),
        )

    def set_cpu_uniforms(self):
        """
        Set up the uniforms for the CPU-based particle rendering.
        """
        self.shader_engine.use_shader_program()

        # Set other uniforms like particle size, color, etc.
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "particleSize"), self.particle_size)
        glUniform3fv(
            glGetUniformLocation(self.shader_engine.shader_program, "particleColor"),
            1,
            glm.value_ptr(self.particle_color),
        )

        if self.debug_mode:
            print("Set particle uniforms for CPU mode.")
            print(f"particleSize: {self.particle_size}")
            print(f"particleColor: {self.particle_color}")

    def update_particles(self):
        """
        Update particle data based on the selected render mode.
        Dispatches the appropriate particle update mechanism based on the render mode.
        """
        self.current_time = time.time()
        elapsed_time = self.current_time - self.start_time
        self.delta_time = min(self.current_time - self.last_time, 0.016)  # Clamp to ~60 FPS
        self.last_time = self.current_time

        # Pass the elapsed time (relative to start) to the shader
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "currentTime"), np.float32(elapsed_time))
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "deltaTime"), self.delta_time)

        # Determine if we should generate a new batch of particles (applies to compute shader and cpu modes)
        if self.generator_delay > 0.0:
            time_since_last_generation = self.current_time - self.last_generation_time
            if self.particle_generator:
                if time_since_last_generation >= self.generator_delay:
                    self.should_generate = True
                    self.last_generation_time = self.current_time
                else:
                    self.should_generate = False
            else:
                self.should_generate = False

        # Update particles based on the selected mode
        if self.particle_render_mode == "compute_shader":
            self._update_particles_compute_shader()
        elif self.particle_render_mode == "transform_feedback":
            if self.particle_generator and self.should_generate:
                self._generate_new_particles_transform_feedback()
            self._remove_expired_particles_transform_feedback()
            self._update_particles_transform_feedback()
        elif self.particle_render_mode == "cpu":
            if self.particle_generator and self.should_generate:
                self._generate_particles_cpu()
            self._update_particles_cpu()

        if self.debug_mode and self.particle_render_mode != "compute_shader":
            # Calculate and print the number of active particles
            print(f"Number of active particles: {self.active_particles}")

    def _remove_expired_particles_transform_feedback(self):
        # Bind the buffer containing the latest particle data
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[self.current_vbo_index])

        # Map the buffer to access data directly
        particle_data = glGetBufferSubData(GL_ARRAY_BUFFER, 0, self.buffer_size_tf_compute)
        particle_data_np = np.frombuffer(particle_data, dtype=np.float32).reshape(-1, self.stride_length_tf_compute)

        # Extract lifetimePercentage column
        lifetime_percentages = particle_data_np[:, 12]

        # Find indices of active and expired particles
        active_indices = np.where(lifetime_percentages < 1.0)[0]
        expired_indices = np.where(lifetime_percentages >= 1.0)[0]

        # Update self.active_particles
        self.active_particles = len(active_indices)

        # Update free_slots
        self.free_slots = list(set(self.free_slots + expired_indices.tolist()))

        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _generate_new_particles_transform_feedback(self):
        # Calculate how many new particles we can generate
        num_free_slots = len(self.free_slots)
        if num_free_slots <= 0:
            return  # No free slots available

        # Ensure we don't generate more particles than max_particles or free slots
        num_gen_particles = min(num_free_slots, self.particle_batch_size)

        new_particles = self.stack_initial_data(num_gen_particles)

        # Write new particles into the buffer at the positions of free slots
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[self.latest_vbo_index])

        for i in range(num_gen_particles):
            slot_index = self.free_slots.pop(0)
            offset = slot_index * self.stride_length_tf_compute * self.float_size
            particle_data = new_particles[i]
            glBufferSubData(GL_ARRAY_BUFFER, offset, particle_data.nbytes, particle_data)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Update particle counts
        self.generated_particles += self.particle_batch_size
        self.last_generation_time = self.current_time  # Update the last generation time

    def _generate_particles_cpu(self):
        """
        Generate new particles if there are free slots available.
        """
        # Update the list of active particles
        active_indices = np.where(self.cpu_particles[:, 12] < 1.0)[0]
        self.active_particles = len(active_indices)
        expired_indices = np.where(self.cpu_particles[:, 12] >= 1.0)[0]
        self.free_slots = list(set(self.free_slots + expired_indices.tolist()))

        num_free_slots = len(self.free_slots)
        if num_free_slots == 0:
            return  # No free slots available

        num_gen_particles = min(num_free_slots, self.particle_batch_size)

        # Generate new particles
        new_particles = self.stack_initial_data(num_gen_particles)

        # Insert new particles into free slots
        for i in range(num_gen_particles):
            slot_idx = self.free_slots.pop(0)
            self.cpu_particles[slot_idx, :] = new_particles[i, :]

        self.generated_particles += num_gen_particles
        self.active_particles += num_gen_particles

    def _update_particles_cpu(self):
        """
        Update particle data on the CPU.
        Simulate particle movement, gravity, collisions, lifetime, weight, and fluid forces.
        Particles with lifetime == 0.0 are immortal.
        """
        current_time = time.time() - self.start_time  # Relative time since particle system started

        for i in range(self.max_particles):
            # Explicitly copy position and velocity to avoid referencing issues
            position = self.cpu_particles[i, 0:4].copy()  # Position (x, y, z, w)
            velocity = self.cpu_particles[i, 4:8].copy()  # Velocity (x, y, z, w)
            spawn_time = self.cpu_particles[i, 8]  # Spawn time
            lifetime = self.cpu_particles[i, 9]  # Lifetime
            particle_id = self.cpu_particles[i, 10]  # Particle ID
            weight = self.cpu_particles[i, 11]  # Weight
            lifetime_percentage = self.cpu_particles[i, 12]  # Lifetime percentage

            if lifetime_percentage >= 1.0:
                continue  # Skip expired particles

            # Apply gravity
            adjusted_gravity = self.cpu_particle_gravity[:3] * weight
            velocity[:3] += adjusted_gravity * self.delta_time

            # Apply fluid forces if fluid simulation is enabled
            if self.fluid_simulation:
                # Calculate fluid damping forces
                pressure_force = -velocity[:3] * self.particle_pressure
                viscosity_force = -velocity[:3] * self.particle_viscosity
                total_fluid_force = pressure_force + viscosity_force

                # Optionally clamp the total fluid force
                max_fluid_force = np.linalg.norm(adjusted_gravity) * self.fluid_force_multiplier
                total_fluid_force_norm = np.linalg.norm(total_fluid_force)
                if total_fluid_force_norm > max_fluid_force:
                    total_fluid_force = (total_fluid_force / total_fluid_force_norm) * max_fluid_force

                velocity[:3] += total_fluid_force * self.delta_time

            # Clamp velocity to the max velocity
            speed = np.linalg.norm(velocity[:3])  # Only consider x, y, z components for speed
            if speed > self.particle_max_velocity:
                velocity[:3] = (velocity[:3] / speed) * self.particle_max_velocity
            # Update position based on velocity
            position += velocity * self.delta_time

            # Check for collision with the ground plane
            distance_to_ground = (
                np.dot(position[:3], self.particle_ground_plane_normal) - self.particle_ground_plane_height
            )

            if distance_to_ground < 0.0:  # Particle is below or at the ground
                # Reflect the velocity based on the ground plane normal
                velocity[:3] = (
                    velocity[:3]
                    - 2 * np.dot(velocity[:3], self.particle_ground_plane_normal) * self.particle_ground_plane_normal
                )
                velocity[:3] *= self.particle_bounce_factor  # Apply the bounce factor

                # Prevent the particle from sinking below the ground
                position[:3] -= self.particle_ground_plane_normal * distance_to_ground

                # Ensure the particle bounces with a minimum upward velocity to avoid sticking
                if abs(velocity[1]) < 0.1:  # Assuming Y-axis is up/down
                    velocity[1] = 0.1  # Small positive value to ensure it moves upward

            # Update lifetime percentage
            if lifetime > 0.0:
                elapsed_time = current_time - spawn_time
                lifetime_percentage = elapsed_time / lifetime
                lifetime_percentage = max(0.0, min(float(lifetime_percentage), 1.0))  # Clamp between 0.0 and 1.0

                if lifetime_percentage >= 1.0:
                    # Particle has expired
                    self.cpu_particles[i, 12] = 1.0  # Lifetime percentage
                    self.free_slots.append(i)  # Add index to free slots
                    continue  # Move to the next particle

            else:
                # For immortal particles
                lifetime_percentage = 0.0

            # Write back the updated lifetime percentage
            self.cpu_particles[i, 12] = lifetime_percentage

            # Write back the updated position and velocity to the particle array
            self.cpu_particles[i, 0:4] = position
            self.cpu_particles[i, 4:8] = velocity

            # Debug output to track lifetime, weight, and velocity
            if self.debug_mode:
                print(
                    f"Particle {i}: Position {position}, Velocity {velocity}, Weight {weight}, ID {particle_id}, Lifetime Percentage {lifetime_percentage}"
                )

        # Upload the CPU-calculated particle data (positions, lifetime percentage, and IDs) to the GPU for rendering.
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)

        # Only upload data for active particles
        particle_data_to_upload = np.hstack(
            (
                self.cpu_particles[: self.active_particles, 0:4],  # Position
                self.cpu_particles[: self.active_particles, 12].reshape(-1, 1),  # Lifetime percentage
                self.cpu_particles[: self.active_particles, 10].reshape(-1, 1),  # Particle ID
            )
        ).astype(np.float32)

        # Upload data to the GPU
        glBufferSubData(GL_ARRAY_BUFFER, 0, particle_data_to_upload.nbytes, particle_data_to_upload)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the buffer

        self.particles_to_render = self.active_particles

    def _update_particles_compute_shader(self):
        """
        Update the particle system by dispatching the compute shader, respecting particle generator logic.
        """
        self.shader_engine.use_compute_shader_program()

        # Set uniforms and dispatch compute shader
        self.set_compute_uniforms()

        # Dispatch compute shader
        num_workgroups = (self.max_particles + 127) // 128
        glDispatchCompute(num_workgroups, 1, 1)

        # Ensure compute shader has finished writing to the SSBO before rendering
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)

        # Reset particlesGenerated counter if necessary
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.generation_data_buffer)
        zero_data = np.array([0], dtype=np.uint32)
        glBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, zero_data.nbytes, zero_data)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

        self.shader_engine.use_shader_program()

        self.particles_to_render = self.max_particles

    def _update_particles_transform_feedback(self):
        self.shader_engine.use_shader_program()

        # Determine source and destination buffers
        source_vbo = self.vbos[self.current_vbo_index]
        dest_vbo = self.vbos[1 - self.current_vbo_index]

        # Bind the VAO
        glBindVertexArray(self.vao)

        # Bind the source buffer for reading vertex attributes
        glBindBuffer(GL_ARRAY_BUFFER, source_vbo)
        self._setup_vertex_attributes()  # Update vertex attribute pointers

        # Enable rasterizer discard to avoid rendering particles to the screen
        glEnable(GL_RASTERIZER_DISCARD)

        # Bind the destination buffer for transform feedback
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, dest_vbo)

        # Start capturing transform feedback
        glBeginTransformFeedback(GL_POINTS)
        glDrawArrays(GL_POINTS, 0, self.max_particles)  # Process all particles
        glEndTransformFeedback()

        # Disable rasterizer discard
        glDisable(GL_RASTERIZER_DISCARD)

        # Ensure that the buffer is synchronized before the next frame
        glMemoryBarrier(GL_TRANSFORM_FEEDBACK_BARRIER_BIT)

        glBindVertexArray(0)

        # Swap the buffers for the next frame
        self.current_vbo_index = 1 - self.current_vbo_index

        self.particles_to_render = self.max_particles

    def print_vao_contents_transform_feedback(self):
        # Get the size of the buffer in bytes
        print(f"Feedback VBO Buffer Size: {self.buffer_size_tf_compute} bytes")

        # Calculate the number of particles
        num_particles = self.buffer_size_tf_compute // self.particle_byte_size_tf_compute
        print(f"Number of particles in the feedback VBO: {num_particles}")

        # Read back the buffer data
        data = glGetBufferSubData(GL_ARRAY_BUFFER, 0, self.buffer_size_tf_compute)

        # Convert the data to a NumPy array
        particle_data = np.frombuffer(data, dtype=np.float32)
        particle_data = particle_data.reshape((num_particles, self.stride_length_tf_compute))

        # Now you can print or process the particle data
        print("Particle Data:")
        print(particle_data)

        # Don't forget to unbind the buffer
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def print_ssbo_contents_compute_shader(self):
        """
        Debug function to print the contents of the SSBO and count active particles.
        """
        # Bind the SSBO
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)

        # Get the size of the buffer in bytes
        print(f"SSBO Buffer Size: {self.buffer_size_tf_compute} bytes")

        # Read back the buffer data
        data = glGetBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, self.buffer_size_tf_compute)

        # Convert the data to a NumPy array
        particle_data = np.frombuffer(data, dtype=np.float32)
        particle_data = particle_data.reshape((self.max_particles, self.stride_length_tf_compute))

        # Check how many particles are active based on lifetimePercentage < 1.0
        active_particles_mask = particle_data[:, 12] < 1.0  # Lifetime percentage at index 12
        active_particles_count = np.sum(active_particles_mask)

        print(f"Number of active particles: {active_particles_count}")
        print(f"Number of total particles in the SSBO: {self.max_particles}")

        # Optionally, you can print out data of only active particles
        active_particle_data = particle_data[active_particles_mask]
        print("Active Particle Data:")
        print(active_particle_data)

        # Unbind the buffer
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

        # Update the active particle count in your class if needed
        self.active_particles = active_particles_count

    def print_cpu_particles(self):
        print(f"Number of particles: {self.active_particles}")
        print("Particle Data:")
        print(self.cpu_particles)

    @common_funcs
    def render(self):
        """
        Render the particle system.
        """
        self.set_general_shader_uniforms()
        self.set_view_projection_matrices()
        self.update_particles()

        # Enable ping-pong rendering for transform feedback mode
        if self.particle_render_mode == "transform_feedback":
            # Determine the current source buffer
            current_vbo = self.vbos[self.current_vbo_index]
            self._setup_vertex_attributes()  # Update vertex attribute pointers
            glBindBuffer(GL_ARRAY_BUFFER, current_vbo)

        # Bind the VAO and update vertex attributes
        glBindVertexArray(self.vao)

        # After rendering, print the SSBO contents if debug mode is enabled
        if self.debug_mode:
            if self.particle_render_mode == "transform_feedback":
                self.print_vao_contents_transform_feedback()
            elif self.particle_render_mode == "compute_shader":
                self.print_ssbo_contents_compute_shader()
            elif self.particle_render_mode == "cpu":
                self.print_cpu_particles()

        # Define a mapping from particle types to OpenGL primitives
        primitive_types = {
            "points": GL_POINTS,
            "lines": GL_LINES,
            "line_strip": GL_LINE_STRIP,
            "line_loop": GL_LINE_LOOP,
            "lines_adjacency": GL_LINES_ADJACENCY,
            "line_strip_adjacency": GL_LINE_STRIP_ADJACENCY,
            "triangles": GL_TRIANGLES,
            "triangle_strip": GL_TRIANGLE_STRIP,
            "triangle_fan": GL_TRIANGLE_FAN,
            "triangles_adjacency": GL_TRIANGLES_ADJACENCY,
            "triangle_strip_adjacency": GL_TRIANGLE_STRIP_ADJACENCY,
            "patches": GL_PATCHES,
        }
        primitive = primitive_types.get(self.particle_type, GL_POINTS)

        # Draw the particles
        glDrawArrays(primitive, 0, self.particles_to_render)

        glBindVertexArray(0)
