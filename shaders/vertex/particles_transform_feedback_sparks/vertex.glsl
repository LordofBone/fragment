#version 430

layout (location = 0) in vec3 position;// Input particle position
layout (location = 1) in vec3 velocity;// Input particle velocity

uniform float deltaTime;// Time elapsed between frames
uniform vec3 particleGravity;// Gravity vector applied to the particles
uniform float particleBounceFactor;// How much velocity is preserved upon bouncing
uniform vec3 particleGroundPlaneNormal;// Normal vector of the ground plane
uniform float particleGroundPlaneHeight;// Height of the ground plane
uniform float particleMaxVelocity;// Maximum allowed velocity for particles
uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Color of the particle
uniform float particleMaxLifetime;// Maximum lifetime of particles (in seconds)

out float particleLifetime;// Particle's current lifetime (0.0 to 1.0)
out vec3 fragColor;// Output color to the fragment shader

// Output variables for transform feedback
out vec3 tfPosition;
out vec3 tfVelocity;

void main() {
    // Update velocity with gravity
    vec3 newVelocity = velocity + particleGravity * deltaTime;

    // Clamp the velocity to the maximum allowed value
    float speed = length(newVelocity);
    if (speed > particleMaxVelocity) {
        newVelocity = normalize(newVelocity) * particleMaxVelocity;
    }

    // Update position based on the clamped velocity
    vec3 newPosition = position + newVelocity * deltaTime;

    // Check for collision with the ground plane
    float distanceToGround = dot(newPosition, particleGroundPlaneNormal) - particleGroundPlaneHeight;
    if (distanceToGround < 0.0) {
        // Reflect the velocity based on the ground plane normal
        newVelocity = reflect(newVelocity, particleGroundPlaneNormal) * particleBounceFactor;

        // Clamp the reflected velocity to the maximum allowed value
        speed = length(newVelocity);
        if (speed > particleMaxVelocity) {
            newVelocity = normalize(newVelocity) * particleMaxVelocity;
        }

        // Prevent the particle from penetrating the ground plane
        newPosition -= particleGroundPlaneNormal * distanceToGround;
    }

    // Output the updated position and velocity for transform feedback
    tfPosition = newPosition;
    tfVelocity = newVelocity;

    // Calculate the particle's current lifetime (0.0 to 1.0)
    particleLifetime = clamp(gl_InstanceID * deltaTime / particleMaxLifetime, 0.0, 10.0);

    // Set the final position of the particle
    gl_Position = vec4(newPosition, 1.0);

    // Set the point size (adjust based on your needs)
    gl_PointSize = particleSize;

    // Pass the color to the fragment shader (you can modify this for effects)
    fragColor = particleColor;
}
