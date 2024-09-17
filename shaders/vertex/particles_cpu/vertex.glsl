#version 430

layout(location = 0) in vec3 position;// Particle position (calculated by CPU)
layout(location = 1) in float particleSize;// Particle size (optional, set on CPU or can be constant)
layout(location = 2) in vec3 particleColor;// Particle color (optional, set on CPU or can be constant)

// Uniforms for view, projection, and model matrices
uniform mat4 view;
uniform mat4 projection;
uniform mat4 model;

// Output to the fragment shader
out vec3 fragColor;

void main() {
    // Apply transformations: model, view, projection
    vec4 worldPosition = model * vec4(position, 1.0);
    gl_Position = projection * view * worldPosition;

    // Set the size of the particle for point rendering
    gl_PointSize = particleSize;

    // Pass the color to the fragment shader
    fragColor = particleColor;
}
