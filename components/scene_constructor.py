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
        """
        Rotate a renderer in the scene by 'angle' (degrees) around 'axis' (x,y,z).
        This is the original approach, rotating about a single axis by 'angle' degrees.
        Note: Has issues with rotating surfaces, will cause weird shadow issues.
        """
        self._apply_to_renderer(name, lambda r: r.rotate(angle, axis))

    def rotate_renderer_euler(self, name, angles):
        """
        NEW: Rotate a renderer by (xDeg, yDeg, zDeg) in degrees (Euler angles).
        This sets the local rotation, overwriting previous 'rotate()' calls.

        angles = (xDeg, yDeg, zDeg).
        """

        def do_rotation(r):
            r.rotate_euler(angles)

        self._apply_to_renderer(name, do_rotation)

    def scale_renderer(self, name, scale):
        """Scale a renderer in the scene."""
        self._apply_to_renderer(name, lambda r: r.scale(scale))

    def set_auto_rotation(self, name, enabled=False, axis=None, speed=None):
        """
        Enable or disable auto-rotation for a renderer.
        Optionally set a new rotation axis and speed.
        Example:
            scene_construct.set_auto_rotation("tyre", True, axis=(0,1,0), speed=2000.0)
        """

        def do_autorot(r):
            r.enable_auto_rotation(enabled, axis=axis, speed=speed)

        self._apply_to_renderer(name, do_autorot)

    def set_auto_rotations(self, name, rotations):
        """
        Enable auto-rotation for a renderer by passing a list of (axis, speed) tuples.
        For example, to rotate the model on the y-axis and also spin it on the x-axis:
          scene_construct.set_auto_rotations("tyre", rotations=[((0.0,1.0,0.0), 4000.0), ((1.0,0.0,0.0), 2000.0)])
        """
        self._apply_to_renderer(name, lambda r: r.enable_auto_rotation(rotations=rotations))

    def _apply_to_renderer(self, name, action):
        """Apply an action to a renderer if it exists."""
        if name in self.renderers:
            action(self.renderers[name])

    def _apply_to_all_renderers(self, action):
        """Apply an action to all renderers."""
        for renderer in self.renderers.values():
            action(renderer)
