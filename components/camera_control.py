import glm


class CameraController:
    def __init__(self, camera_positions, move_speed=1.0, loop=True):
        self.camera_positions = camera_positions
        self.move_speed = move_speed
        self.loop = loop
        self.current_position_index = 0
        self.next_position_index = 1
        self.t = 0.0

    def update(self, delta_time):
        self.t += self.move_speed * delta_time
        if self.t > 1.0:
            self.t = 0.0
            self.current_position_index = self.next_position_index
            self.next_position_index = (self.next_position_index + 1) % len(self.camera_positions)

        current_position = glm.vec3(*self.camera_positions[self.current_position_index])
        next_position = glm.vec3(*self.camera_positions[self.next_position_index])
        interpolated_position = glm.mix(current_position, next_position, self.t)

        return interpolated_position

    def get_current_target(self):
        # Assuming target is always (0, 0, 0) for simplicity, this can be extended
        return glm.vec3(0, 0, 0)
