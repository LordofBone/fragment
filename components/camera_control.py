import glm


class CameraController:
    def __init__(self, camera_positions, lens_rotations=None, move_speed=1.0, loop=True):
        # Ensure camera_positions is a list of tuples (x, y, z, rotation_x, rotation_y)
        self.camera_positions = [(*pos[:3], pos[3], pos[4]) for pos in camera_positions]

        # Ensure lens_rotations is a list, even if a single float is passed
        self.lens_rotations = self.ensure_list(lens_rotations, default=0.0)

        self.move_speed = move_speed
        self.loop = loop
        self.current_position_index = 0
        self.next_position_index = 1 if len(camera_positions) > 1 else 0
        self.t = 0.0
        self.current_lens_rotation_index = 0
        self.next_lens_rotation_index = 1 if len(self.lens_rotations) > 1 else 0

    def ensure_list(self, value, default=0.0):
        """Ensure that a value is a list, converting if necessary."""
        if isinstance(value, (float, int)):
            return [value]
        elif value is None:
            return [default]
        return value

    def update(self, delta_time):
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
        """Interpolate between current and next camera positions."""
        current_pos = glm.vec3(*self.camera_positions[self.current_position_index][:3])
        next_pos = glm.vec3(*self.camera_positions[self.next_position_index][:3])
        return glm.mix(current_pos, next_pos, self.t)

    def interpolate_rotations(self):
        """Interpolate between current and next camera rotations."""
        current_rotation = glm.vec2(
            self.camera_positions[self.current_position_index][4],
            self.camera_positions[self.current_position_index][3],
        )
        next_rotation = glm.vec2(
            self.camera_positions[self.next_position_index][4],
            self.camera_positions[self.next_position_index][3],
        )
        return glm.mix(current_rotation, next_rotation, self.t)

    def get_current_target(self):
        # Assuming target is always (0, 0, 0) for simplicity, this can be extended
        return glm.vec3(0, 0, 0)

    def get_current_lens_rotation(self):
        # Interpolate between the current and next lens rotation using linear interpolation
        current_rotation = self.lens_rotations[self.current_lens_rotation_index]
        next_rotation = self.lens_rotations[self.next_lens_rotation_index]
        return self.linear_interpolate(current_rotation, next_rotation)

    def linear_interpolate(self, start, end):
        """Simple linear interpolation between start and end."""
        return start * (1.0 - self.t) + end * self.t
