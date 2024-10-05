#version 430

layout (location = 0) in vec3 position;// Input particle position
layout (location = 1) in vec3 velocity;// Input particle velocity
layout (location = 2) in float spawnTime;// Time when the particle was created
layout (location = 3) in float particleLifetime;// The lifetime of the particle (0.0 means no expiration)
layout (location = 4) in float particleID;// The ID of the particle
layout (location = 5) in float particleWeight;// The weight of the particle

uniform float currentTime;// The global time for tracking particle lifetime
uniform float deltaTime;// Time elapsed between frames
uniform vec3 particleGravity;// Gravity vector applied to the particles
uniform float particleBounceFactor;// How much velocity is preserved upon bouncing
uniform vec3 particleGroundPlaneNormal;// Normal vector of the ground plane
uniform float particleGroundPlaneHeight;// Height of the ground plane
uniform float particleMaxVelocity;// Maximum allowed velocity for particles
uniform float particlePressure;// Pressure force for fluid dynamics
uniform float particleViscosity;// Viscosity force for fluid dynamics
uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle
uniform bool fluidSimulation;// Flag to enable water simulation

// Camera uniforms for view and projection matrices
uniform mat4 view;// View matrix
uniform mat4 projection;// Projection matrix
uniform vec3 cameraPosition;// Position of the camera in world space

// New uniform for model matrix to apply transformations (translation, scaling, rotation)
uniform mat4 model;// Model matrix

// Output variables for transform feedback
out vec3 tfPosition;
out vec3 tfVelocity;
out float tfSpawnTime;
out float tfParticleLifetime;
out float tfParticleID;
out float tfLifetimePercentage;
out float tfParticleWeight;
out float lifetimePercentageToFragment;// For fragment shader

out vec3 fragColor;// Output color to the fragment shader
flat out float particleIDOut;// Pass the particle ID to the fragment shader

// A simple function to simulate the interaction with neighboring particles
vec3 calculateFluidForces(vec3 velocity) {
    // Apply a simple pressure and viscosity model for fluid flow
    vec3 pressureForce = -normalize(velocity) * particlePressure;
    vec3 viscosityForce = -velocity * particleViscosity;
    return pressureForce + viscosityForce;
}

void main() {
    // Adjust gravity by weight (heavier particles are less affected by gravity)
    vec3 adjustedGravity = particleGravity / particleWeight;

    // Apply gravity scaled by weight
    vec3 newVelocity = velocity + adjustedGravity * deltaTime;

    // Conditionally apply fluid simulation forces if the flag is true
    if (fluidSimulation) {
        // Apply fluid forces (pressure and viscosity)
        vec3 fluidForces = calculateFluidForces(velocity);
        newVelocity += fluidForces * deltaTime;
    }

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

    // Calculate the time that has passed since the particle was spawned
    float elapsedTime = currentTime - spawnTime;

    // Calculate lifetime percentage
    if (particleLifetime > 0.0) {
        float calculatedLifetimePercentage = clamp(elapsedTime / particleLifetime, 0.0, 1.0);
        tfLifetimePercentage = calculatedLifetimePercentage;// For transform feedback
        lifetimePercentageToFragment = calculatedLifetimePercentage;// For fragment shader

        // If the particle's lifetime exceeds, it should disappear; moving off-screen and setting size to 0
        if (tfLifetimePercentage >= 1.0) {
            newPosition = vec3(10000.0, 10000.0, 10000.0);
            newVelocity = vec3(0.0);
            gl_PointSize = 0.0;
        }
    } else {
        // If lifetime is 0.0, the particle never expires
        tfLifetimePercentage = 0.0;
        lifetimePercentageToFragment = 0.0;
    }

    tfLifetimePercentage = lifetimePercentageToFragment;// For transform feedback

    // Adjust particle size based on distance from the camera
    vec3 particleToCamera = cameraPosition - newPosition;
    float distanceFromCamera = length(particleToCamera);
    float adjustedSize = particleSize / distanceFromCamera;

    // Set particle size for rendering
    gl_PointSize = adjustedSize;

    // Output the updated position and velocity for transform feedback
    tfPosition = newPosition;
    tfVelocity = newVelocity;

    // Pass the spawn time, lifetime, and particle ID
    tfSpawnTime = spawnTime;
    tfParticleLifetime = particleLifetime;
    tfParticleID = particleID;
    tfParticleWeight = particleWeight;

    // Set the final position of the particle using view and projection matrices
    vec4 worldPosition = model * vec4(newPosition, 1.0);
    gl_Position = projection * view * worldPosition;

    // Pass the color to the fragment shader
    fragColor = particleColor;

    // Pass the particle ID to the fragment shader
    particleIDOut = particleID;
}
