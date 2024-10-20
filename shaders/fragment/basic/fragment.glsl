#version 430

in vec3 fragColor;
out vec4 color;

void main() {
    // Output the color with full opacity
    color = vec4(fragColor, 1.0);
}
