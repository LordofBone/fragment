#version 430

layout (location = 0) in vec3 position;// Input particle position
layout (location = 1) in vec3 velocity;// Input particle velocity
layout (location = 2) in float spawnTime;// Time when the particle was created
layout (location = 3) in float particleLifetime;// The lifetime of the particle
layout (location = 4) in float particleID;// The ID of the particle

uniform float currentTime;// The global time for tracking particle lifetime
uniform float deltaTime;// Time elapsed between frames
uniform vec3 particleGravity;// Gravity vector applied to the particles
uniform float particleBounceFactor;// How much velocity is preserved upon bouncing
uniform vec3 particleGroundPlaneNormal;// Normal vector of the ground plane
uniform float particleGroundPlaneHeight;// Height of the ground plane
uniform float particleMaxVelocity;// Maximum allowed velocity for particles
uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle

// New uniforms for weight
uniform float minWeight;// Minimum weight of particles
uniform float maxWeight;// Maximum weight of particles

// Camera uniforms for view and projection matrices
uniform mat4 view;// View matrix
uniform mat4 projection;// Projection matrix
uniform vec3 cameraPosition;// Position of the camera in world space

// Output variables for transform feedback
out vec3 tfPosition;
out vec3 tfVelocity;
out float tfSpawnTime;
out float tfParticleLifetime;
out float tfParticleID;

out float lifetimePercentage;// Particle's current lifetime percentage
out vec3 fragColor;// Output color to the fragment shader
flat out float particleIDOut;// Pass the particle ID to the fragment shader

void main() {
    // Generate a random weight for this particle
    float weight = mix(minWeight, maxWeight, fract(sin(particleID) * 43758.5453));

    // Adjust gravity by weight (heavier particles are less affected by gravity)
    vec3 adjustedGravity = particleGravity / weight;

    // Apply gravity scaled by weight
    vec3 newVelocity = velocity + adjustedGravity * deltaTime;

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

    // Calculate the percentage of the particle's lifetime that has elapsed
    lifetimePercentage = clamp(elapsedTime / particleLifetime, 0.0, 1.0);

    // If the particle's lifetime exceeds its randomly generated lifetime, it should disappear
    if (lifetimePercentage >= 1.0) {
        newPosition = vec3(10000.0, 10000.0, 10000.0);// Move off-screen
        newVelocity = vec3(0.0);
        gl_PointSize = 0.0;// Make invisible
    }

    // Adjust particle size based on distance from the camera
    vec3 particleToCamera = cameraPosition - newPosition;
    float distanceFromCamera = length(particleToCamera);
    float adjustedSize = particleSize / distanceFromCamera;// Inverse proportional to distance

    // Set particle size for rendering
    gl_PointSize = adjustedSize;

    // Output the updated position and velocity for transform feedback
    tfPosition = newPosition;
    tfVelocity = newVelocity;

    // Pass the spawn time, lifetime, and particle ID
    tfSpawnTime = spawnTime;
    tfParticleLifetime = particleLifetime;
    tfParticleID = particleID;

    // Set the final position of the particle using view and projection matrices
    gl_Position = projection * view * vec4(newPosition, 1.0);

    // Pass the color to the fragment shader
    fragColor = particleColor;

    // Pass the particle ID to the fragment shader
    particleIDOut = particleID;
}
