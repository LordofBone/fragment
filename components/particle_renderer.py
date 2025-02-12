# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import time

import glm
import numpy as np
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, with_gl_render_state


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def rotate_plane_normal_py(base_normal, angleX_deg, angleY_deg):
    """
    Rotate a base_normal vector by first rotating around the X-axis (angleX_deg)
    and then around the Y-axis (angleY_deg). The final transform is computed as:
      final_matrix = rotY * rotX
    The result is normalized and returned as a NumPy array.
    """
    rx = glm.radians(angleX_deg)
    ry = glm.radians(angleY_deg)
    rotX = glm.rotate(glm.mat4(1.0), rx, glm.vec3(1, 0, 0))
    rotY = glm.rotate(glm.mat4(1.0), ry, glm.vec3(0, 1, 0))
    mat4_final = rotY * rotX

    if not isinstance(base_normal, glm.vec3):
        base_normal = glm.vec3(*base_normal)
    rotated4 = mat4_final * glm.vec4(base_normal, 0.0)
    planeN = np.array([rotated4.x, rotated4.y, rotated4.z], dtype=np.float32)
    norm = np.linalg.norm(planeN)
    if norm > 1e-12:
        planeN /= norm
    return planeN


# ------------------------------------------------------------------------------
# ParticleRenderer Class
# ------------------------------------------------------------------------------
class ParticleRenderer(AbstractRenderer):
    DEFAULT_MAX_PARTICLES_MAPPING = {"cpu": 2000, "transform_feedback": 200000, "compute_shader": 2000000}

    # --------------------------------------------------------------------------
    # Initialization
    # --------------------------------------------------------------------------
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
        particle_fade_color=(0.0, 0.0, 0.0),
        particle_gravity=(0.0, -9.81, 0.0),
        particle_bounce_factor=0.6,
        particle_ground_plane_normal=(0.0, 1.0, 0.0),
        particle_ground_plane_angle=(0.0, 0.0),
        particle_min_weight=0.5,
        particle_max_weight=1.0,
        fluid_simulation=False,
        fluid_force_multiplier=1.0,
        fluid_pressure=1.0,
        fluid_viscosity=0.5,
        **kwargs,
    ):
        """
        Initialize the ParticleRenderer with simulation, appearance, and generation parameters.
        """
        super().__init__(renderer_name=renderer_name, **kwargs)

        # Maximum particles and render mode selection
        if max_particles_map is not None:
            if not isinstance(max_particles_map, dict):
                raise TypeError("max_particles_map must be a dictionary.")
            invalid_keys = set(max_particles_map.keys()) - set(self.DEFAULT_MAX_PARTICLES_MAPPING.keys())
            if invalid_keys:
                raise ValueError(f"Invalid render modes in max_particles_map: {invalid_keys}")
            self.max_particles_mapping = max_particles_map
        else:
            self.max_particles_mapping = self.DEFAULT_MAX_PARTICLES_MAPPING

        self.particle_render_mode = particle_render_mode
        self.max_particles = min(particles_max, self.max_particles_mapping[self.particle_render_mode])
        self.particle_batch_size = min(particle_batch_size, self.max_particles)
        self.active_particles = 0
        self.particles_to_render = 0
        self.total_particles = self.max_particles

        # Particle generation controls
        self.particle_shader_override = particle_shader_override
        self.particle_generator = particle_generator
        self.generator_delay = generator_delay
        self.generated_particles = 0
        self.last_generation_time = time.time()
        self.particle_type = particle_type
        self.should_generate = (self.generator_delay == 0.0)

        # Attributes for transform feedback / compute shader modes
        self.stride_length_tf_compute = None
        self.particle_byte_size_tf_compute = None
        self.buffer_size_tf_compute = None
        self.total_floats_per_particle = None

        # Attributes for CPU mode
        self.stride_length_cpu = 6  # 4 for position, 1 for lifetimePercentage, 1 for particleID
        self.particle_byte_size_cpu = self.stride_length_cpu * self.float_size
        self.buffer_size_cpu = self.max_particles * self.particle_byte_size_cpu

        self.current_vbo_index = None
        self.latest_vbo_index = None
        self.vao = None
        self.vbo = None
        self.feedback_vbo = None
        self.ssbo = None
        self.generation_data_buffer = None
        self.particle_size = particle_size
        self.particle_smooth_edges = particle_smooth_edges

        # Particle field dimensions
        self.max_height = max_height
        self.max_width = max_width
        self.max_depth = max_depth
        self.min_height = min_height
        self.min_width = min_width
        self.min_depth = min_depth
        self.start_time = time.time()
        self.last_time = self.start_time
        self.particle_ground_plane_height = particle_ground_plane_height

        # Initial velocity ranges
        self.min_initial_velocity_x = min_initial_velocity_x
        self.max_initial_velocity_x = max_initial_velocity_x
        self.min_initial_velocity_y = min_initial_velocity_y
        self.max_initial_velocity_y = max_initial_velocity_y
        self.min_initial_velocity_z = min_initial_velocity_z
        self.max_initial_velocity_z = max_initial_velocity_z
        self.particle_max_velocity = particle_max_velocity
        self.particle_max_lifetime = particle_max_lifetime
        self.particle_spawn_time_jitter = particle_spawn_time_jitter
        self.particle_max_spawn_time_jitter = particle_max_spawn_time_jitter
        self.free_slots = []

        # Shader selection based on render mode
        if self.particle_shader_override is True:
            pass
        elif self.particle_render_mode == "transform_feedback":
            self.shader_names = {"vertex": "particles_transform_feedback", "fragment": "particles", "compute": None}
        elif self.particle_render_mode == "compute_shader":
            self.shader_names = {"vertex": "particles_compute_shader", "fragment": "particles", "compute": "particles"}
        elif self.particle_render_mode == "cpu":
            self.shader_names = {"vertex": "particles_cpu", "fragment": "particles", "compute": None}

        # CPU mode data
        self.cpu_particles = np.zeros((self.max_particles, 10), dtype=np.float32)
        self.cpu_particle_gravity = np.array(particle_gravity, dtype=np.float32)

        self.particle_color = glm.vec3(*particle_color)
        self.particle_fade_to_color = particle_fade_to_color
        self.particle_fade_color = glm.vec3(*particle_fade_color)
        self.particle_positions = None
        self.particle_velocities = None
        self.particle_gravity = glm.vec3(particle_gravity)
        self.particle_bounce_factor = particle_bounce_factor
        self.particle_ground_plane_normal = glm.vec3(particle_ground_plane_normal)
        self.particle_ground_plane_angle = glm.vec2(*particle_ground_plane_angle)
        self.particle_min_weight = particle_min_weight
        self.particle_max_weight = particle_max_weight
        self.fluid_simulation = fluid_simulation
        self.fluid_force_multiplier = fluid_force_multiplier
        self.fluid_pressure = fluid_pressure
        self.fluid_viscosity = fluid_viscosity

        self.current_time = time.time()
        self.delta_time = min(self.current_time - self.last_time, 0.016)
        self.last_time = self.current_time

    # --------------------------------------------------------------------------
    # Setup Methods
    # --------------------------------------------------------------------------
    def setup(self):
        """
        Setup the particle renderer: initialize shaders, create buffers,
        and enable point size control.
        """
        self.init_shaders()
        self.create_buffers()
        glEnable(GL_PROGRAM_POINT_SIZE)

    def init_shaders(self):
        """
        Initialize shaders for particle rendering.
        For transform feedback mode, set up the list of varyings and relink the shader.
        """
        super().init_shaders()
        if self.particle_render_mode == "transform_feedback":
            varyings = [
                "tfPosition", "tfVelocity", "tfSpawnTime", "tfParticleLifetime",
                "tfParticleID", "tfParticleWeight", "tfLifetimePercentage"
            ]
            varyings_c = (ctypes.POINTER(ctypes.c_char) * len(varyings))(
                *[ctypes.create_string_buffer(v.encode("utf-8")) for v in varyings]
            )
            glTransformFeedbackVaryings(self.shader_engine.shader_program, len(varyings), varyings_c,
                                        GL_INTERLEAVED_ATTRIBS)
            glLinkProgram(self.shader_engine.shader_program)
            if not glGetProgramiv(self.shader_engine.shader_program, GL_LINK_STATUS):
                log = glGetProgramInfoLog(self.shader_engine.shader_program)
                raise RuntimeError(f"Shader program linking failed: {log.decode()}")

    def supports_shadow_mapping(self):
        return False

    def set_view_projection_matrices(self):
        """
        Setup and upload the view and projection matrices, as well as the camera
        position and model matrix, to the shader.
        """
        self.setup_camera()
        view_location = glGetUniformLocation(self.shader_engine.shader_program, "view")
        projection_location = glGetUniformLocation(self.shader_engine.shader_program, "projection")
        camera_position_location = glGetUniformLocation(self.shader_engine.shader_program, "cameraPosition")
        model_matrix_location = glGetUniformLocation(self.shader_engine.shader_program, "model")
        glUniformMatrix4fv(view_location, 1, GL_FALSE, glm.value_ptr(self.view))
        glUniformMatrix4fv(projection_location, 1, GL_FALSE, glm.value_ptr(self.projection))
        glUniform3fv(camera_position_location, 1, glm.value_ptr(self.camera_position))
        glUniformMatrix4fv(model_matrix_location, 1, GL_FALSE, glm.value_ptr(self.model_matrix))

    # --------------------------------------------------------------------------
    # Buffer Creation Methods
    # --------------------------------------------------------------------------
    def create_buffers(self):
        """
        Create the appropriate particle buffers based on the selected render mode.
        """
        self.current_vbo_index = 0
        self.latest_vbo_index = 0
        initial_batch_size = self.particle_batch_size if self.particle_generator else self.max_particles
        particles = self.stack_initial_data(initial_batch_size,
                                            pad_to_multiple_of_16=(self.particle_render_mode == "compute_shader"))
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
        Initialize the particle data array, setting inactive defaults and inserting
        the initial active particle data.
        """
        particle_data = np.zeros((self.max_particles, self.stride_length_tf_compute), dtype=np.float32)
        particle_data[:, 10] = np.arange(self.max_particles, dtype=np.float32)
        particle_data[:, 12] = 1.0  # Inactive particles
        particle_data[:, 0:3] = 10000.0  # Off-screen initial positions
        particle_data[:initial_batch_size, :10] = particles[:, :10]
        particle_data[:initial_batch_size, 11] = particles[:, 11]
        particle_data[:initial_batch_size, 12] = 0.0  # Active particles
        self.active_particles = initial_batch_size
        self.generated_particles += self.active_particles
        return particle_data

    def stack_initial_data(self, num_particles=0, pad_to_multiple_of_16=False):
        """
        Generate and stack initial particle data arrays.
        If pad_to_multiple_of_16 is True, pad the data so each particle's data is a multiple of 4 floats.
        """
        data_arrays = self.generate_initial_data(num_particles)
        arrays_to_stack = list(data_arrays)
        self.total_floats_per_particle = sum(arr.shape[1] for arr in arrays_to_stack)
        if pad_to_multiple_of_16:
            floats_per_particle_padded = ((self.total_floats_per_particle + 3) // 4) * 4
            padding_floats_needed = floats_per_particle_padded - self.total_floats_per_particle
            if padding_floats_needed > 0:
                padding = np.zeros((num_particles, padding_floats_needed), dtype=np.float32)
                arrays_to_stack.append(padding)
        else:
            padding_floats_needed = 0
        self.stride_length_tf_compute = self.total_floats_per_particle + padding_floats_needed
        self.particle_byte_size_tf_compute = self.stride_length_tf_compute * self.float_size
        self.buffer_size_tf_compute = self.max_particles * self.particle_byte_size_tf_compute
        data = np.hstack(arrays_to_stack).astype(np.float32)
        return data

    def generate_initial_data(self, num_particles=0):
        """
        Generate initial arrays for particle properties:
        positions, velocities, spawn times, lifetimes, IDs, weights, and lifetime percentages.
        """
        self.current_time = time.time()
        particle_positions = np.zeros((num_particles, 4), dtype=np.float32)
        particle_positions[:, 0] = np.random.uniform(self.min_width, self.max_width, num_particles)
        particle_positions[:, 1] = np.random.uniform(self.min_height, self.max_height, num_particles)
        particle_positions[:, 2] = np.random.uniform(self.min_depth, self.max_depth, num_particles)
        particle_positions[:, 3] = 1.0

        particle_velocities = np.zeros((num_particles, 4), dtype=np.float32)
        particle_velocities[:, 0] = np.random.uniform(self.min_initial_velocity_x, self.max_initial_velocity_x,
                                                      num_particles)
        particle_velocities[:, 1] = np.random.uniform(self.min_initial_velocity_y, self.max_initial_velocity_y,
                                                      num_particles)
        particle_velocities[:, 2] = np.random.uniform(self.min_initial_velocity_z, self.max_initial_velocity_z,
                                                      num_particles)

        if self.particle_spawn_time_jitter:
            jitter = np.random.uniform(0, self.particle_max_spawn_time_jitter, (num_particles, 1)).astype(np.float32)
            spawn_times = np.full((num_particles, 1), self.current_time - self.start_time, dtype=np.float32) + jitter
        else:
            spawn_times = np.full((num_particles, 1), self.current_time - self.start_time, dtype=np.float32)

        if self.particle_max_lifetime > 0.0:
            lifetimes = np.random.uniform(0.1, self.particle_max_lifetime, (num_particles, 1)).astype(np.float32)
        else:
            lifetimes = np.full((num_particles, 1), 0.0, dtype=np.float32)

        particle_ids = np.arange(self.generated_particles, self.generated_particles + num_particles,
                                 dtype=np.float32).reshape(-1, 1)
        weights = np.random.uniform(self.particle_min_weight, self.particle_max_weight, (num_particles, 1)).astype(
            np.float32)
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
        particle_positions, particle_velocities, spawn_times, lifetimes, particle_ids, weights, lifetime_percentages)

    # --------------------------------------------------------------------------
    # Buffer Creation for CPU Mode
    # --------------------------------------------------------------------------
    def setup_cpu_buffers(self, particle_data):
        """
        Setup buffers for CPU-based particle rendering.
        Allocates a VAO and VBO, and sets up vertex attribute pointers for CPU mode.
        """
        self.cpu_particles = particle_data
        self.shader_engine.use_shader_program()
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        glBindVertexArray(self.vao)
        buffer_size = self.max_particles * self.particle_byte_size_cpu
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, buffer_size, None, GL_DYNAMIC_DRAW)
        self._setup_vertex_attributes_cpu()
        glBindVertexArray(0)

    # --------------------------------------------------------------------------
    # Buffer Creation for Transform Feedback and Compute Shader Modes
    # --------------------------------------------------------------------------
    def setup_transform_feedback_buffers(self, particle_data):
        """
        Setup buffers for transform feedback-based particle rendering.
        Creates two VBOs for ping-pong buffering and a VAO with vertex attribute setup.
        """
        self.shader_engine.use_shader_program()
        self.vbos = glGenBuffers(2)
        for vbo in self.vbos:
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, self.buffer_size_tf_compute, particle_data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[0])
        self._setup_vertex_attributes()
        glBindVertexArray(0)

    def setup_compute_shader_buffers(self, particle_data):
        """
        Setup buffers for compute shader-based particle rendering.
        Creates an SSBO for particle data and another SSBO for generation data.
        Also sets up a VAO for rendering.
        """
        self.shader_engine.use_compute_shader_program()
        self.ssbo = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
        glBufferData(GL_SHADER_STORAGE_BUFFER, particle_data.nbytes, particle_data, GL_DYNAMIC_COPY)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)
        generation_data = np.zeros(1, dtype=np.uint32)
        self.generation_data_buffer = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.generation_data_buffer)
        glBufferData(GL_SHADER_STORAGE_BUFFER, generation_data.nbytes, generation_data, GL_DYNAMIC_DRAW)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.generation_data_buffer)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.ssbo)
        glBindVertexArray(0)

    # --------------------------------------------------------------------------
    # Vertex Attribute Setup Methods
    # --------------------------------------------------------------------------
    def _setup_vertex_attributes(self):
        """
        Setup vertex attribute pointers for transform feedback mode.
        """
        vertex_stride = self.stride_length_tf_compute * self.float_size
        self.shader_engine.use_shader_program()
        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_engine.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_engine.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleID")
        weight_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleWeight")
        lifetime_percentage_loc = glGetAttribLocation(self.shader_engine.shader_program, "lifetimePercentage")
        if (position_loc == -1 or velocity_loc == -1 or spawn_time_loc == -1 or
                lifetime_loc == -1 or particle_id_loc == -1 or weight_loc == -1 or lifetime_percentage_loc == -1):
            print(f"position_loc: {position_loc}, velocity_loc: {velocity_loc}, spawn_time_loc: {spawn_time_loc}, "
                  f"lifetime_loc: {lifetime_loc}, particle_id_loc: {particle_id_loc}, weight_loc: {weight_loc}, "
                  f"lifetime_percentage_loc: {lifetime_percentage_loc}")
            raise RuntimeError("Required vertex attributes not found in shader program.")
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 4, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(velocity_loc)
        glVertexAttribPointer(velocity_loc, 4, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(4 * self.float_size))
        glEnableVertexAttribArray(spawn_time_loc)
        glVertexAttribPointer(spawn_time_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(8 * self.float_size))
        glEnableVertexAttribArray(lifetime_loc)
        glVertexAttribPointer(lifetime_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(9 * self.float_size))
        glEnableVertexAttribArray(particle_id_loc)
        glVertexAttribPointer(particle_id_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(10 * self.float_size))
        glEnableVertexAttribArray(weight_loc)
        glVertexAttribPointer(weight_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(11 * self.float_size))
        glEnableVertexAttribArray(lifetime_percentage_loc)
        glVertexAttribPointer(lifetime_percentage_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(12 * self.float_size))
        if self.debug_mode:
            self._check_vertex_attrib_pointer_setup()

    def _check_vertex_attrib_pointer_setup(self):
        """
        Debug function to print vertex attribute pointer setup details.
        """
        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        velocity_loc = glGetAttribLocation(self.shader_engine.shader_program, "velocity")
        spawn_time_loc = glGetAttribLocation(self.shader_engine.shader_program, "spawnTime")
        lifetime_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleLifetime")
        particle_id_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleID")
        particle_weight_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleWeight")
        lifetime_percentage_loc = glGetAttribLocation(self.shader_engine.shader_program, "lifetimePercentage")
        pos_stride = glGetVertexAttribiv(position_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        vel_stride = glGetVertexAttribiv(velocity_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        spawn_stride = glGetVertexAttribiv(spawn_time_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        life_stride = glGetVertexAttribiv(lifetime_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        id_stride = glGetVertexAttribiv(particle_id_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        weight_stride = glGetVertexAttribiv(particle_weight_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        pct_stride = glGetVertexAttribiv(lifetime_percentage_loc, GL_VERTEX_ATTRIB_ARRAY_STRIDE)
        pos_offset = glGetVertexAttribPointerv(position_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        vel_offset = glGetVertexAttribPointerv(velocity_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        spawn_offset = glGetVertexAttribPointerv(spawn_time_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        life_offset = glGetVertexAttribPointerv(lifetime_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        id_offset = glGetVertexAttribPointerv(particle_id_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        weight_offset = glGetVertexAttribPointerv(particle_weight_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        pct_offset = glGetVertexAttribPointerv(lifetime_percentage_loc, GL_VERTEX_ATTRIB_ARRAY_POINTER)
        print("Vertex Attribute Setup:")
        print(f"Position: Location={position_loc}, Stride={pos_stride}, Offset={pos_offset}")
        print(f"Velocity: Location={velocity_loc}, Stride={vel_stride}, Offset={vel_offset}")
        print(f"Spawn Time: Location={spawn_time_loc}, Stride={spawn_stride}, Offset={spawn_offset}")
        print(f"Lifetime: Location={lifetime_loc}, Stride={life_stride}, Offset={life_offset}")
        print(f"Particle ID: Location={particle_id_loc}, Stride={id_stride}, Offset={id_offset}")
        print(f"Particle Weight: Location={particle_weight_loc}, Stride={weight_stride}, Offset={weight_offset}")
        print(f"Lifetime Percentage: Location={lifetime_percentage_loc}, Stride={pct_stride}, Offset={pct_offset}")

    def _setup_vertex_attributes_cpu(self):
        """
        Setup vertex attribute pointers for CPU-based particle rendering.
        """
        vertex_stride = self.stride_length_cpu * self.float_size
        self.shader_engine.use_shader_program()
        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        lifetime_percentage_loc = glGetAttribLocation(self.shader_engine.shader_program, "lifetimePercentage")
        particle_id_loc = glGetAttribLocation(self.shader_engine.shader_program, "particleID")
        if position_loc == -1 or lifetime_percentage_loc == -1 or particle_id_loc == -1:
            raise RuntimeError("Required attributes not found in shader program for CPU mode.")
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 4, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(lifetime_percentage_loc)
        glVertexAttribPointer(lifetime_percentage_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(4 * self.float_size))
        glEnableVertexAttribArray(particle_id_loc)
        glVertexAttribPointer(particle_id_loc, 1, GL_FLOAT, GL_FALSE, vertex_stride,
                              ctypes.c_void_p(5 * self.float_size))
        if self.debug_mode:
            print(
                f"CPU Mode: Position loc={position_loc}, Lifetime Percentage loc={lifetime_percentage_loc}, Particle ID loc={particle_id_loc}")

    # --------------------------------------------------------------------------
    # Uniform Setup Methods
    # --------------------------------------------------------------------------
    def set_general_shader_uniforms(self):
        """
        Set general uniforms used by the particle shader.
        """
        self.shader_engine.use_shader_program()
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "particleSize"), self.particle_size)
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "particleFadeToColor"),
                    int(self.particle_fade_to_color))
        glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "particleFadeColor"), 1,
                     glm.value_ptr(self.particle_fade_color))
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "smoothEdges"),
                    int(self.particle_smooth_edges))
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "minWeight"), self.particle_min_weight)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "maxWeight"), self.particle_max_weight)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "particleMaxVelocity"),
                    self.particle_max_velocity)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "particleBounceFactor"),
                    self.particle_bounce_factor)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "particleGroundPlaneHeight"),
                    self.particle_ground_plane_height)
        glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "particleColor"), 1,
                     glm.value_ptr(self.particle_color))
        glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "particleGravity"), 1,
                     glm.value_ptr(self.particle_gravity))
        glUniform1i(glGetUniformLocation(self.shader_engine.shader_program, "fluidSimulation"),
                    int(self.fluid_simulation))
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "fluidPressure"), self.fluid_pressure)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "fluidViscosity"), self.fluid_viscosity)
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "fluidForceMultiplier"),
                    self.fluid_force_multiplier)
        glUniform3fv(glGetUniformLocation(self.shader_engine.shader_program, "particleGroundPlaneNormal"), 1,
                     glm.value_ptr(self.particle_ground_plane_normal))
        glUniform2f(glGetUniformLocation(self.shader_engine.shader_program, "groundPlaneAngle"),
                    self.particle_ground_plane_angle.x, self.particle_ground_plane_angle.y)

    def set_compute_uniforms(self):
        """
        Set uniforms required by the compute shader.
        """
        self.shader_engine.use_compute_shader_program()
        glUniform1i(glGetUniformLocation(self.shader_engine.compute_shader_program, "shouldGenerate"),
                    int(self.should_generate))
        current_time_sec = time.time() - self.start_time
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "currentTime"),
                    np.float32(current_time_sec))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "deltaTime"),
                    np.float32(self.delta_time))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxLifetime"),
                    np.float32(self.particle_max_lifetime))
        glUniform1i(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxParticles"), self.max_particles)
        glUniform1ui(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleBatchSize"),
                     np.uint32(self.particle_batch_size))
        glUniform1i(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGenerator"),
                    int(self.particle_generator))
        glUniform1i(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleSpawnTimeJitter"),
                    int(self.particle_spawn_time_jitter))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxSpawnTimeJitter"),
                    np.float32(self.particle_max_spawn_time_jitter))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMinWeight"),
                    np.float32(self.particle_min_weight))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxWeight"),
                    np.float32(self.particle_max_weight))
        glUniform3fv(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGravity"), 1,
                     glm.value_ptr(self.particle_gravity))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleMaxVelocity"),
                    np.float32(self.particle_max_velocity))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleBounceFactor"),
                    np.float32(self.particle_bounce_factor))
        glUniform3fv(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGroundPlaneNormal"), 1,
                     glm.value_ptr(self.particle_ground_plane_normal))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "particleGroundPlaneHeight"),
                    np.float32(self.particle_ground_plane_height))
        glUniform2f(glGetUniformLocation(self.shader_engine.compute_shader_program, "groundPlaneAngle"),
                    self.particle_ground_plane_angle.x, self.particle_ground_plane_angle.y)
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "fluidPressure"),
                    np.float32(self.fluid_pressure))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "fluidViscosity"),
                    np.float32(self.fluid_viscosity))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "fluidForceMultiplier"),
                    self.fluid_force_multiplier)
        glUniform1i(glGetUniformLocation(self.shader_engine.compute_shader_program, "fluidSimulation"),
                    int(self.fluid_simulation))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minX"), np.float32(self.min_width))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxX"), np.float32(self.max_width))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minY"),
                    np.float32(self.min_height))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxY"),
                    np.float32(self.max_height))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minZ"), np.float32(self.min_depth))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxZ"), np.float32(self.max_depth))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minInitialVelocityX"),
                    np.float32(self.min_initial_velocity_x))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxInitialVelocityX"),
                    np.float32(self.max_initial_velocity_x))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minInitialVelocityY"),
                    np.float32(self.min_initial_velocity_y))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxInitialVelocityY"),
                    np.float32(self.max_initial_velocity_y))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "minInitialVelocityZ"),
                    np.float32(self.min_initial_velocity_z))
        glUniform1f(glGetUniformLocation(self.shader_engine.compute_shader_program, "maxInitialVelocityZ"),
                    np.float32(self.max_initial_velocity_z))

    # --------------------------------------------------------------------------
    # Particle Update Methods
    # --------------------------------------------------------------------------
    def update_particles(self):
        """
        Update the particle system based on the selected render mode.
        This involves updating simulation time, handling particle generation,
        and dispatching the appropriate update routine.
        """
        self.current_time = time.time()
        elapsed_time = self.current_time - self.start_time
        self.delta_time = min(self.current_time - self.last_time, 0.016)
        self.last_time = self.current_time

        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "currentTime"), np.float32(elapsed_time))
        glUniform1f(glGetUniformLocation(self.shader_engine.shader_program, "deltaTime"), self.delta_time)

        if self.generator_delay > 0.0:
            time_since_last = self.current_time - self.last_generation_time
            if self.particle_generator:
                if time_since_last >= self.generator_delay:
                    self.should_generate = True
                    self.last_generation_time = self.current_time
                else:
                    self.should_generate = False
            else:
                self.should_generate = False

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
            print(f"Number of active particles: {self.active_particles}")

    def _remove_expired_particles_transform_feedback(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[self.current_vbo_index])
        particle_data = glGetBufferSubData(GL_ARRAY_BUFFER, 0, self.buffer_size_tf_compute)
        particle_data_np = np.frombuffer(particle_data, dtype=np.float32).reshape(-1, self.stride_length_tf_compute)
        lifetime_pct = particle_data_np[:, 12]
        active_indices = np.where(lifetime_pct < 1.0)[0]
        expired_indices = np.where(lifetime_pct >= 1.0)[0]
        self.active_particles = len(active_indices)
        self.free_slots = list(set(self.free_slots + expired_indices.tolist()))
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _generate_new_particles_transform_feedback(self):
        num_free = len(self.free_slots)
        if num_free <= 0:
            return
        num_gen = min(num_free, self.particle_batch_size)
        new_particles = self.stack_initial_data(num_gen)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[self.latest_vbo_index])
        for i in range(num_gen):
            slot = self.free_slots.pop(0)
            offset = slot * self.stride_length_tf_compute * self.float_size
            pdata = new_particles[i]
            glBufferSubData(GL_ARRAY_BUFFER, offset, pdata.nbytes, pdata)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.generated_particles += self.particle_batch_size
        self.last_generation_time = self.current_time

    def _generate_particles_cpu(self):
        active_idx = np.where(self.cpu_particles[:, 12] < 1.0)[0]
        self.active_particles = len(active_idx)
        expired_idx = np.where(self.cpu_particles[:, 12] >= 1.0)[0]
        self.free_slots = list(set(self.free_slots + expired_idx.tolist()))
        num_free = len(self.free_slots)
        if num_free == 0:
            return
        num_gen = min(num_free, self.particle_batch_size)
        new_particles = self.stack_initial_data(num_gen)
        for i in range(num_gen):
            slot_idx = self.free_slots.pop(0)
            self.cpu_particles[slot_idx, :] = new_particles[i, :]
        self.generated_particles += num_gen
        self.active_particles += num_gen

    def _update_particles_cpu(self):
        current_rel = time.time() - self.start_time
        yaw_deg = self.particle_ground_plane_angle[0]
        pitch_deg = self.particle_ground_plane_angle[1]
        planeN = rotate_plane_normal_py(self.particle_ground_plane_normal, yaw_deg, pitch_deg)
        for i in range(self.max_particles):
            pos = self.cpu_particles[i, 0:4].copy()
            vel = self.cpu_particles[i, 4:8].copy()
            spawn_time = self.cpu_particles[i, 8]
            lifetime = self.cpu_particles[i, 9]
            pid = self.cpu_particles[i, 10]
            weight = self.cpu_particles[i, 11]
            life_pct = self.cpu_particles[i, 12]
            if life_pct >= 1.0:
                continue
            adjusted_grav = self.cpu_particle_gravity[:3] * weight
            vel[:3] += adjusted_grav * self.delta_time
            if self.fluid_simulation:
                pressure = -vel[:3] * self.fluid_pressure
                viscosity = -vel[:3] * self.fluid_viscosity
                total_fluid = pressure + viscosity
                max_fluid = np.linalg.norm(adjusted_grav) * self.fluid_force_multiplier
                fmag = np.linalg.norm(total_fluid)
                if fmag > max_fluid:
                    total_fluid = total_fluid / fmag * max_fluid
                vel[:3] += total_fluid * self.delta_time
            speed = np.linalg.norm(vel[:3])
            if speed > self.particle_max_velocity:
                vel[:3] = vel[:3] / speed * self.particle_max_velocity
            pos[:3] += vel[:3] * self.delta_time
            dist_plane = np.dot(pos[:3], planeN) - self.particle_ground_plane_height
            if dist_plane < 0.0:
                vel_dot = np.dot(vel[:3], planeN)
                vel[:3] = vel[:3] - 2.0 * vel_dot * planeN
                vel[:3] *= self.particle_bounce_factor
                bspeed = np.linalg.norm(vel[:3])
                if bspeed > self.particle_max_velocity:
                    vel[:3] = vel[:3] / bspeed * self.particle_max_velocity
                pos[:3] -= planeN * dist_plane
            if lifetime > 0.0:
                elapsed = current_rel - spawn_time
                new_pct = elapsed / lifetime
                new_pct = max(0.0, min(new_pct, 1.0))
                if new_pct >= 1.0:
                    self.cpu_particles[i, 12] = 1.0
                    self.free_slots.append(i)
                    continue
                else:
                    life_pct = new_pct
            else:
                life_pct = 0.0
            self.cpu_particles[i, 0:4] = pos
            self.cpu_particles[i, 4:8] = vel
            self.cpu_particles[i, 12] = life_pct
            if self.debug_mode:
                print(f"Particle {i} -> Pos {pos}, Vel {vel}, Weight {weight}, ID {pid}, LifetimePct {life_pct}")
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        up_data = np.hstack((
            self.cpu_particles[:self.active_particles, 0:4],
            self.cpu_particles[:self.active_particles, 12].reshape(-1, 1),
            self.cpu_particles[:self.active_particles, 10].reshape(-1, 1)
        )).astype(np.float32)
        glBufferSubData(GL_ARRAY_BUFFER, 0, up_data.nbytes, up_data)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.particles_to_render = self.active_particles

    def _update_particles_compute_shader(self):
        self.shader_engine.use_compute_shader_program()
        self.set_compute_uniforms()
        num_workgroups = (self.max_particles + 127) // 128
        glDispatchCompute(num_workgroups, 1, 1)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.generation_data_buffer)
        zero_data = np.array([0], dtype=np.uint32)
        glBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, zero_data.nbytes, zero_data)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)
        self.shader_engine.use_shader_program()
        self.particles_to_render = self.max_particles

    def _update_particles_transform_feedback(self):
        self.shader_engine.use_shader_program()
        source_vbo = self.vbos[self.current_vbo_index]
        dest_vbo = self.vbos[1 - self.current_vbo_index]
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, source_vbo)
        self._setup_vertex_attributes()
        glEnable(GL_RASTERIZER_DISCARD)
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, dest_vbo)
        glBeginTransformFeedback(GL_POINTS)
        glDrawArrays(GL_POINTS, 0, self.max_particles)
        glEndTransformFeedback()
        glDisable(GL_RASTERIZER_DISCARD)
        if glMemoryBarrier:
            glMemoryBarrier(GL_TRANSFORM_FEEDBACK_BARRIER_BIT)
        else:
            glFinish()
        glBindVertexArray(0)
        self.current_vbo_index = 1 - self.current_vbo_index
        self.particles_to_render = self.max_particles

    # --------------------------------------------------------------------------
    # Debug / Print Methods
    # --------------------------------------------------------------------------
    def print_vao_contents_transform_feedback(self):
        print(f"Feedback VBO Buffer Size: {self.buffer_size_tf_compute} bytes")
        num_particles = self.buffer_size_tf_compute // self.particle_byte_size_tf_compute
        print(f"Number of particles in the feedback VBO: {num_particles}")
        data = glGetBufferSubData(GL_ARRAY_BUFFER, 0, self.buffer_size_tf_compute)
        particle_data = np.frombuffer(data, dtype=np.float32)
        particle_data = particle_data.reshape((num_particles, self.stride_length_tf_compute))
        print("Particle Data:")
        print(particle_data)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def print_ssbo_contents_compute_shader(self):
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
        print(f"SSBO Buffer Size: {self.buffer_size_tf_compute} bytes")
        data = glGetBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, self.buffer_size_tf_compute)
        particle_data = np.frombuffer(data, dtype=np.float32)
        particle_data = particle_data.reshape((self.max_particles, self.stride_length_tf_compute))
        active_mask = particle_data[:, 12] < 1.0
        active_count = np.sum(active_mask)
        print(f"Number of active particles: {active_count}")
        print(f"Total particles in SSBO: {self.max_particles}")
        print("Active Particle Data:")
        print(particle_data[active_mask])
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)
        self.active_particles = active_count

    def print_cpu_particles(self):
        print(f"Number of active particles: {self.active_particles}")
        print("CPU Particle Data:")
        print(self.cpu_particles)

    # --------------------------------------------------------------------------
    # Rendering Method
    # --------------------------------------------------------------------------
    @with_gl_render_state
    def render(self):
        """
        Render the particle system using the selected mode.
        """
        self.set_general_shader_uniforms()
        self.set_view_projection_matrices()
        self.update_particles()
        if self.particle_render_mode == "transform_feedback":
            current_vbo = self.vbos[self.current_vbo_index]
            self._setup_vertex_attributes()
            glBindBuffer(GL_ARRAY_BUFFER, current_vbo)
        glBindVertexArray(self.vao)
        if self.debug_mode:
            if self.particle_render_mode == "transform_feedback":
                self.print_vao_contents_transform_feedback()
            elif self.particle_render_mode == "compute_shader":
                self.print_ssbo_contents_compute_shader()
            elif self.particle_render_mode == "cpu":
                self.print_cpu_particles()
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
        glDrawArrays(primitive, 0, self.particles_to_render)
        glBindVertexArray(0)
