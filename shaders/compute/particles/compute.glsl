#version 430 core

// Define the particle structure
struct Particle {
    vec3 position;// 3 floats (12 bytes + 4 bytes padding)
    vec3 velocity;// 3 floats (12 bytes + 4 bytes padding)
    float spawnTime;// 1 float (4 bytes)
    float lifetime;// 1 float (4 bytes)
    float particleID;// 1 float (4 bytes)
    float lifetimePercentage;// 1 float (4 bytes)
};

// Bind the particle buffer as a shader storage buffer
layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

// Buffer for generation data
layout(std430, binding = 1) buffer GenerationData {
    uint lastGenerationTime;
};

// Specify workgroup size
layout(local_size_x = 128) in;

uniform uint currentTime;
uniform uint generatorDelay;
uniform float deltaTime;
uniform float particleMaxLifetime;
uniform vec3 particleGravity;
uniform float particleMaxVelocity;
uniform float particleBounceFactor;
uniform vec3 particleGroundPlaneNormal;
uniform float particleGroundPlaneHeight;
uniform int maxParticles;
uniform bool particleGenerator;
uniform int particleBatchSize;

uniform float minX;
uniform float maxX;
uniform float minY;
uniform float maxY;
uniform float minZ;
uniform float maxZ;

uniform bool particleSpawnTimeJitter;
uniform float particleMaxSpawnTimeJitter;

uniform float particlePressure;
uniform float particleViscosity;
uniform bool fluidSimulation;

// Shared variable for counting generated particles in this frame
shared uint particlesGenerated;

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

void main() {
    uint index = gl_GlobalInvocationID.x;

    if (index >= uint(maxParticles)) return;// Avoid updating more particles than allowed

    // Initialize the shared counter to 0 only once per workgroup
    if (gl_LocalInvocationID.x == 0) {
        particlesGenerated = 0;
    }

    // Synchronize to ensure all threads see the initialized value
    barrier();

    Particle particle = particles[index];

    // Always set particleID
    particle.particleID = float(index);

    bool isExpired = (particle.lifetimePercentage >= 1.0);

    bool shouldGenerate = false;

    if (particleGenerator && isExpired) {
        uint timeSinceLastGen = currentTime - lastGenerationTime;
        if (timeSinceLastGen >= generatorDelay) {
            // Atomically increment the particlesGenerated counter and check if we can generate more particles
            uint generated = atomicAdd(particlesGenerated, 1);
            if (generated < uint(particleBatchSize)) {
                shouldGenerate = true;
                // Atomically update the lastGenerationTime
                atomicMax(lastGenerationTime, currentTime);
            }
        }
    }

    if (shouldGenerate) {
        float randSeed = particle.particleID * 0.1 + float(currentTime) * 0.001;

        // Generate random positions
        float randX = random(randSeed + 0.0, float(currentTime) * 0.001);
        float randY = random(randSeed + 1.0, float(currentTime) * 0.001);
        float randZ = random(randSeed + 2.0, float(currentTime) * 0.001);
        particle.position.x = mix(minX, maxX, randX);
        particle.position.y = mix(minY, maxY, randY);
        particle.position.z = mix(minZ, maxZ, randZ);

        // Generate random velocities between -0.5 and 0.5
        particle.velocity.x = random(randSeed + 3.0, float(currentTime) * 0.001) - 0.5;
        particle.velocity.y = random(randSeed + 4.0, float(currentTime) * 0.001) - 0.5;
        particle.velocity.z = random(randSeed + 5.0, float(currentTime) * 0.001) - 0.5;

        // Assign lifetime
        if (particleMaxLifetime > 0.0) {
            float randLifetime = random(randSeed + 6.0, float(currentTime) * 0.001);
            particle.lifetime = mix(0.1, particleMaxLifetime, randLifetime);

        } else {
            particle.lifetime = 0.0;
        }

        // Initialize spawn time with optional jitter
        particle.spawnTime = float(currentTime) * 0.001;
        if (particleSpawnTimeJitter) {
            float randJitter = random(randSeed + 7.0, float(currentTime) * 0.001);
            float jitterValue = randJitter * particleMaxSpawnTimeJitter;
            particle.spawnTime += jitterValue;
        }

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
        float elapsedTime = float(currentTime) * 0.001 - particle.spawnTime;
        if (particle.lifetime > 0.0) {
            particle.lifetimePercentage = clamp(elapsedTime / particle.lifetime, 0.0, 1.0);
        } else {
            particle.lifetimePercentage = 1.0;
        }

        // Handle precision issues
        if (particle.lifetimePercentage >= 0.9999) {
            particle.lifetimePercentage = 1.0;
        }
    } else {
        // If particle expired and not regenerated, reset velocity
        particle.velocity = vec3(0.0);
    }

    // Write the updated particle data back to the buffer
    particles[index] = particle;
}
