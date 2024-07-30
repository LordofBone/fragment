from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer


class Scene:
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
