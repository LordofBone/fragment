#version 430
#include "glsl_utilities.glsl"

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
uniform vec2 groundPlaneAngle;
uniform float particleGroundPlaneHeight;
uniform float particleMaxVelocity;
uniform float particleSize;
uniform vec3  particleColor;

uniform bool  fluidSimulation;
uniform vec3  particleGravity;
uniform float fluidPressure;
uniform float fluidViscosity;
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

    float elapsedTime = currentTime - spawnTime;
    float calcLifetimePct = 0.0;
    if (particleLifetime > 0.0) {
        calcLifetimePct = clamp(elapsedTime / particleLifetime, 0.0, 1.0);
    }
    tfLifetimePercentage         = calcLifetimePct;
    lifetimePercentageToFragment = calcLifetimePct;

    // If expired -> skip
    if (calcLifetimePct >= 1.0 || lifetimePercentage >= 1.0)
    {
        tfPosition           = position;
        tfVelocity           = velocity;
        tfLifetimePercentage = 1.0;
        lifetimePercentageToFragment = 1.0;

        // Hide the particle
        gl_PointSize = 0.0;
        gl_Position  = vec4(0.0);
        fragPos      = (model * position).xyz;
        return;
    }

    // -------------------------------------------------------------------------
    // Forces
    // -------------------------------------------------------------------------
    vec3 adjustedGravity = particleGravity * particleWeight;
    vec3 newVelocity     = velocity.xyz + adjustedGravity * deltaTime;

    if (fluidSimulation) {
        vec3 fluidForces = calculateFluidForces(
        newVelocity, adjustedGravity,
        fluidPressure, fluidViscosity,
        fluidForceMultiplier
        );
        newVelocity += fluidForces * deltaTime;
    }

    // Clamp velocity
    float speed = length(newVelocity);
    if (speed > particleMaxVelocity) {
        newVelocity = normalize(newVelocity) * particleMaxVelocity;
    }

    // Integrate
    vec3 newPos = position.xyz + newVelocity * deltaTime;

    // -------------------------------------------------------------------------
    // Collision with rotated plane
    // -------------------------------------------------------------------------
    // 1) Compute final plane normal from base + angles:
    vec3 planeN = rotatePlaneNormal(particleGroundPlaneNormal, groundPlaneAngle);

    // 2) Distance
    float distGround = dot(newPos, planeN) - particleGroundPlaneHeight;
    if (distGround < 0.0)
    {
        newVelocity = reflect(newVelocity, planeN) * particleBounceFactor;

        float bounceSpeed = length(newVelocity);
        if (bounceSpeed > particleMaxVelocity) {
            newVelocity = normalize(newVelocity) * particleMaxVelocity;
        }

        // push out so it’s not under the plane
        newPos -= planeN * distGround;
    }

    // -------------------------------------------------------------------------
    // Render
    // -------------------------------------------------------------------------
    vec3 toCamera = cameraPosition - newPos;
    float distanceFromCamera = length(toCamera);
    float adjustedSize = particleSize / distanceFromCamera;
    gl_PointSize = adjustedSize;

    // TF outputs
    tfPosition = vec4(newPos, 1.0);
    tfVelocity = vec4(newVelocity, 0.0);

    // MVP transform
    vec4 worldPosition = model * vec4(newPos, 1.0);
    gl_Position        = projection * view * worldPosition;
    fragPos            = worldPosition.xyz;
}
