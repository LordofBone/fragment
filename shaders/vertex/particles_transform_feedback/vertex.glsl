#version 430
#include "common_funcs.glsl"

layout (location = 0) in vec4 position;// Input particle position (x, y, z, w)
layout (location = 1) in vec4 velocity;// Input particle velocity (x, y, z, w)
layout (location = 2) in float spawnTime;// Time when the particle was created
layout (location = 3) in float particleLifetime;// The lifetime of the particle (0.0 means no expiration)
layout (location = 4) in float particleID;// The ID of the particle
layout (location = 5) in float particleWeight;// The weight of the particle
layout (location = 6) in float lifetimePercentage;// The percentage of the particle's lifetime

uniform float currentTime;// The global time for tracking particle lifetime
uniform float deltaTime;// Time elapsed between frames
uniform vec3 particleGravity;// Gravity vector applied to the particles
uniform float particleBounceFactor;// How much velocity is preserved upon bouncing
uniform vec3 particleGroundPlaneNormal;// Normal vector of the ground plane
uniform float particleGroundPlaneHeight;// Height of the ground plane
uniform float particleMaxVelocity;// Maximum allowed velocity for particles
uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle
uniform bool fluidSimulation;// Flag to enable fluid simulation

// Camera uniforms for view and projection matrices
uniform mat4 view;// View matrix
uniform mat4 projection;// Projection matrix
uniform vec3 cameraPosition;// Position of the camera in world space
uniform mat4 model;// Model matrix

// Output variables for transform feedback
out vec4 tfPosition;
out vec4 tfVelocity;
out float tfSpawnTime;
out float tfParticleLifetime;
out float tfParticleID;
out float tfLifetimePercentage;
out float tfParticleWeight;
out float lifetimePercentageToFragment;// For fragment shader

out vec3 fragColor;// Output color to the fragment shader
flat out float particleIDOut;// Pass the particle ID to the fragment shader
out vec3 fragPos;// Particle's position in world space

void main() {
    // Initialize outputs
    tfSpawnTime = spawnTime;
    tfParticleLifetime = particleLifetime;
    tfParticleID = particleID;
    tfParticleWeight = particleWeight;
    fragColor = particleColor;
    particleIDOut = particleID;

    // Calculate elapsed time and lifetime percentage
    float elapsedTime = currentTime - spawnTime;
    float calculatedLifetimePercentage = 0.0;

    if (particleLifetime > 0.0) {
        calculatedLifetimePercentage = clamp(elapsedTime / particleLifetime, 0.0, 1.0);
    }

    tfLifetimePercentage = calculatedLifetimePercentage;
    lifetimePercentageToFragment = calculatedLifetimePercentage;

    // If the particle has expired, set outputs accordingly and return
    if (tfLifetimePercentage >= 1.0 || lifetimePercentage >= 1.0) {
        tfPosition = position;
        tfVelocity = velocity;
        gl_PointSize = 0.0;
        gl_Position = vec4(0.0);
        tfLifetimePercentage = 1.0;
        lifetimePercentageToFragment = 1.0;
        tfParticleID = particleID;
        particleIDOut = particleID;
        fragPos = (model * position).xyz;
        return;
    }

    // Apply gravity scaled by weight
    vec3 adjustedGravity = particleGravity * particleWeight;
    vec3 newVelocity = velocity.xyz + adjustedGravity * deltaTime;

    // Conditionally apply fluid simulation forces
    if (fluidSimulation) {
        vec3 fluidForces = calculateFluidForces(velocity.xyz);
        newVelocity += fluidForces * deltaTime;
    }

    // Clamp the velocity to the maximum allowed value
    float speed = length(newVelocity);
    if (speed > particleMaxVelocity) {
        newVelocity = normalize(newVelocity) * particleMaxVelocity;
    }

    // Update position based on the clamped velocity
    vec3 newPosition = position.xyz + newVelocity * deltaTime;

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

    // Adjust particle size based on distance from the camera
    vec3 particleToCamera = cameraPosition - newPosition;
    float distanceFromCamera = length(particleToCamera);
    float adjustedSize = particleSize / distanceFromCamera;

    // Set particle size for rendering
    gl_PointSize = adjustedSize;

    // Output the updated position and velocity for transform feedback
    tfPosition = vec4(newPosition, 1.0);
    tfVelocity = vec4(newVelocity, 0.0);

    // Set the final position of the particle using view and projection matrices
    vec4 worldPosition = model * vec4(newPosition, 1.0);
    gl_Position = projection * view * worldPosition;

    // Pass the fragment position in world space
    fragPos = worldPosition.xyz;
}
