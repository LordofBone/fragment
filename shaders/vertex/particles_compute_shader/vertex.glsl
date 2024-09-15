#version 430 core

// Define the particle structure (same as in the compute shader)
struct Particle {
    vec3 position;
    vec3 velocity;
    float spawnTime;
    float lifetime;
    float particleID;
    float lifetimePercentage;
};

// Bind the particle buffer as a shader storage buffer
layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform float particleSize;// Size of the particle
uniform vec3 particleColor;// Base color of the particle

out vec3 fragColor;

void main() {
    uint index = gl_VertexID;// Use the vertex ID to access the correct particle

    Particle particle = particles[index];// Fetch the particle data from the SSBO

    if (particle.lifetimePercentage >= 1.0) {
        // Discard the vertex if the particle is expired
        gl_Position = vec4(0.0);
    } else {
        vec4 worldPosition = model * vec4(particle.position, 1.0);
        gl_Position = projection * view * worldPosition;

        // Adjust color based on lifetime to simulate cooling (start hot, then cool to black)
        vec3 fadeColor = vec3(0.0, 0.0, 0.0);

        // Interpolate from the varied color to black over the particle's lifetime
        fragColor = mix(particleColor, fadeColor, particle.lifetimePercentage);

        // Set point size if using points
        gl_PointSize = particleSize;
    }
}
