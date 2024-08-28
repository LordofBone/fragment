from utils.decorators import singleton


@singleton
class TextureManager:
    def __init__(self):
        # Initialize the texture unit management
        self.current_texture_unit = 0
        self.texture_unit_map = {}

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
        if key not in self.texture_unit_map:
            # Assign a new texture unit and increment the counter
            self.texture_unit_map[key] = self.current_texture_unit
            self.current_texture_unit += 1
        return self.texture_unit_map[key]

    def reset(self):
        """
        Resets the texture manager, clearing all stored texture units.
        """
        self.current_texture_unit = 0
        self.texture_unit_map.clear()
