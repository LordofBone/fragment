#version 430
#include "common_funcs.glsl"

// Input
layout (location = 0) in vec4 position;
layout (location = 1) in vec4 velocity;
layout (location = 2) in float spawnTime;
layout (location = 3) in float particleLifetime;
layout (location = 4) in float particleID;
layout (location = 5) in float particleWeight;
layout (location = 6) in float lifetimePercentage;

// Uniforms
uniform float currentTime;
uniform float deltaTime;
uniform float particleBounceFactor;
uniform vec3 particleGroundPlaneNormal;
uniform float particleGroundPlaneHeight;
uniform float particleMaxVelocity;
uniform float particleSize;
uniform vec3 particleColor;

uniform bool fluidSimulation;

// Now define these in the vertex shader (no conflict with common_funcs):
uniform vec3 particleGravity;
uniform float fluidPressure;
uniform float fluidViscosity;
uniform float fluidForceMultiplier;

// Matrices, etc.
uniform mat4 view;
uniform mat4 projection;
uniform mat4 model;
uniform vec3 cameraPosition;

// Transform feedback outputs
out vec4 tfPosition;
out vec4 tfVelocity;
out float tfSpawnTime;
out float tfParticleLifetime;
out float tfParticleID;
out float tfLifetimePercentage;
out float tfParticleWeight;
out float lifetimePercentageToFragment;

// For fragment
out vec3 fragColor;
flat out float particleIDOut;
out vec3 fragPos;

void main()
{
    // Pass through
    tfSpawnTime        = spawnTime;
    tfParticleLifetime = particleLifetime;
    tfParticleID       = particleID;
    tfParticleWeight   = particleWeight;
    fragColor          = particleColor;
    particleIDOut      = particleID;

    float elapsedTime = currentTime - spawnTime;
    float calcLifetimePct = 0.0;
    if (particleLifetime > 0.0)
    {
        calcLifetimePct = clamp(elapsedTime / particleLifetime, 0.0, 1.0);
    }

    tfLifetimePercentage        = calcLifetimePct;
    lifetimePercentageToFragment = calcLifetimePct;

    // If expired
    if (calcLifetimePct >= 1.0 || lifetimePercentage >= 1.0)
    {
        tfPosition           = position;
        tfVelocity           = velocity;
        gl_PointSize         = 0.0;
        gl_Position          = vec4(0.0);
        tfLifetimePercentage = 1.0;
        lifetimePercentageToFragment = 1.0;
        tfParticleID         = particleID;
        particleIDOut        = particleID;
        fragPos              = (model * position).xyz;
        return;
    }

    // Gravity
    vec3 adjustedGravity = particleGravity * particleWeight;
    vec3 newVelocity     = velocity.xyz + adjustedGravity * deltaTime;

    // Fluid
    if (fluidSimulation)
    {
        // Call with 5 parameters
        vec3 fluidForces = calculateFluidForces(
        newVelocity,
        adjustedGravity,
        fluidPressure,
        fluidViscosity,
        fluidForceMultiplier
        );
        newVelocity += fluidForces * deltaTime;
    }

    // clamp velocity
    float speed = length(newVelocity);
    if (speed > particleMaxVelocity)
    {
        newVelocity = normalize(newVelocity) * particleMaxVelocity;
    }

    // Update position
    vec3 newPos = position.xyz + newVelocity * deltaTime;

    // Ground collision
    float distGround = dot(newPos, particleGroundPlaneNormal) - particleGroundPlaneHeight;
    if (distGround < 0.0)
    {
        newVelocity = reflect(newVelocity, particleGroundPlaneNormal) * particleBounceFactor;
        float bounceSpeed = length(newVelocity);
        if (bounceSpeed > particleMaxVelocity)
        {
            newVelocity = normalize(newVelocity) * particleMaxVelocity;
        }
        newPos -= particleGroundPlaneNormal * distGround;
    }

    // Billboard approach: size by distance
    vec3 toCamera = cameraPosition - newPos;
    float distanceFromCamera = length(toCamera);
    float adjustedSize = particleSize / distanceFromCamera;
    gl_PointSize = adjustedSize;

    // Transform feedback
    tfPosition = vec4(newPos, 1.0);
    tfVelocity = vec4(newVelocity, 0.0);

    vec4 worldPosition = model * vec4(newPos, 1.0);
    gl_Position        = projection * view * worldPosition;
    fragPos            = worldPosition.xyz;
}
