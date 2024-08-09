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

    def setup(self):
        """Setup the rendering window."""
        self.render_window = RendererWindow(window_size=self.config.window_size, title="Renderer",
                                            msaa_level=self.config.msaa_level)

    def add_renderer(self, renderer_type, **params):
        """Add a renderer to the instance."""
        if renderer_type == 'model':
            renderer = ModelRenderer(**params)
        elif renderer_type == 'surface':
            renderer = SurfaceRenderer(**params)
        elif renderer_type == 'skybox':
            renderer = SkyboxRenderer(**params)
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")
        self.scene_construct.add_renderer(renderer)

    def run(self):
        """Run the rendering loop."""
        for renderer in self.scene_construct.renderers:
            renderer.setup()

        def render_callback(delta_time):
            for renderer in self.scene_construct.renderers:
                renderer.update_camera(delta_time)
            self.scene_construct.render()

        self.render_window.mainloop(render_callback)
