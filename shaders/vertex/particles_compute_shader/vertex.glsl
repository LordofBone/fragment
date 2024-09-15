#version 430 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 velocity;
layout(location = 2) in float spawnTime;
layout(location = 3) in float particleLifetime;
layout(location = 4) in float particleID;
layout(location = 5) in float lifetimePercentage;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform vec3 cameraPosition;

out vec3 fragColor;

void main() {
    if (lifetimePercentage >= 1.0) {
        // Discard the vertex if the particle is expired
        gl_Position = vec4(0.0);
    } else {
        vec4 worldPosition = model * vec4(position, 1.0);
        gl_Position = projection * view * worldPosition;

        // Calculate color based on lifetimePercentage
        fragColor = mix(vec3(1.0, 1.0, 1.0), vec3(1.0, 0.0, 0.0), lifetimePercentage);

        // Set point size if using points
        gl_PointSize = 5.0;
    }
}
