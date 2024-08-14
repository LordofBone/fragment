from OpenGL.GL import *

from components.model_renderer import ModelRenderer
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
        self.render_order = []  # Initialize render_order as an empty list

    def setup(self):
        """Setup the rendering window."""
        self.render_window = RendererWindow(
            window_size=self.config.window_size, title="Renderer", msaa_level=self.config.msaa_level
        )

        # Ensure renderers are added before initializing framebuffers
        for renderer_name, renderer in self.scene_construct.renderers.items():
            renderer.setup()

        # Initialize framebuffers after all renderers have been added
        self.initialize_framebuffers(self.config.window_size[0], self.config.window_size[1])

    def initialize_framebuffers(self, width, height):
        """Initialize all framebuffers."""
        for renderer_name in self.scene_construct.renderers:
            framebuffer, texture = self.create_framebuffer(width, height)
            self.framebuffers[renderer_name] = (framebuffer, texture)

    def create_framebuffer(self, width, height):
        """Create a framebuffer object with attached texture and depth buffer."""
        framebuffer = glGenFramebuffers(1)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindFramebuffer(GL_FRAMEBUFFER, framebuffer)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0)

        rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, rbo)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Framebuffer is not complete")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        return framebuffer, texture

    def add_renderer(self, name, renderer_type, order=None, **params):
        """Add a renderer to the instance with a specific name."""
        if renderer_type == "model":
            renderer = ModelRenderer(**params)
        elif renderer_type == "surface":
            renderer = SurfaceRenderer(**params)
        elif renderer_type == "skybox":
            renderer = SkyboxRenderer(**params)
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")

        self.scene_construct.add_renderer(name, renderer)

        # Set default order if none is provided
        if order is None:
            order = len(self.render_order)

        self.render_order.append((name, order))
        self.render_order.sort(key=lambda x: x[1], reverse=True)

    def run(self):
        """Run the rendering loop."""
        self.setup()  # Ensures that setup is called before running

        def render_callback(delta_time):
            for renderer_name, _ in self.render_order:
                framebuffer, _ = self.framebuffers[renderer_name]
                glBindFramebuffer(GL_FRAMEBUFFER, framebuffer)
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                self.scene_construct.render(renderer_name)
                glBindFramebuffer(GL_FRAMEBUFFER, 0)

            # Render the final pass with transparency and distortion
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            for renderer_name, _ in self.render_order:
                _, texture = self.framebuffers[renderer_name]
                glBindTexture(GL_TEXTURE_2D, texture)
                self.scene_construct.render(renderer_name)

        self.render_window.mainloop(render_callback)
