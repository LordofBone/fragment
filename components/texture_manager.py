import numpy as np
from OpenGL.GL import *

from utils.decorators import singleton


@singleton
class TextureManager:
    def __init__(self):
        self.reset()

    def get_texture_unit(self, identifier, texture_type):
        """
        Get a unique texture unit for a specific texture type and object instance.

        Parameters:
            identifier (str): Unique identifier for the object instance.
            texture_type (str): Type of the texture (e.g., 'diffuse', 'normal', 'displacement', etc.).

        Returns:
            int: The assigned texture unit.
        """
        key = (identifier, texture_type)
        return self.texture_unit_map.setdefault(key, self._assign_new_texture_unit())

    def _assign_new_texture_unit(self):
        """Assign a new texture unit."""
        texture_unit = self.current_texture_unit
        self.current_texture_unit += 1
        return texture_unit

    def get_dummy_texture(self):
        if self.dummy_texture is None:
            self.dummy_texture = self.create_dummy_texture()
        return self.dummy_texture

    def create_dummy_texture(self):
        dummy_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, dummy_texture)
        data = np.array([1.0], dtype=np.float32)  # White color for depth value of 1.0
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, 1, 1, 0, GL_DEPTH_COMPONENT, GL_FLOAT, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)
        return dummy_texture

    def reset(self):
        """Resets the texture manager, clearing all stored texture units."""
        self.current_texture_unit = 0
        self.texture_unit_map = {}
        self.dummy_texture = None
