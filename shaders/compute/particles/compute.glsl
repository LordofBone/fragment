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
uniform float width;
uniform float height;
uniform float depth;

// Function to generate random values based on particle ID
float random(float seed) {
    return fract(sin(seed) * 43758.5453123);
}

// Main compute shader function
void main() {
    uint index = gl_GlobalInvocationID.x;
    Particle particle = particles[index];

    // Initialize velocities and positions with random values if not already set
    if (particle.lifetimePercentage == 0.0) {
        float randSeed = particle.particleID * 0.1;

        // Set random initial position within the bounds (width, height, depth)
        particle.position.x = (random(randSeed) * 2.0 - 1.0) * width;
        particle.position.y = (random(randSeed + 1.0) * 2.0 - 1.0) * height;
        particle.position.z = (random(randSeed + 2.0) * 2.0 - 1.0) * depth;

        // Set random velocity
        particle.velocity.x = (random(randSeed + 3.0) * 2.0 - 1.0) * particleMaxVelocity;
        particle.velocity.y = (random(randSeed + 4.0) * 2.0 - 1.0) * particleMaxVelocity;
        particle.velocity.z = (random(randSeed + 5.0) * 2.0 - 1.0) * particleMaxVelocity;

        // Assign a random lifetime based on the uniform `particleMaxLifetime`
        particle.lifetime = random(randSeed + 6.0) * particleMaxLifetime;

        // Initialize the particle's spawn time
        particle.spawnTime = currentTime;
    }

    // Update only if the particle is active (lifetimePercentage < 1.0)
    if (particle.lifetimePercentage < 1.0) {
        // Update velocity with gravity
        particle.velocity += particleGravity * deltaTime;

        // Update position
        particle.position += particle.velocity * deltaTime;

        // Calculate the elapsed time and update the lifetime percentage
        float elapsedTime = currentTime - particle.spawnTime;
        particle.lifetimePercentage = elapsedTime / particle.lifetime;

        // Clamp lifetimePercentage to 1.0
        if (particle.lifetimePercentage > 1.0) {
            particle.lifetimePercentage = 1.0;
        }

        // Write the updated particle data back to the buffer
        particles[index] = particle;
    }
}
