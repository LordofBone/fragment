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

    def reset(self):
        """Resets the texture manager, clearing all stored texture units."""
        self.current_texture_unit = 0
        self.texture_unit_map = {}
