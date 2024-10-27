import time

from OpenGL.GL import *

from components.model_renderer import ModelRenderer
from components.particle_renderer import ParticleRenderer
from components.renderer_window import RendererWindow
from components.scene_constructor import SceneConstructor
from components.skybox_renderer import SkyboxRenderer
from components.surface_renderer import SurfaceRenderer


class RenderingInstance:
    def __init__(self, config):
        self.config = config
        self.render_window = None
        self.scene_construct = SceneConstructor()
        self.framebuffers = {}
        self.render_order = []
        self.running = False  # Flag to control the main loop

    def setup(self):
        self.render_window = RendererWindow(
            window_size=self.config.window_size,
            title=self.config.window_title,
            msaa_level=self.config.msaa_level
        )

        for renderer in self.scene_construct.renderers.values():
            renderer.setup()

        self.initialize_framebuffers(self.config.window_size[0], self.config.window_size[1])

    def initialize_framebuffers(self, width, height):
        for renderer_name in self.scene_construct.renderers:
            self.framebuffers[renderer_name] = self.create_framebuffer(width, height)

    def create_framebuffer(self, width, height):
        framebuffer = glGenFramebuffers(1)
        texture = self.create_texture(width, height)
        self.attach_texture_to_framebuffer(framebuffer, texture, width, height)
        return framebuffer, texture

    def create_texture(self, width, height):
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        self.set_texture_parameters()
        return texture

    def set_texture_parameters(self):
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def attach_texture_to_framebuffer(self, framebuffer, texture, width, height):
        glBindFramebuffer(GL_FRAMEBUFFER, framebuffer)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0)

        rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, rbo)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Framebuffer is not complete")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def add_renderer(self, name, renderer_type, order=None, **params):
        renderer = self.create_renderer(renderer_type, **params)
        self.scene_construct.add_renderer(name, renderer)
        self.update_render_order(name, order)

    def create_renderer(self, renderer_type, **params):
        if renderer_type == "model":
            return ModelRenderer(**params)
        elif renderer_type == "surface":
            return SurfaceRenderer(**params)
        elif renderer_type == "skybox":
            return SkyboxRenderer(**params)
        elif renderer_type == "particle":
            return ParticleRenderer(**params)
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")

    def update_render_order(self, name, order):
        if order is None:
            order = self.calculate_order()

        self.render_order.append((name, order))
        self.render_order.sort(key=lambda x: x[1])

    def calculate_order(self):
        if self.render_order:
            return max(o for _, o in self.render_order) + 1
        return 0

    def run(self, duration=60, stats_queue=None, stop_event=None):
        # Perform setup
        self.setup()

        # Signal that the renderer is fully initialized and ready
        if stats_queue is not None:
            stats_queue.put(('ready', None))

        # Start the main loop
        self.running = True
        start_time = time.time()

        while self.running and (time.time() - start_time) < duration:
            if stop_event is not None and stop_event.is_set():
                print("Benchmark stopped by user.")
                break
            delta_time = self.render_window.clock.tick(60) / 1000.0  # Targeting 60 FPS

            # Handle events (e.g., window close)
            if self.render_window.handle_events():
                if stats_queue:
                    stats_queue.put(('stopped_by_user', True))
                self.running = False
                break

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            self.render_planar_views()
            self.render_scene(delta_time)

            # Collect FPS data
            current_fps = self.render_window.clock.get_fps()
            if stats_queue:
                stats_queue.put(('fps', current_fps))

            self.render_window.draw_fps(current_fps)

            # Update the display
            self.render_window.display_flip()

            # Sleep briefly to prevent high CPU usage
            time.sleep(0.001)

        self.shutdown()

    def render_planar_views(self):
        for renderer_name, _ in self.render_order:
            renderer = self.scene_construct.renderers[renderer_name]
            if renderer.planar_camera:
                renderer.render_planar_view(self.scene_construct.renderers.values())

    def render_scene(self, delta_time):
        for renderer_name, _ in self.render_order:
            renderer = self.scene_construct.renderers[renderer_name]
            renderer.update_camera(delta_time)
            self.scene_construct.render(renderer_name)

    def shutdown(self):
        """Shut down the rendering instance and clean up resources."""
        self.running = False  # Stop the main loop

        # First, shut down the renderers while the OpenGL context is still valid
        for renderer in self.scene_construct.renderers.values():
            renderer.shutdown()

        # Clean up OpenGL resources if needed
        for framebuffer, texture in self.framebuffers.values():
            glDeleteFramebuffers(1, [framebuffer])
            glDeleteTextures(1, [texture])
        self.framebuffers.clear()

        # Finally, shut down the render window (this destroys the OpenGL context)
        if self.render_window:
            self.render_window.shutdown()
