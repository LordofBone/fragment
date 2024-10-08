#version 430 core

// Define the particle structure (same as in the compute shader)
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

// Camera uniforms for view and projection matrices
uniform mat4 view;// View matrix
uniform mat4 projection;// Projection matrix
uniform vec3 cameraPosition;// Position of the camera in world space

// New uniform for model matrix to apply transformations (translation, scaling, rotation)
uniform mat4 model;// Model matrix

uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle

// Outputs to fragment shader
out float lifetimePercentageToFragment;
out vec3 fragColor;
flat out float particleIDOut;// Particle ID passed to the fragment shader

void main() {
    uint index = gl_VertexID;// Use the vertex ID to access the correct particle

    Particle particle = particles[index];// Fetch the particle data from the SSBO

    if (particle.lifetimePercentage >= 1.0) {
        // Discard the vertex if the particle is expired
        gl_Position = vec4(0.0);
    } else {
        vec4 worldPosition = model * particle.position;
        gl_Position = projection * view * worldPosition;

        // Pass the lifetime percentage to the fragment shader
        lifetimePercentageToFragment = particle.lifetimePercentage;

        // Adjust particle size based on distance from the camera
        vec3 particleToCamera = cameraPosition - particle.position.xyz;
        float distanceFromCamera = length(particleToCamera);
        float adjustedSize = particleSize / distanceFromCamera;

        // Pass the base color to the fragment shader
        fragColor = particleColor;

        // Pass the particle ID to the fragment shader
        particleIDOut = particle.particleID;

        // Set point size if using points
        gl_PointSize = adjustedSize;
    }
}
