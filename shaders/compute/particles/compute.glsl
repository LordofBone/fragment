#version 430 core
#include "glsl_utilities.glsl"

// -----------------------------------------------------------------------------
// Particle Structure & Buffers
// -----------------------------------------------------------------------------
struct Particle {
    vec4  position;// (x, y, z, w)
    vec4  velocity;// (x, y, z, w)
    float spawnTime;
    float lifetime;
    float particleID;
    float particleWeight;
    float lifetimePercentage;
};

// ---------------------------------------------------
// SSBO: Particle setup
// ---------------------------------------------------
layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

layout(std430, binding = 1) buffer GenerationData {
    uint particlesGenerated;// used if shouldGenerate = true
};

layout(local_size_x = 128) in;// dispatch size

// ---------------------------------------------------
// Uniforms
// ---------------------------------------------------
uniform float currentTime;
uniform float deltaTime;
uniform float particleMaxLifetime;
uniform float particleMaxVelocity;
uniform float particleMinWeight;
uniform float particleMaxWeight;
uniform float particleBounceFactor;

// Base normal + angles
uniform vec3  particleGroundPlaneNormal;
uniform vec2  groundPlaneAngle;
uniform float particleGroundPlaneHeight;

uniform int   maxParticles;

// Particle generation logic
uniform bool  particleGenerator;
uniform uint  particleBatchSize;
uniform bool  shouldGenerate;

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

uniform bool  particleSpawnTimeJitter;
uniform float particleMaxSpawnTimeJitter;

// Fluid simulation
uniform bool  fluidSimulation;
uniform vec3  particleGravity;
uniform float fluidPressure;
uniform float fluidViscosity;
uniform float fluidForceMultiplier;

// -----------------------------------------------------------------------------
// Shared variable for counting how many new particles are created per dispatch
// -----------------------------------------------------------------------------
shared uint particlesGeneratedInWorkgroup;

void main()
{
    uint index = gl_GlobalInvocationID.x;
    if (index >= uint(maxParticles)) return;

    Particle particle = particles[index];
    particle.particleID = float(index);

    bool isExpired = (particle.lifetimePercentage >= 1.0);

    // Initialize local shared counter once per workgroup
    if (gl_LocalInvocationID.x == 0) {
        particlesGeneratedInWorkgroup = 0u;
    }
    barrier();

    //--------------------------------------------
    // 1) Particle Generation
    //--------------------------------------------
    if (shouldGenerate && particleGenerator && isExpired)
    {
        // Atomically increment the global generation counter
        uint globalGenerated = atomicAdd(particlesGenerated, 1u);
        if (globalGenerated < particleBatchSize)
        {
            // We'll seed our random generator with ID + time
            uint baseSeed = uint(particle.particleID)*1664525u
            + uint(gl_GlobalInvocationID.x)*1013904223u
            + uint(currentTime * 1000.0);

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

            // Lifetime (0.0 means immortal)
            if (particleMaxLifetime > 0.0)
            {
                float randLifetime = rand(baseSeed + 204u);
                particle.lifetime  = mix(0.1, particleMaxLifetime, randLifetime);
            }
            else
            {
                particle.lifetime  = 0.0;
            }

            // Weight
            particle.particleWeight = mix(
            particleMinWeight,
            particleMaxWeight,
            rand(baseSeed + 205u)
            );

            // Spawn time + optional jitter
            particle.spawnTime = currentTime;
            if (particleSpawnTimeJitter)
            {
                float randJitter  = rand(baseSeed + 206u);
                float jitterValue = randJitter * particleMaxSpawnTimeJitter;
                particle.spawnTime += jitterValue;
            }

            // Reset particle lifetime
            particle.lifetimePercentage = 0.0;
        }
    }

    //--------------------------------------------
    // 2) Update existing particles
    //--------------------------------------------
    if (particle.lifetimePercentage < 1.0)
    {
        // Gravity scaled by weight
        vec3 adjGravity = particleGravity * particle.particleWeight;
        particle.velocity.xyz += adjGravity * deltaTime;

        // Fluid simulation
        if (fluidSimulation) {
            vec3 fluid = calculateFluidForces(
            particle.velocity.xyz, adjGravity,
            fluidPressure, fluidViscosity,
            fluidForceMultiplier
            );
            particle.velocity.xyz += fluid * deltaTime;
        }

        // clamp velocity
        float speed = length(particle.velocity.xyz);
        if (speed > particleMaxVelocity) {
            particle.velocity.xyz = normalize(particle.velocity.xyz) * particleMaxVelocity;
        }

        // Integrate
        particle.position.xyz += particle.velocity.xyz * deltaTime;

        // Collide with rotated ground plane
        vec3 planeN = rotatePlaneNormal(particleGroundPlaneNormal, groundPlaneAngle);
        float dist  = dot(particle.position.xyz, planeN) - particleGroundPlaneHeight;
        if (dist < 0.0) {
            // reflect
            particle.velocity.xyz = reflect(particle.velocity.xyz, planeN) * particleBounceFactor;

            // clamp
            float bSpeed = length(particle.velocity.xyz);
            if (bSpeed > particleMaxVelocity) {
                particle.velocity.xyz = normalize(particle.velocity.xyz) * particleMaxVelocity;
            }

            // push out
            particle.position.xyz -= planeN * dist;
        }

        // Update lifetime
        float elapsed = currentTime - particle.spawnTime;
        if (particle.lifetime > 0.0) {
            particle.lifetimePercentage = clamp(elapsed / particle.lifetime, 0.0, 1.0);
        } else {
            // immortal
            particle.lifetimePercentage = 0.0;
        }

        // If nearly expired
        if (particle.lifetimePercentage >= 0.9999) {
            particle.lifetimePercentage = 1.0;
        }
    }
    else
    {
        // If expired, keep velocity zero
        particle.velocity.xyz = vec3(0.0);
    }

    // Write back to SSBO
    particles[index] = particle;
}
