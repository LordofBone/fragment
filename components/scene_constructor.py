from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer


class SceneConstructor:
    def __init__(self):
        self.renderers = []

    def add_renderer(self, renderer: AbstractRenderer):
        self.renderers.append(renderer)

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        for renderer in self.renderers:
            renderer.render()

    def setup(self):
        for renderer in self.renderers:
            renderer.setup()

    def translate_renderer(self, index, position):
        if index < len(self.renderers):
            self.renderers[index].translate(position)

    def rotate_renderer(self, index, angle, axis):
        if index < len(self.renderers):
            self.renderers[index].rotate(angle, axis)

    def scale_renderer(self, index, scale):
        if index < len(self.renderers):
            self.renderers[index].scale(scale)

    def set_auto_rotation(self, index, enabled):
        if index < len(self.renderers):
            self.renderers[index].enable_auto_rotation(enabled)
