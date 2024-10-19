#version 430

layout (location = 0) in vec4 position;// Input particle position
layout (location = 1) in float lifetimePercentage;// Lifetime percentage from CPU
layout (location = 2) in float particleID;// The ID of the particle

// Camera uniforms for view and projection matrices
uniform mat4 view;// View matrix
uniform mat4 projection;// Projection matrix
uniform vec3 cameraPosition;// Position of the camera in world space

// New uniform for model matrix to apply transformations (translation, scaling, rotation)
uniform mat4 model;// Model matrix

uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle

// Output to the fragment shader
out vec3 fragColor;
out float lifetimePercentageToFragment;
flat out float particleIDOut;
out vec3 fragPos;// Particle's position in world space

void main() {
    // Apply transformations: model, view, projection
    vec4 worldPosition = model * position;
    gl_Position = projection * view * worldPosition;

    // Adjust particle size based on distance from the camera
    vec3 particleToCamera = cameraPosition - worldPosition.xyz;
    float distanceFromCamera = length(particleToCamera);
    float adjustedSize = particleSize / distanceFromCamera;

    // Set the size of the particle for point rendering
    gl_PointSize = adjustedSize;

    // Pass the color and lifetime percentage to the fragment shader
    fragColor = particleColor;
    lifetimePercentageToFragment = lifetimePercentage;
    particleIDOut = particleID;

    // Pass the fragment position in world space
    fragPos = worldPosition.xyz;
}
