import glm


class CameraController:
    def __init__(self, camera_positions, lens_rotations=None, move_speed=1.0, loop=True):
        self.camera_positions = camera_positions

        # Ensure lens_rotations is a list, even if a single float is passed
        if isinstance(lens_rotations, float) or isinstance(lens_rotations, int):
            lens_rotations = [lens_rotations]
        elif lens_rotations is None:
            lens_rotations = [0.0]  # Default to no rotation if none provided

        self.lens_rotations = lens_rotations
        self.move_speed = move_speed
        self.loop = loop
        self.current_position_index = 0
        self.next_position_index = 1 if len(camera_positions) > 1 else 0
        self.t = 0.0
        self.current_lens_rotation_index = 0
        self.next_lens_rotation_index = 1 if len(self.lens_rotations) > 1 else 0

    def update(self, delta_time):
        self.t += self.move_speed * delta_time
        if self.t > 1.0:
            self.t = 0.0
            self.current_position_index = self.next_position_index
            self.next_position_index = (self.next_position_index + 1) % len(self.camera_positions)
            self.current_lens_rotation_index = self.next_lens_rotation_index
            self.next_lens_rotation_index = (self.next_lens_rotation_index + 1) % len(self.lens_rotations)

        current_position = glm.vec3(*self.camera_positions[self.current_position_index])
        next_position = glm.vec3(*self.camera_positions[self.next_position_index])
        interpolated_position = glm.mix(current_position, next_position, self.t)

        return interpolated_position

    def get_current_target(self):
        # Assuming target is always (0, 0, 0) for simplicity, this can be extended
        return glm.vec3(0, 0, 0)

    def get_current_lens_rotation(self):
        # Interpolate between the current and next lens rotation using linear interpolation
        current_rotation = self.lens_rotations[self.current_lens_rotation_index]
        next_rotation = self.lens_rotations[self.next_lens_rotation_index]

        # Simple linear interpolation
        interpolated_rotation = current_rotation * (1.0 - self.t) + next_rotation * self.t

        return interpolated_rotation
