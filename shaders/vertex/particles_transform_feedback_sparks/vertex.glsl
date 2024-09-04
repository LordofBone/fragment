#version 430

layout (location = 0) in vec3 position;// Input particle position
layout (location = 1) in vec3 velocity;// Input particle velocity

uniform float deltaTime;// Time elapsed between frames
uniform vec3 gravity;// Gravity vector applied to the particles
uniform float bounceFactor;// How much velocity is preserved upon bouncing
uniform vec3 groundPlaneNormal;// Normal vector of the ground plane
uniform float groundPlaneHeight;// Height of the ground plane
uniform float maxVelocity;// Maximum allowed velocity for particles
uniform float particleSize;// Maximum allowed velocity for particles

out vec3 fragColor;// Output color to the fragment shader

// Output variables for transform feedback
out vec3 tf_position;
out vec3 tf_velocity;

void main() {
    // Update velocity with gravity
    vec3 newVelocity = velocity + gravity * deltaTime;

    // Clamp the velocity to the maximum allowed value
    float speed = length(newVelocity);
    if (speed > maxVelocity) {
        newVelocity = normalize(newVelocity) * maxVelocity;
    }

    // Update position based on the clamped velocity
    vec3 newPosition = position + newVelocity * deltaTime;

    // Check for collision with the ground plane
    float distanceToGround = dot(newPosition, groundPlaneNormal) - groundPlaneHeight;
    if (distanceToGround < 0.0) {
        // Reflect the velocity based on the ground plane normal
        newVelocity = reflect(newVelocity, groundPlaneNormal) * bounceFactor;

        // Clamp the reflected velocity to the maximum allowed value
        speed = length(newVelocity);
        if (speed > maxVelocity) {
            newVelocity = normalize(newVelocity) * maxVelocity;
        }

        // Prevent the particle from penetrating the ground plane
        newPosition -= groundPlaneNormal * distanceToGround;
    }

    // Output the updated position and velocity for transform feedback
    tf_position = newPosition;
    tf_velocity = newVelocity;

    // Pass the color to the fragment shader (you can modify this for effects)
    fragColor = vec3(1.0, 0.8, 0.2);// A spark-like yellow/orange color

    // Set the final position of the particle
    gl_Position = vec4(newPosition, 1.0);

    // Set the point size (adjust based on your needs)
    gl_PointSize = particleSize;
}
