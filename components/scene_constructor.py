from components.abstract_renderer import AbstractRenderer


class SceneConstructor:
    def __init__(self):
        self.renderers = {}

    def add_renderer(self, name: str, renderer: AbstractRenderer):
        """Add a renderer to the scene with a specific name."""
        self.renderers[name] = renderer

    def render(self, name=None):
        """Render all objects in the scene, or a specific renderer if name is provided."""
        if name:
            self.renderers[name].render()
        else:
            for renderer in self.renderers.values():
                renderer.render()

    def translate_renderer(self, name, position):
        """Translate a renderer in the scene."""
        if name in self.renderers:
            self.renderers[name].translate(position)

    def rotate_renderer(self, name, angle, axis):
        """Rotate a renderer in the scene."""
        if name in self.renderers:
            self.renderers[name].rotate(angle, axis)

    def scale_renderer(self, name, scale):
        """Scale a renderer in the scene."""
        if name in self.renderers:
            self.renderers[name].scale(scale)

    def set_auto_rotation(self, name, enabled):
        """Enable or disable auto-rotation for a renderer."""
        if name in self.renderers:
            self.renderers[name].enable_auto_rotation(enabled)
