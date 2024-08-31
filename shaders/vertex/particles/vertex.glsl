#version 430

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 velocity;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 fragColor;

void main() {
    // Calculate the final position of the particle in world space
    vec4 worldPosition = model * vec4(position, 1.0);

    // Pass the position to the next stage (for fragment shader)
    gl_Position = projection * view * worldPosition;

    // Set the color based on the velocity (for visual effect)
    fragColor = normalize(velocity) * 0.5 + 0.5;
}
