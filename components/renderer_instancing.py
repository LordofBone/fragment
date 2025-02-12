# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import time

from OpenGL.GL import *

from components.audio_player import AudioPlayer
from components.model_renderer import ModelRenderer
from components.particle_renderer import ParticleRenderer
from components.renderer_window import RendererWindow
from components.scene_constructor import SceneConstructor
from components.skybox_renderer import SkyboxRenderer
from components.surface_renderer import SurfaceRenderer


class RenderingInstance:
    """
    RenderingInstance coordinates all rendering activities:
      - Window creation and management
      - Scene construction and renderers
      - Framebuffer management
      - Audio playback
      - Main loop and updates (FPS, events)
    """

    # --------------------------------------------------------------------------
    # Initialization
    # --------------------------------------------------------------------------
    def __init__(self, config):
        """
        Initialize the RenderingInstance with a given configuration.

        Args:
            config: A RendererConfig object containing various rendering options.
        """
        # --- Primary Configuration ---
        self.config = config

        # --- Window/Context & Runtime State ---
        self.render_window = None
        self.duration = 0
        self.running = False

        # --- Scene Management ---
        self.scene_construct = SceneConstructor()
        self.render_order = []

        # --- Framebuffer Tracking ---
        self.framebuffers = {}

        # --- Audio ---
        self.audio_player = None

    # --------------------------------------------------------------------------
    # Setup and Lifecycle Methods
    # --------------------------------------------------------------------------
    def setup(self):
        """
        Set up the rendering instance:
          - Create the window
          - Initialize renderers
          - Create any needed framebuffers
        """
        # 1) Create the main window
        self.render_window = RendererWindow(
            window_size=self.config.window_size,
            title=self.config.window_title,
            msaa_level=self.config.msaa_level,
            vsync_enabled=self.config.vsync_enabled,
            fullscreen=self.config.fullscreen,
        )

        # 2) Store the maximum run duration
        self.duration = self.config.duration

        # 3) Set up each renderer in the scene
        for renderer in self.scene_construct.renderers.values():
            renderer.setup()

        # 4) Initialize framebuffers
        self.initialize_framebuffers(self.config.window_size[0], self.config.window_size[1])

    def run(self, stats_queue=None, stop_event=None):
        """
        Start the main rendering loop. Collect FPS and handle events.

        Args:
            stats_queue: Optional multiprocessing.Queue for sending stats.
            stop_event: Optional multiprocessing.Event for stopping externally.
        """
        # 1) Perform initial setup
        self.setup()

        # 2) Notify that renderer is ready
        if stats_queue is not None:
            stats_queue.put(("ready", None))

        # 3) Begin the main loop
        self.running = True
        start_time = time.time()

        # --- FPS Tracking ---
        fps_update_interval = 1.0  # seconds
        last_fps_update_time = time.time()
        fps_accumulator = 0.0
        fps_frame_count = 0

        # 4) Start audio playback if enabled
        self.start_audio()

        # 5) Main Loop
        while self.running and (time.time() - start_time) < self.duration:
            # Check external stop_event
            if stop_event is not None and stop_event.is_set():
                print("Benchmark stopped by user.")
                break

            # Update delta time (in seconds)
            delta_time = self.render_window.clock.tick() / 1000.0

            # Handle window events (returns True if close requested)
            if self.render_window.handle_events():
                if stats_queue:
                    stats_queue.put(("stopped_by_user", True))
                self.running = False
                break

            # Clear screen
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            # Render all scene objects
            self.render_scene(delta_time)

            # Gather FPS data
            current_fps = self.render_window.clock.get_fps()
            fps_accumulator += current_fps
            fps_frame_count += 1

            current_time = time.time()
            if current_time - last_fps_update_time >= fps_update_interval:
                average_fps = fps_accumulator / fps_frame_count
                if stats_queue:
                    stats_queue.put(("fps", average_fps))
                self.render_window.draw_fps_in_title(average_fps)
                # Reset FPS tracking
                fps_accumulator = 0.0
                fps_frame_count = 0
                last_fps_update_time = current_time

            # Update display
            self.render_window.display_flip()

        # 6) Shutdown once loop finishes or is broken
        self.shutdown()

    def shutdown(self):
        """
        Clean up the rendering instance:
          - Stop audio
          - Shut down each renderer and delete framebuffers
          - Close the window (OpenGL context)
        """
        self.running = False

        # 1) Stop audio if active
        if self.audio_player:
            self.audio_player.stop()

        # 2) Shut down renderers
        for renderer in self.scene_construct.renderers.values():
            renderer.shutdown()

        # 3) Clean up framebuffers
        for framebuffer, texture in self.framebuffers.values():
            glDeleteFramebuffers(1, [framebuffer])
            glDeleteTextures(1, [texture])
        self.framebuffers.clear()

        # 4) Close the window/context
        if self.render_window:
            self.render_window.shutdown()

    # --------------------------------------------------------------------------
    # Audio Methods
    # --------------------------------------------------------------------------
    def start_audio(self):
        """
        Start audio playback if sound is enabled and an audio file is provided.
        """
        if not self.config.sound_enabled:
            return  # No audio if disabled

        if self.config.background_audio:
            self.audio_player = AudioPlayer(
                audio_file=self.config.background_audio,
                delay=self.config.audio_delay,
                loop=self.config.audio_loop,
            )
            self.audio_player.start()

    # --------------------------------------------------------------------------
    # Renderer / Scene Management Methods
    # --------------------------------------------------------------------------
    def add_renderer(self, name, renderer_type, order=None, **params):
        """
        Create and store a new renderer of the given type and name in the scene.

        Args:
            name: Unique name for this renderer.
            renderer_type: One of 'model', 'surface', 'skybox', 'particle'.
            order: Optional manual render order index (lower is earlier).
            **params: Additional parameters for the renderer constructor.
        """
        renderer = self.create_renderer(name, renderer_type, **params)
        self.scene_construct.add_renderer(name, renderer)
        self.update_render_order(name, order)

    def create_renderer(self, name, renderer_type, **params):
        """
        Factory method to create a renderer based on type.

        Args:
            name: Renderer name.
            renderer_type: 'model', 'surface', 'skybox', or 'particle'.
            **params: Additional init parameters for the renderer.

        Returns:
            An instance of the appropriate renderer.
        """
        if renderer_type == "model":
            return ModelRenderer(renderer_name=name, **params)
        elif renderer_type == "surface":
            return SurfaceRenderer(renderer_name=name, **params)
        elif renderer_type == "skybox":
            return SkyboxRenderer(renderer_name=name, **params)
        elif renderer_type == "particle":
            return ParticleRenderer(renderer_name=name, **params)
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")

    def update_render_order(self, name, order):
        """
        Update the render order of the newly added renderer.

        Args:
            name: Name of the renderer.
            order: If None, the renderer is placed at the end;
                   otherwise, a specific integer order is used.
        """
        if order is None:
            order = self.calculate_order()
        self.render_order.append((name, order))
        self.render_order.sort(key=lambda x: x[1])

    def calculate_order(self):
        """
        Return a new render order index, incrementing from the last used value.
        """
        if self.render_order:
            return max(o for _, o in self.render_order) + 1
        return 0

    # --------------------------------------------------------------------------
    # Rendering and Framebuffer Methods
    # --------------------------------------------------------------------------
    def render_scene(self, delta_time):
        """
        Render the entire scene:
          - Render shadow maps (if needed)
          - Render planar views (if used)
          - Finally render the main scene
        """
        # 1) Render shadow maps
        self.render_shadow_maps()

        # 2) Render planar views
        self.render_planar_views()

        # 3) Normal scene rendering
        glViewport(0, 0, self.render_window.window_size[0], self.render_window.window_size[1])
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)

        for renderer_name, _ in self.render_order:
            renderer = self.scene_construct.renderers[renderer_name]
            renderer.update_camera(delta_time)
            renderer.render()

    def render_shadow_maps(self):
        """
        For the first renderer that supports shadow mapping, render a shadow map.
        (If multiple shadow-capable renderers exist, only the first is used.)
        """
        scene_renderers = list(self.scene_construct.renderers.values())
        for renderer_name, _ in self.render_order:
            renderer = self.scene_construct.renderers[renderer_name]
            if renderer.supports_shadow_mapping() and renderer.shadowing_enabled and renderer.lights_enabled:
                renderer.render_shadow_map(scene_renderers)
                break  # Only do one shadow map pass

    def render_planar_views(self):
        """
        If a renderer uses a planar camera, render the scene from that perspective.
        """
        for renderer_name, _ in self.render_order:
            renderer = self.scene_construct.renderers[renderer_name]
            if renderer.planar_camera:
                renderer.render_planar_view(self.scene_construct.renderers.values())

    def initialize_framebuffers(self, width, height):
        """
        Create a framebuffer for each renderer for potential off-screen rendering.

        Args:
            width: Window (or render target) width.
            height: Window (or render target) height.
        """
        for renderer_name in self.scene_construct.renderers:
            self.framebuffers[renderer_name] = self.create_framebuffer(width, height)

    def create_framebuffer(self, width, height):
        """
        Create a new framebuffer with a color texture attachment and a renderbuffer
        for depth/stencil.

        Returns:
            (framebuffer, texture) tuple.
        """
        framebuffer = glGenFramebuffers(1)
        texture = self.create_texture(width, height)
        self.attach_texture_to_framebuffer(framebuffer, texture, width, height)
        return framebuffer, texture

    def create_texture(self, width, height):
        """
        Create and configure a 2D texture.
        """
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        self.set_texture_parameters()
        return texture

    def set_texture_parameters(self):
        """
        Configure basic texture parameters.
        """
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def attach_texture_to_framebuffer(self, framebuffer, texture, width, height):
        """
        Attach a 2D texture and a depth-stencil renderbuffer to a framebuffer.

        Args:
            framebuffer: The OpenGL framebuffer object ID.
            texture: The OpenGL texture object ID.
            width: Texture width.
            height: Texture height.
        """
        glBindFramebuffer(GL_FRAMEBUFFER, framebuffer)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0)

        rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, rbo)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Framebuffer is not complete")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
