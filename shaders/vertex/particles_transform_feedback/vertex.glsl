#version 430
#include "common_funcs.glsl"

// -----------------------------------------------------------------------------
// Inputs
// -----------------------------------------------------------------------------
layout (location = 0) in vec4 position;// (x, y, z, w)
layout (location = 1) in vec4 velocity;// (x, y, z, w)
layout (location = 2) in float spawnTime;
layout (location = 3) in float particleLifetime;
layout (location = 4) in float particleID;
layout (location = 5) in float particleWeight;
layout (location = 6) in float lifetimePercentage;

// -----------------------------------------------------------------------------
// Uniforms
// -----------------------------------------------------------------------------
uniform float currentTime;
uniform float deltaTime;
uniform float particleBounceFactor;
uniform vec3  particleGroundPlaneNormal;
uniform float particleGroundPlaneHeight;
uniform float particleMaxVelocity;
uniform float particleSize;
uniform vec3  particleColor;

uniform bool  fluidSimulation;
uniform vec3  particleGravity;
uniform float particlePressure;
uniform float particleViscosity;
uniform float fluidForceMultiplier;

uniform mat4  view;
uniform mat4  projection;
uniform mat4  model;
uniform vec3  cameraPosition;

// -----------------------------------------------------------------------------
// Transform Feedback Outputs
// -----------------------------------------------------------------------------
out vec4 tfPosition;
out vec4 tfVelocity;
out float tfSpawnTime;
out float tfParticleLifetime;
out float tfParticleID;
out float tfLifetimePercentage;
out float tfParticleWeight;

// For the fragment shader
out float lifetimePercentageToFragment;
out vec3  fragColor;
flat out float particleIDOut;
out vec3  fragPos;

void main()
{
    // Pass original scalar data forward (unchanged)
    tfSpawnTime         = spawnTime;
    tfParticleLifetime  = particleLifetime;
    tfParticleID        = particleID;
    tfParticleWeight    = particleWeight;
    fragColor           = particleColor;
    particleIDOut       = particleID;

    // Compute lifetime percentage from spawnTime, if we have a finite lifetime
    float elapsedTime   = currentTime - spawnTime;
    float calcLifetimePct = 0.0;
    if (particleLifetime > 0.0)
    {
        calcLifetimePct = clamp(elapsedTime / particleLifetime, 0.0, 1.0);
    }

    tfLifetimePercentage         = calcLifetimePct;
    lifetimePercentageToFragment = calcLifetimePct;

    // If expired, mark it as dead. Position/Velocity remain what they were,
    // and we set lifetimePercentage to 1.0 so we can skip it on the next pass.
    if (calcLifetimePct >= 1.0 || lifetimePercentage >= 1.0)
    {
        tfPosition           = position;
        tfVelocity           = velocity;
        tfLifetimePercentage = 1.0;
        lifetimePercentageToFragment = 1.0;

        // Render trick: set gl_PointSize to 0 and gl_Position to something trivial.
        gl_PointSize         = 0.0;
        gl_Position          = vec4(0.0);

        // We still carry IDs, etc., for debugging
        tfParticleID         = particleID;
        particleIDOut        = particleID;
        fragPos              = (model * position).xyz;
        return;
    }

    // -------------------------------------------------------------------------
    //   Simulate forces
    // -------------------------------------------------------------------------
    // 1) Gravity scaled by particle weight
    vec3 adjustedGravity = particleGravity * particleWeight;
    vec3 newVelocity     = velocity.xyz + adjustedGravity * deltaTime;

    // 2) Fluid forces if fluidSimulation == true
    if (fluidSimulation)
    {
        vec3 fluidForces = calculateFluidForces(
        newVelocity,
        adjustedGravity,
        particlePressure,
        particleViscosity,
        fluidForceMultiplier
        );
        newVelocity += fluidForces * deltaTime;
    }

    // 3) Clamp velocity to the max
    float speed = length(newVelocity);
    if (speed > particleMaxVelocity)
    {
        newVelocity = normalize(newVelocity) * particleMaxVelocity;
    }

    // 4) Update the position
    vec3 newPos = position.xyz + newVelocity * deltaTime;

    // 5) Ground-plane collision check
    float distGround = dot(newPos, particleGroundPlaneNormal) - particleGroundPlaneHeight;
    if (distGround < 0.0)
    {
        // Reflect off ground plane
        newVelocity = reflect(newVelocity, particleGroundPlaneNormal) * particleBounceFactor;

        // Re-clamp velocity after bounce
        float bounceSpeed = length(newVelocity);
        if (bounceSpeed > particleMaxVelocity)
        {
            newVelocity = normalize(newVelocity) * particleMaxVelocity;
        }

        // Push particle back up so it isn’t under the plane
        newPos -= particleGroundPlaneNormal * distGround;

        // As on CPU: ensure it bounces up at least a tiny bit
        if (abs(newVelocity.y) < 0.1)
        {
            newVelocity.y = 0.1;
        }
    }

    // -------------------------------------------------------------------------
    //   Prepare for rendering
    // -------------------------------------------------------------------------
    // Size by distance (simple billboard style)
    vec3 toCamera          = cameraPosition - newPos;
    float distanceFromCamera = length(toCamera);
    float adjustedSize     = particleSize / distanceFromCamera;
    gl_PointSize           = adjustedSize;

    // Transform feedback outputs
    tfPosition = vec4(newPos, 1.0);
    tfVelocity = vec4(newVelocity, 0.0);

    // Standard MVP transform
    vec4 worldPosition = model * vec4(newPos, 1.0);
    gl_Position        = projection * view * worldPosition;
    fragPos            = worldPosition.xyz;
}
