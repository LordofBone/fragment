from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer


class SceneConstructor:
    def __init__(self):
        self.renderers = []

    def add_renderer(self, renderer: AbstractRenderer):
        """Add a renderer to the scene."""
        self.renderers.append(renderer)

    def render(self):
        """Render all objects in the scene."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        for renderer in self.renderers:
            renderer.render()

    def translate_renderer(self, index, position):
        """Translate a renderer in the scene."""
        if index < len(self.renderers):
            self.renderers[index].translate(position)

    def rotate_renderer(self, index, angle, axis):
        """Rotate a renderer in the scene."""
        if index < len(self.renderers):
            self.renderers[index].rotate(angle, axis)

    def scale_renderer(self, index, scale):
        """Scale a renderer in the scene."""
        if index < len(self.renderers):
            self.renderers[index].scale(scale)

    def set_auto_rotation(self, index, enabled):
        """Enable or disable auto-rotation for a renderer."""
        if index < len(self.renderers):
            self.renderers[index].enable_auto_rotation(enabled)
