#version 430 core

// Define the particle structure
struct Particle {
    vec3 position;
    vec3 velocity;
    float spawnTime;
    float lifetime;
    float particleID;
    float lifetimePercentage;
};

// Bind the particle buffer as a shader storage buffer
layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

// Specify workgroup size (adjust based on GPU capabilities)
layout(local_size_x = 128) in;

// Uniforms for time and other parameters
uniform float currentTime;
uniform float deltaTime;
uniform float particleMaxLifetime;
uniform vec3 particleGravity;
uniform float particleMaxVelocity;
uniform float particleBounceFactor;
uniform vec3 particleGroundPlaneNormal;
uniform float particleGroundPlaneHeight;
uniform float width;
uniform float height;
uniform float depth;
uniform int maxParticles;
uniform int particleBatchSize;
uniform bool particleGenerator;

// Optional fluid simulation parameters
uniform float particlePressure;
uniform float particleViscosity;
uniform bool fluidSimulation;

// Shared variable for counting active particles
shared uint activeParticlesCount;

// Function to generate random values based on particle ID
float random(float seed, float time) {
    return fract(sin(seed + float(gl_GlobalInvocationID.x) * 12.9898 + time * 78.233) * 43758.5453123);
}

// Function to calculate fluid forces (simple pressure and viscosity model)
vec3 calculateFluidForces(vec3 velocity) {
    vec3 pressureForce = -normalize(velocity) * particlePressure;
    vec3 viscosityForce = -velocity * particleViscosity;
    return pressureForce + viscosityForce;
}

// Main compute shader function
void main() {
    uint index = gl_GlobalInvocationID.x;

    if (index >= maxParticles) return;// Avoid updating more particles than allowed

    // Initialize the shared counter to 0 only once per workgroup
    if (gl_LocalInvocationID.x == 0) {
        activeParticlesCount = 0;
    }

    // Synchronize to ensure all threads see the initialized value
    barrier();

    Particle particle = particles[index];

    // Check if the particle has expired (lifetimePercentage >= 1.0)
    bool isExpired = particle.lifetimePercentage >= 1.0;

    // Count active particles
    if (particle.lifetimePercentage < 1.0) {
        atomicAdd(activeParticlesCount, 1);
    }

    // Synchronize to ensure all threads have updated the counter
    barrier();

    // Only generate new particles if there is space available
    if (isExpired && particleGenerator) {
        float randSeed = particle.particleID * 0.1;

        // Update particleID to make it unique
        particle.particleID += 1.0;

        // Set random initial position within the bounds (width, height, depth)
        particle.position.x = (random(randSeed, currentTime) * 2.0 - 1.0) * width;
        particle.position.y = (random(randSeed + 1.0, currentTime) * 2.0 - 1.0) * height;
        particle.position.z = (random(randSeed + 2.0, currentTime) * 2.0 - 1.0) * depth;

        // Set random velocity
        particle.velocity.x = (random(randSeed + 3.0, currentTime) * 2.0 - 1.0) * particleMaxVelocity;
        particle.velocity.y = (random(randSeed + 4.0, currentTime) * 2.0 - 1.0) * particleMaxVelocity;
        particle.velocity.z = (random(randSeed + 5.0, currentTime) * 2.0 - 1.0) * particleMaxVelocity;

        // Assign a random lifetime based on the uniform `particleMaxLifetime`
        // Ensure lifetime is not zero
        particle.lifetime = mix(0.1, particleMaxLifetime, random(randSeed + 6.0, currentTime));

        // Initialize the particle's spawn time and reset lifetime percentage
        particle.spawnTime = currentTime;
        particle.lifetimePercentage = 0.0;
    }

    // Process the particles that are currently active
    if (particle.lifetimePercentage < 1.0) {
        // Apply gravity
        particle.velocity += particleGravity * deltaTime;

        // Apply fluid simulation forces if enabled
        if (fluidSimulation) {
            vec3 fluidForces = calculateFluidForces(particle.velocity);
            particle.velocity += fluidForces * deltaTime;
        }

        // Clamp the velocity to the maximum allowed value
        float speed = length(particle.velocity);
        if (speed > particleMaxVelocity) {
            particle.velocity = normalize(particle.velocity) * particleMaxVelocity;
        }

        // Update position based on velocity
        particle.position += particle.velocity * deltaTime;

        // Check for collision with the ground plane
        float distanceToGround = dot(particle.position, particleGroundPlaneNormal) - particleGroundPlaneHeight;
        if (distanceToGround < 0.0) {
            // Reflect the velocity based on the ground plane normal
            particle.velocity = reflect(particle.velocity, particleGroundPlaneNormal) * particleBounceFactor;

            // Clamp the reflected velocity to the maximum allowed value
            speed = length(particle.velocity);
            if (speed > particleMaxVelocity) {
                particle.velocity = normalize(particle.velocity) * particleMaxVelocity;
            }

            // Prevent the particle from penetrating the ground plane
            particle.position -= particleGroundPlaneNormal * distanceToGround;
        }

        // Calculate the elapsed time and update the lifetime percentage
        float elapsedTime = currentTime - particle.spawnTime;
        if (particle.lifetime > 0.0) {
            particle.lifetimePercentage = clamp(elapsedTime / particle.lifetime, 0.0, 1.0);
        } else {
            particle.lifetimePercentage = 1.0;// Expire immediately if lifetime is zero
        }
    }

    // Write the updated particle data back to the buffer
    particles[index] = particle;
}
