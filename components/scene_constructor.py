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
            self._apply_to_all_renderers(lambda r: r.render())

    def translate_renderer(self, name, position):
        """Translate a renderer in the scene."""
        self._apply_to_renderer(name, lambda r: r.translate(position))

    def rotate_renderer(self, name, angle, axis):
        """Rotate a renderer in the scene."""
        self._apply_to_renderer(name, lambda r: r.rotate(angle, axis))

    def scale_renderer(self, name, scale):
        """Scale a renderer in the scene."""
        self._apply_to_renderer(name, lambda r: r.scale(scale))

    def set_auto_rotation(self, name, enabled):
        """Enable or disable auto-rotation for a renderer."""
        self._apply_to_renderer(name, lambda r: r.enable_auto_rotation(enabled))

    def _apply_to_renderer(self, name, action):
        """Apply an action to a renderer if it exists."""
        if name in self.renderers:
            action(self.renderers[name])

    def _apply_to_all_renderers(self, action):
        """Apply an action to all renderers."""
        for renderer in self.renderers.values():
            action(renderer)
