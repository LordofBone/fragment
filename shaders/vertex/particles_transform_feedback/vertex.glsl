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

// For the collision plane
uniform vec3  particleGroundPlaneNormal;// base normal
uniform vec2  groundPlaneAngle;// yaw, pitch in degrees
uniform float particleGroundPlaneHeight;

uniform float currentTime;
uniform float deltaTime;
uniform float particleMaxVelocity;
uniform float particleBounceFactor;

// Gravity, fluid, etc.
uniform bool  fluidSimulation;
uniform vec3  particleGravity;
uniform float fluidPressure;
uniform float fluidViscosity;
uniform float fluidForceMultiplier;

// Sizing / color
uniform float particleSize;
uniform vec3  particleColor;

// MVP & camera
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

// For fragment shader
out float lifetimePercentageToFragment;
out vec3  fragColor;
flat out float particleIDOut;
out vec3  fragPos;

void main()
{
    // Pass along unchanged values
    tfSpawnTime        = spawnTime;
    tfParticleLifetime = particleLifetime;
    tfParticleID       = particleID;
    tfParticleWeight   = particleWeight;
    fragColor          = particleColor;
    particleIDOut      = particleID;

    float elapsed      = currentTime - spawnTime;
    float calcLifetime = 0.0;
    if (particleLifetime > 0.0) {
        calcLifetime = clamp(elapsed / particleLifetime, 0.0, 1.0);
    }
    tfLifetimePercentage = calcLifetime;
    lifetimePercentageToFragment = calcLifetime;

    // If expired, skip further processing
    if (calcLifetime >= 1.0 || lifetimePercentage >= 1.0) {
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

    // Gravity integration
    vec3 adjGravity  = particleGravity * particleWeight;
    vec3 newVelocity = velocity.xyz + adjGravity * deltaTime;

    // Fluid forces (if enabled)
    if (fluidSimulation) {
        vec3 fluid = calculateFluidForces(
        newVelocity, adjGravity,
        fluidPressure, fluidViscosity,
        fluidForceMultiplier
        );
        newVelocity += fluid * deltaTime;
    }

    // Clamp velocity
    float speed = length(newVelocity);
    if (speed > particleMaxVelocity) {
        newVelocity = normalize(newVelocity) * particleMaxVelocity;
    }

    // Integrate position
    vec3 newPos = position.xyz + newVelocity * deltaTime;

    // Collide with the rotated ground plane
    vec3 planeN = rotatePlaneNormal(particleGroundPlaneNormal, groundPlaneAngle);
    float dist  = dot(newPos, planeN) - particleGroundPlaneHeight;
    if (dist < 0.0) {
        newVelocity = reflect(newVelocity, planeN) * particleBounceFactor;
        float bSpeed = length(newVelocity);
        if (bSpeed > particleMaxVelocity) {
            newVelocity = normalize(newVelocity) * particleMaxVelocity;
        }
        // Push particle out of the plane boundary (note: dist is negative)
        newPos -= planeN * dist;
    }

    // Set particle size based on distance to camera
    vec3 toCam = cameraPosition - newPos;
    float dCam = length(toCam);
    float size = particleSize / dCam;
    gl_PointSize = size;

    // Set transform feedback outputs
    tfPosition = vec4(newPos, 1.0);
    tfVelocity = vec4(newVelocity, 0.0);

    // Compute final clip-space position for rendering
    vec4 worldPos = model * vec4(newPos, 1.0);
    gl_Position   = projection * view * worldPos;
    fragPos       = worldPos.xyz;
}
