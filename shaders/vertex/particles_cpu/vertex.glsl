#version 430

layout (location = 0) in vec3 position;// Input particle position
layout (location = 1) in float lifetimePercentage;// Lifetime percentage from CPU
layout (location = 2) in float particleID;// The ID of the particle

// Uniforms for view, projection, and model matrices
uniform mat4 view;
uniform mat4 projection;
uniform mat4 model;

uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle

// Output to the fragment shader
out vec3 fragColor;
out float lifetimePercentageToFragment;
out float particleIDOut;

void main() {
    // Apply transformations: model, view, projection
    vec4 worldPosition = model * vec4(position, 1.0);
    gl_Position = projection * view * worldPosition;

    // Set the size of the particle for point rendering
    gl_PointSize = particleSize;

    // Pass the color and lifetime percentage to the fragment shader
    fragColor = particleColor;
    lifetimePercentageToFragment = lifetimePercentage;
    particleIDOut = particleID;
}
