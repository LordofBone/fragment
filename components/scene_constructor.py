from components.abstract_renderer import AbstractRenderer


class SceneConstructor:
    """
    SceneConstructor manages a collection of renderers within a scene.

    It provides methods to add new renderers, apply transformations
    (translate, rotate, scale, etc.), and render either all or a specific renderer.
    """
    def __init__(self):
        """
        Initialize the scene with an empty dictionary of named renderers.
        """
        self.renderers = {}

    # --------------------------------------------------------------------------
    # Registration / Addition
    # --------------------------------------------------------------------------
    def add_renderer(self, name: str, renderer: AbstractRenderer):
        """
        Add a renderer to the scene under the specified name.

        Args:
            name (str): Identifier for the renderer.
            renderer (AbstractRenderer): An instance of a renderer subclass.
        """
        self.renderers[name] = renderer

    # --------------------------------------------------------------------------
    # Rendering
    # --------------------------------------------------------------------------
    def render(self, name=None):
        """
        Render either a specific renderer (by name) or all renderers in the scene.

        Args:
            name (str, optional): If provided, only render the named renderer.
        """
        if name:
            self.renderers[name].render()
        else:
            self._apply_to_all_renderers(lambda r: r.render())

    # --------------------------------------------------------------------------
    # Transforms & Auto-Rotation
    # --------------------------------------------------------------------------
    def translate_renderer(self, name, position):
        """
        Translate the named renderer by the specified (x,y,z) position.

        Args:
            name (str): Name of the renderer.
            position (tuple): (x, y, z) translation vector.
        """
        self._apply_to_renderer(name, lambda r: r.translate(position))

    def rotate_renderer(self, name, angle, axis):
        """
        Rotate the named renderer by 'angle' (in degrees) around a single axis (x,y,z).

        Note: This approach can cause issues with certain surface/shadow calculations
              (rotation is about a single axis).
        """
        self._apply_to_renderer(name, lambda r: r.rotate(angle, axis))

    def rotate_renderer_euler(self, name, angles):
        """
        Rotate the named renderer by Euler angles (xDeg, yDeg, zDeg).

        This effectively overwrites previous single-axis rotate() calls.

        Args:
            name (str): Renderer name.
            angles (tuple): (xDeg, yDeg, zDeg).
        """
        def do_rotation(r):
            r.rotate_euler(angles)
        self._apply_to_renderer(name, do_rotation)

    def scale_renderer(self, name, scale):
        """
        Uniformly scale the named renderer by (xScale, yScale, zScale).

        Args:
            name (str): Renderer name.
            scale (tuple): Scale factors (x, y, z).
        """
        self._apply_to_renderer(name, lambda r: r.scale(scale))

    def set_auto_rotation(self, name, enabled=False, axis=None, speed=None):
        """
        Enable or disable auto-rotation for the named renderer.

        Args:
            name (str): Renderer name.
            enabled (bool): Enable/disable auto-rotation.
            axis (tuple): Rotation axis (x, y, z).
            speed (float): Speed factor for the rotation.
        """
        def do_autorot(r):
            r.enable_auto_rotation(enabled, axis=axis, speed=speed)
        self._apply_to_renderer(name, do_autorot)

    def set_auto_rotations(self, name, rotations):
        """
        Enable auto-rotation for the named renderer with multiple rotations,
        each defined by (axis, speed).

        Args:
            name (str): Renderer name.
            rotations (list of tuples): e.g. [((0,1,0), 4000.0), ((1,0,0), 2000.0)].
        """
        self._apply_to_renderer(name, lambda r: r.enable_auto_rotation(rotations=rotations))

    # --------------------------------------------------------------------------
    # Private Utility Methods
    # --------------------------------------------------------------------------
    def _apply_to_renderer(self, name, action):
        """
        Apply a given function (action) to the named renderer if it exists.
        """
        if name in self.renderers:
            action(self.renderers[name])

    def _apply_to_all_renderers(self, action):
        """
        Apply a given function (action) to every renderer in the scene.
        """
        for renderer in self.renderers.values():
            action(renderer)
