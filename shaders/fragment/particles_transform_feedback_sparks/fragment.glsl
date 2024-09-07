#version 430

in vec3 fragColor;// Base color from vertex shader (input color)
in float lifetimePercentage;// Particle's lifetime percentage passed from vertex shader

out vec4 finalColor;

void main() {
    // Calculate alpha based on the lifetime of the particle (fading effect)
    float alpha = clamp(1.0 - lifetimePercentage, 0.0, 1.0);

    // Adjust color based on lifetime to simulate cooling (start hot, then cool to base color)
    vec3 fadeColor = vec3(0.0, 0.0, 0.0);

    // Interpolate from the hot color to the input fragColor over the particle's lifetime
    vec3 cooledColor = mix(fragColor, fadeColor, lifetimePercentage);

    // Output the final color with fading alpha
    finalColor = vec4(cooledColor, 0.2);
}
