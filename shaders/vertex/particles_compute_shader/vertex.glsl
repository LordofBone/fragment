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

        // Calculate color based on lifetimePercentage
        fragColor = mix(vec3(1.0, 1.0, 1.0), vec3(1.0, 0.0, 0.0), particle.lifetimePercentage);

        // Set point size if using points
        gl_PointSize = 5.0;
    }
}
