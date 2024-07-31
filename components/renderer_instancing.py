from components.model_renderer import ModelRenderer
from components.renderer_window import RendererWindow
from components.scene import Scene
from components.surface_renderer import SurfaceRenderer


class RenderingInstance:
    def __init__(self, config):
        self.config = config
        self.render_window = None
        self.scene = Scene()

    def setup(self):
        self.render_window = RendererWindow(window_size=self.config.window_size, title="Renderer",
                                            msaa_level=self.config.msaa_level)

    def add_renderer(self, renderer_type, **params):
        if renderer_type == 'model':
            renderer = ModelRenderer(**params)
        elif renderer_type == 'surface':
            renderer = SurfaceRenderer(**params)
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")
        self.scene.add_renderer(renderer)

    def run(self):
        for renderer in self.scene.renderers:
            renderer.setup()

        def render_callback():
            self.scene.render()

        self.render_window.mainloop(render_callback)
