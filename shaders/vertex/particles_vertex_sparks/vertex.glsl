#version 430

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 velocity;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

uniform float particle_size;
uniform vec3 gravity;
uniform float bounceFactor;
uniform vec3 groundPlaneNormal;
uniform float groundPlaneHeight;

out vec3 fragColor;

void main() {
    vec3 newVelocity = velocity + gravity;
    vec3 newPosition = position + newVelocity;

    // Check for collision with the ground plane
    float distanceToGround = dot(newPosition, groundPlaneNormal) - groundPlaneHeight;
    if (distanceToGround < 0.0) {
        newVelocity = reflect(newVelocity, groundPlaneNormal) * bounceFactor;
        newPosition -= groundPlaneNormal * distanceToGround;
    }

    // Pass the updated position to the next pipeline stage
    gl_Position = projection * view * model * vec4(newPosition, 1.0);

    // Set the color based on the velocity for a visual effect
    fragColor = normalize(newVelocity) * 0.5 + 0.5;

    // Set the size of the particle
    gl_PointSize = particle_size;
}
