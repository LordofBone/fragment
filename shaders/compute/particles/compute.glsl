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

// Uniforms for time
uniform float currentTime;
uniform float deltaTime;

// Gravity and other constants (you can pass these as uniforms if you want)
const vec3 gravity = vec3(0.0, -9.81, 0.0);

// Main compute shader function
void main() {
    uint index = gl_GlobalInvocationID.x;

    Particle particle = particles[index];

    // Update only if the particle is active (lifetimePercentage < 1.0)
    if (particle.lifetimePercentage < 1.0) {
        // Update velocity with gravity
        particle.velocity += gravity * deltaTime;

        // Update position
        particle.position += particle.velocity * deltaTime;

        // Update lifetime percentage
        float elapsedTime = currentTime - particle.spawnTime;
        particle.lifetimePercentage = elapsedTime / particle.lifetime;

        // Clamp lifetimePercentage to 1.0
        if (particle.lifetimePercentage > 1.0) {
            particle.lifetimePercentage = 1.0;
        }

        // Write back to the particle buffer
        particles[index] = particle;
    }
}
