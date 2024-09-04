#version 430

in vec3 fragPosition;
in vec3 fragVelocity;

out vec4 finalColor;

void main() {
    // Set the final color of the particle
    // Use the velocity to influence color for a dynamic effect
    vec3 color = normalize(fragVelocity) * 0.5 + 0.5;

    // Set the final color of the fragment
    finalColor = vec4(color, 1.0);
}
