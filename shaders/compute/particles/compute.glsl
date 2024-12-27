#version 430 core
#include "common_funcs.glsl"

// ---------------------------
// Particle structure
// ---------------------------
struct Particle {
    vec4 position;// (x, y, z, w)
    vec4 velocity;// (x, y, z, w)
    float spawnTime;
    float lifetime;
    float particleID;
    float particleWeight;
    float lifetimePercentage;
};

// Particle Buffer
layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

layout(std430, binding = 1) buffer GenerationData {
    uint particlesGenerated;
};

// Workgroup size
layout(local_size_x = 128) in;

// Main uniforms
uniform float currentTime;
uniform float deltaTime;
uniform float particleMaxLifetime;
uniform float particleMaxVelocity;
uniform float particleMinWeight;
uniform float particleMaxWeight;
uniform float particleBounceFactor;
uniform vec3 particleGroundPlaneNormal;
uniform float particleGroundPlaneHeight;
uniform int maxParticles;
uniform bool particleGenerator;
uniform uint particleBatchSize;
uniform bool shouldGenerate;

// Ranges for random spawn positions
uniform float minX;
uniform float maxX;
uniform float minY;
uniform float maxY;
uniform float minZ;
uniform float maxZ;

// Ranges for random initial velocities
uniform float minInitialVelocityX;
uniform float maxInitialVelocityX;
uniform float minInitialVelocityY;
uniform float maxInitialVelocityY;
uniform float minInitialVelocityZ;
uniform float maxInitialVelocityZ;

uniform bool particleSpawnTimeJitter;
uniform float particleMaxSpawnTimeJitter;

// Fluid simulation toggle
uniform bool fluidSimulation;

// Additional fluid uniforms here
uniform vec3 particleGravity;
uniform float fluidPressure;
uniform float fluidViscosity;
uniform float fluidForceMultiplier;

shared uint particlesGeneratedInWorkgroup;

void main()
{
    uint index = gl_GlobalInvocationID.x;
    if (index >= uint(maxParticles)) return;

    Particle particle = particles[index];
    particle.particleID = float(index);

    bool isExpired = (particle.lifetimePercentage >= 1.0);

    // Initialize shared counter once per workgroup
    if (gl_LocalInvocationID.x == 0) {
        particlesGeneratedInWorkgroup = 0u;
    }
    barrier();

    // Particle generation if expired
    if (shouldGenerate && particleGenerator && isExpired)
    {
        uint globalGenerated = atomicAdd(particlesGenerated, 1u);
        if (globalGenerated < particleBatchSize)
        {
            uint localGenerated = atomicAdd(particlesGeneratedInWorkgroup, 1u);
            uint baseSeed = uint(particle.particleID)*1664525u
            + uint(gl_GlobalInvocationID.x)*1013904223u
            + uint(currentTime*1000.0);

            // Random position
            float randX = rand(baseSeed + 101u);
            float randY = rand(baseSeed + 102u);
            float randZ = rand(baseSeed + 103u);
            particle.position = vec4(
            mix(minX, maxX, randX),
            mix(minY, maxY, randY),
            mix(minZ, maxZ, randZ),
            1.0
            );

            // Random velocity
            float randVelX = rand(baseSeed + 201u);
            float randVelY = rand(baseSeed + 202u);
            float randVelZ = rand(baseSeed + 203u);
            particle.velocity = vec4(
            mix(minInitialVelocityX, maxInitialVelocityX, randVelX),
            mix(minInitialVelocityY, maxInitialVelocityY, randVelY),
            mix(minInitialVelocityZ, maxInitialVelocityZ, randVelZ),
            0.0
            );

            // Lifetime
            if (particleMaxLifetime > 0.0)
            {
                float randLifetime = rand(baseSeed + 204u);
                particle.lifetime = mix(0.1, particleMaxLifetime, randLifetime);
            }
            else
            {
                particle.lifetime = 0.0;
            }

            // Weight
            particle.particleWeight = mix(
            particleMinWeight, particleMaxWeight, rand(baseSeed + 205u)
            );

            // Spawn time + optional jitter
            particle.spawnTime = currentTime;
            if (particleSpawnTimeJitter)
            {
                float randJitter = rand(baseSeed + 206u);
                float jitterValue = randJitter * particleMaxSpawnTimeJitter;
                particle.spawnTime += jitterValue;
            }

            particle.lifetimePercentage = 0.0;
        }
    }

    // Process active
    if (particle.lifetimePercentage < 1.0)
    {
        // Gravity scaled by weight
        vec3 adjustedGravity = particleGravity * particle.particleWeight;
        particle.velocity.xyz += adjustedGravity * deltaTime;

        // Fluid
        if (fluidSimulation)
        {
            // Pass all 5 parameters to 'calculateFluidForces'
            vec3 fluidForces = calculateFluidForces(
            particle.velocity.xyz,
            adjustedGravity,
            fluidPressure,
            fluidViscosity,
            fluidForceMultiplier
            );
            particle.velocity.xyz += fluidForces * deltaTime;
        }

        // velocity clamp
        float speed = length(particle.velocity.xyz);
        if (speed > particleMaxVelocity)
        {
            particle.velocity.xyz = normalize(particle.velocity.xyz) * particleMaxVelocity;
        }

        // Update position
        particle.position.xyz += particle.velocity.xyz * deltaTime;

        // ground collision
        float distanceToGround = dot(particle.position.xyz, particleGroundPlaneNormal) - particleGroundPlaneHeight;
        if (distanceToGround < 0.0)
        {
            particle.velocity.xyz = reflect(particle.velocity.xyz, particleGroundPlaneNormal) * particleBounceFactor;
            float bounceSpeed = length(particle.velocity.xyz);
            if (bounceSpeed > particleMaxVelocity)
            {
                particle.velocity.xyz = normalize(particle.velocity.xyz) * particleMaxVelocity;
            }
            // push up
            particle.position.xyz -= particleGroundPlaneNormal * distanceToGround;
        }

        // lifetime
        float elapsedTime = currentTime - particle.spawnTime;
        if (particle.lifetime > 0.0)
        {
            particle.lifetimePercentage = clamp(elapsedTime / particle.lifetime, 0.0, 1.0);
        }
        if (particle.lifetimePercentage >= 0.9999)
        {
            particle.lifetimePercentage = 1.0;
        }
    }
    else
    {
        // Expired
        particle.velocity.xyz = vec3(0.0);
    }

    particles[index] = particle;
}
