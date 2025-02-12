import numpy as np
from OpenGL.GL import *

from utils.decorators import singleton


@singleton
class TextureManager:
    """
    Manages texture units and a dummy texture for various object instances.

    Provides:
      - A mapping from (object identifier, texture type) -> unique texture unit
      - A dummy texture used when no valid texture is available.
    """

    def __init__(self):
        """
        Initialize the TextureManager and reset internal mappings.
        """
        self.reset()

    def reset(self):
        """
        Clear all stored texture units and reset the dummy texture.
        """
        self.current_texture_unit = 0
        self.texture_unit_map = {}
        self.dummy_texture = None

    def get_texture_unit(self, identifier, texture_type):
        """
        Return a unique texture unit for a specific object identifier & texture type.

        Args:
            identifier (str): Unique identifier for the object instance (e.g. renderer).
            texture_type (str): A name for the texture's role (diffuse, normal, etc.).

        Returns:
            int: The assigned (or newly created) texture unit index.
        """
        key = (identifier, texture_type)
        if key not in self.texture_unit_map:
            self.texture_unit_map[key] = self._assign_new_texture_unit()
        return self.texture_unit_map[key]

    def _assign_new_texture_unit(self):
        """
        Assign the next available texture unit to a new (identifier, texture_type) pair.

        Returns:
            int: The next free texture unit index.
        """
        texture_unit = self.current_texture_unit
        self.current_texture_unit += 1
        return texture_unit

    def get_dummy_texture(self):
        """
        Retrieve the dummy texture (a small white depth component texture).
        Create it if it doesn't exist yet.

        Returns:
            int: OpenGL texture handle for the dummy texture.
        """
        if self.dummy_texture is None:
            self.dummy_texture = self.create_dummy_texture()
        return self.dummy_texture

    def create_dummy_texture(self):
        """
        Create a 1x1 depth texture (white) to use when no valid texture is available.

        Returns:
            int: The new texture handle.
        """
        dummy_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, dummy_texture)

        data = np.array([1.0], dtype=np.float32)  # single-pixel float depth=1.0
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, 1, 1, 0, GL_DEPTH_COMPONENT, GL_FLOAT, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)

        return dummy_texture
