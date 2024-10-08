#version 430 core

// Define the particle structure
struct Particle {
    vec4 position;// Use only the first 3 components (x, y, z)
    vec4 velocity;// Use only the first 3 components (x, y, z)
    float spawnTime;// 1 float (4 bytes)
    float lifetime;// 1 float (4 bytes)
    float particleID;// 1 float (4 bytes)
    float particleWeight;// 1 float (4 bytes)
    float lifetimePercentage;// 1 float (4 bytes)
};

// Bind the particle buffer as a shader storage buffer
layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

// Buffer for generation data
layout(std430, binding = 1) buffer GenerationData {
    uint particlesGenerated;
};

// Specify workgroup size
layout(local_size_x = 128) in;

// Uniforms
uniform float currentTime;// Time in seconds
uniform float deltaTime;
uniform float particleMaxLifetime;
uniform vec3 particleGravity;
uniform float particleMaxVelocity;
uniform float particleMinWeight;
uniform float particleMaxWeight;
uniform float particleBounceFactor;
uniform vec3 particleGroundPlaneNormal;
uniform float particleGroundPlaneHeight;
uniform int maxParticles;
uniform bool particleGenerator;
uniform uint particleBatchSize;
uniform bool shouldGenerate;// New uniform to control generation

uniform float minX;
uniform float maxX;
uniform float minY;
uniform float maxY;
uniform float minZ;
uniform float maxZ;

uniform float minInitialVelocityX;
uniform float maxInitialVelocityX;
uniform float minInitialVelocityY;
uniform float maxInitialVelocityY;
uniform float minInitialVelocityZ;
uniform float maxInitialVelocityZ;

uniform bool particleSpawnTimeJitter;
uniform float particleMaxSpawnTimeJitter;

uniform float particlePressure;
uniform float particleViscosity;
uniform bool fluidSimulation;

// Shared variable for particles generated in the workgroup
shared uint particlesGeneratedInWorkgroup;

// Function to generate random values based on particle ID
float random(float seed, float time) {
    return fract(sin(seed + float(gl_GlobalInvocationID.x) * 12.9898 + time * 78.233) * 43758.5453123);
}

// Function to calculate fluid forces (simple pressure and viscosity model)
vec3 calculateFluidForces(vec3 velocity) {
    vec3 pressureForce = vec3(0.0);
    if (length(velocity) > 0.0) {
        pressureForce = -normalize(velocity) * particlePressure;
    }
    vec3 viscosityForce = -velocity * particleViscosity;
    return pressureForce + viscosityForce;
}

void main() {
    uint index = gl_GlobalInvocationID.x;

    if (index >= uint(maxParticles)) return;// Avoid updating more particles than allowed

    Particle particle = particles[index];

    // Always set particleID
    particle.particleID = float(index);

    bool isExpired = (particle.lifetimePercentage >= 1.0);

    // Initialize the shared counter to 0 only once per workgroup
    if (gl_LocalInvocationID.x == 0) {
        particlesGeneratedInWorkgroup = 0u;
    }

    // Synchronize to ensure all threads in the workgroup see the updated value
    barrier();
    if (shouldGenerate && particleGenerator && isExpired) {
        // Atomically increment the particlesGenerated counter and check if we can generate more particles
        uint globalGenerated = atomicAdd(particlesGenerated, 1u);
        if (globalGenerated < particleBatchSize) {
            // Atomically increment the local workgroup counter
            uint localGenerated = atomicAdd(particlesGeneratedInWorkgroup, 1u);

            // Regenerate the particle
            float randSeed = particle.particleID * 0.1 + currentTime;

            // Generate random positions
            float randX = random(randSeed + 0.0, currentTime);
            float randY = random(randSeed + 1.0, currentTime);
            float randZ = random(randSeed + 2.0, currentTime);
            particle.position.x = mix(minX, maxX, randX);
            particle.position.y = mix(minY, maxY, randY);
            particle.position.z = mix(minZ, maxZ, randZ);
            particle.position.w = 1.0;

            // Generate random initial velocities
            float randVelX = random(randSeed + 3.0, currentTime);
            float randVelY = random(randSeed + 4.0, currentTime);
            float randVelZ = random(randSeed + 5.0, currentTime);
            particle.velocity.x = mix(minInitialVelocityX, maxInitialVelocityX, randVelX);
            particle.velocity.y = mix(minInitialVelocityY, maxInitialVelocityY, randVelY);
            particle.velocity.z = mix(minInitialVelocityZ, maxInitialVelocityZ, randVelZ);
            particle.velocity.w = 0.0;

            // Assign lifetime
            if (particleMaxLifetime > 0.0) {
                float randLifetime = random(randSeed + 6.0, currentTime);
                particle.lifetime = mix(0.1, particleMaxLifetime, randLifetime);
            } else {
                particle.lifetime = 0.0;
            }

            // Generate random weight; within min and max values
            particle.particleWeight = mix(particleMinWeight, particleMaxWeight, random(randSeed + 8.0, currentTime));

            // Initialize spawn time with optional jitter
            particle.spawnTime = currentTime;
            if (particleSpawnTimeJitter) {
                float randJitter = random(randSeed + 7.0, currentTime);
                float jitterValue = randJitter * particleMaxSpawnTimeJitter;
                particle.spawnTime += jitterValue;
            }

            particle.lifetimePercentage = 0.0;
        }
    }

    // Process the particles that are currently active
    if (particle.lifetimePercentage < 1.0) {
        // Scale gravity based on weight (optional)
        vec3 adjustedGravity = particleGravity * particle.particleWeight;
        particle.velocity.xyz += adjustedGravity * deltaTime;

        // Apply fluid simulation forces if enabled
        if (fluidSimulation) {
            vec3 fluidForces = calculateFluidForces(particle.velocity.xyz);
            particle.velocity.xyz += fluidForces * deltaTime;
        }

        // Clamp the velocity to the maximum allowed value
        float speed = length(particle.velocity.xyz);
        if (speed > particleMaxVelocity) {
            particle.velocity.xyz = normalize(particle.velocity.xyz) * particleMaxVelocity;
        }

        // Update position based on velocity
        particle.position.xyz += particle.velocity.xyz * deltaTime;

        // Check for collision with the ground plane
        float distanceToGround = dot(particle.position.xyz, particleGroundPlaneNormal) - particleGroundPlaneHeight;
        if (distanceToGround < 0.0) {
            // Reflect the velocity based on the ground plane normal
            particle.velocity.xyz = reflect(particle.velocity.xyz, particleGroundPlaneNormal) * particleBounceFactor;

            // Clamp the reflected velocity to the maximum allowed value
            speed = length(particle.velocity.xyz);
            if (speed > particleMaxVelocity) {
                particle.velocity.xyz = normalize(particle.velocity.xyz) * particleMaxVelocity;
            }

            // Prevent the particle from penetrating the ground plane
            particle.position.xyz -= particleGroundPlaneNormal * distanceToGround;
        }

        // Calculate the elapsed time and update the lifetime percentage
        float elapsedTime = currentTime - particle.spawnTime;
        if (particle.lifetime > 0.0) {
            particle.lifetimePercentage = clamp(elapsedTime / particle.lifetime, 0.0, 1.0);
        }

        // Handle precision issues
        if (particle.lifetimePercentage >= 0.9999) {
            particle.lifetimePercentage = 1.0;
        }
    } else {
        // If particle expired and not regenerated, reset velocity
        particle.velocity.xyz = vec3(0.0);
    }

    // Write the updated particle data back to the buffer
    particles[index] = particle;
}