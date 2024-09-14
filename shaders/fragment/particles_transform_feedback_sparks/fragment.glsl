#version 430

in vec3 fragColor;// Base color from vertex shader (input color)
in float tfLifetimePercentage;// Particle's lifetime percentage passed from vertex shader
flat in float particleIDOut;// Particle ID passed from the vertex shader

out vec4 finalColor;

// Pseudo-random function based on particle ID and fragment coordinates
float generateRandomValue(vec2 uv, float id) {
    return fract(sin(dot(uv + id, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    // Calculate alpha based on the lifetime of the particle (fading effect)
    float alpha = clamp(1.0 - tfLifetimePercentage, 0.0, 1.0);

    // Generate a random value based on particle ID and fragment's local position for color variation within the particle
    vec2 localCoords = gl_PointCoord;// gl_PointCoord gives the local coordinates within the particle (0.0 to 1.0)
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Apply the color variation to the base color
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);// Vary color by ±10%

    // Adjust color based on lifetime to simulate cooling (start hot, then cool to black)
    vec3 fadeColor = vec3(0.0, 0.0, 0.0);

    // Interpolate from the varied color to black over the particle's lifetime
    vec3 cooledColor = mix(variedColor, fadeColor, tfLifetimePercentage);

    // Output the final color with fading alpha
    finalColor = vec4(cooledColor, alpha);
}
