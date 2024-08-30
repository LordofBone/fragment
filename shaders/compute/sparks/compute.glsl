#version 430

layout(local_size_x = 128) in;

struct Particle {
    vec3 position;
    vec3 velocity;
};

layout(std430, binding = 0) buffer Particles {
    Particle particles[];
};

uniform float deltaTime;
uniform vec3 gravity;
uniform float bounceFactor;
uniform vec3 groundPlaneNormal;
uniform float groundPlaneHeight;

void main() {
    uint idx = gl_GlobalInvocationID.x;

    // Update velocity with gravity
    particles[idx].velocity += gravity * deltaTime;

    // Update position
    particles[idx].position += particles[idx].velocity * deltaTime;

    // Handle ground collision and bounce
    if (dot(particles[idx].position, groundPlaneNormal) < groundPlaneHeight) {
        particles[idx].velocity = reflect(particles[idx].velocity, groundPlaneNormal) * bounceFactor;
        particles[idx].position = particles[idx].position + groundPlaneNormal * (groundPlaneHeight - dot(particles[idx].position, groundPlaneNormal));
    }
}
