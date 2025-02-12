# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import glm


# ------------------------------------------------------------------------------
# CameraController Class
# ------------------------------------------------------------------------------
class CameraController:
    """
    CameraController manages smooth transitions between a series of camera positions.

    It interpolates between positions (x, y, z) and rotations (yaw, pitch) based on
    time, and supports optional lens rotation interpolation.
    """

    def __init__(self, camera_positions, lens_rotations=None, move_speed=1.0, loop=True):
        """
        Initialize the camera controller.

        Args:
            camera_positions (list): List of tuples (x, y, z, yaw, pitch).
            lens_rotations (list or float): List of lens rotation values or a single value.
            move_speed (float): Speed factor for camera movement.
            loop (bool): Whether to loop camera positions.
        """
        # Ensure camera_positions follow the (x, y, z, yaw, pitch) format
        self.camera_positions = [(*pos[:3], pos[3], pos[4]) for pos in camera_positions]

        # Ensure lens_rotations is a list
        self.lens_rotations = self.ensure_list(lens_rotations, default=0.0)

        self.move_speed = move_speed
        self.loop = loop
        self.current_position_index = 0
        self.next_position_index = 1 if len(self.camera_positions) > 1 else 0
        self.t = 0.0
        self.current_lens_rotation_index = 0
        self.next_lens_rotation_index = 1 if len(self.lens_rotations) > 1 else 0

    # --------------------------------------------------------------------------
    # Utility Methods
    # --------------------------------------------------------------------------
    def ensure_list(self, value, default=0.0):
        """
        Ensure that the provided value is a list.

        If a single number is provided, wrap it in a list. If None, return a list with the default.
        """
        if isinstance(value, (float, int)):
            return [value]
        elif value is None:
            return [default]
        return value

    # --------------------------------------------------------------------------
    # Update and Interpolation Methods
    # --------------------------------------------------------------------------
    def update(self, delta_time):
        """
        Update camera position and rotation based on the elapsed time.

        Args:
            delta_time (float): Time elapsed since the last update.

        Returns:
            Tuple: Interpolated position (glm.vec3) and rotation (glm.vec2).
        """
        self.t += self.move_speed * delta_time
        if self.t > 1.0:
            self.t = 0.0
            self.current_position_index = self.next_position_index
            self.next_position_index = (self.next_position_index + 1) % len(self.camera_positions)
            self.current_lens_rotation_index = self.next_lens_rotation_index
            self.next_lens_rotation_index = (self.next_lens_rotation_index + 1) % len(self.lens_rotations)

        interpolated_position = self.interpolate_positions()
        interpolated_rotation = self.interpolate_rotations()
        return interpolated_position, interpolated_rotation

    def interpolate_positions(self):
        """
        Interpolate between the current and next camera positions.

        Returns:
            glm.vec3: Interpolated position.
        """
        current_pos = glm.vec3(*self.camera_positions[self.current_position_index][:3])
        next_pos = glm.vec3(*self.camera_positions[self.next_position_index][:3])
        return glm.mix(current_pos, next_pos, self.t)

    def interpolate_rotations(self):
        """
        Interpolate between the current and next camera rotations (yaw, pitch).

        Returns:
            glm.vec2: Interpolated rotation.
        """
        current_rotation = glm.vec2(
            self.camera_positions[self.current_position_index][3],
            self.camera_positions[self.current_position_index][4],
        )
        next_rotation = glm.vec2(
            self.camera_positions[self.next_position_index][3],
            self.camera_positions[self.next_position_index][4],
        )
        return glm.mix(current_rotation, next_rotation, self.t)

    def get_current_lens_rotation(self):
        """
        Interpolate the lens rotation between the current and next values.

        Returns:
            float: Interpolated lens rotation.
        """
        current_rotation = self.lens_rotations[self.current_lens_rotation_index]
        next_rotation = self.lens_rotations[self.next_lens_rotation_index]
        return self.linear_interpolate(current_rotation, next_rotation)

    def linear_interpolate(self, start, end):
        """
        Perform a simple linear interpolation.

        Args:
            start (float): Starting value.
            end (float): Ending value.

        Returns:
            float: Interpolated value.
        """
        return start * (1.0 - self.t) + end * self.t
