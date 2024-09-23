#version 430

in vec3 fragColor;// Base color from vertex shader (input color)
in float lifetimePercentageToFragment;// Particle's lifetime percentage passed from vertex shader
flat in float particleIDOut;// Particle ID passed from the vertex shader

out vec4 finalColor;

// Uniforms for controlling fade behavior
uniform vec3 particleFadeColor;// Color to fade to when fadeToColor is false
uniform bool particleFadeToColor;// Boolean flag to decide if particles fade by alpha or fade to fadeColor

// Pseudo-random function based on particle ID and fragment coordinates
float generateRandomValue(vec2 uv, float id) {
    return fract(sin(dot(uv + id, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    // Calculate alpha based on the lifetime of the particle (fading effect)
    float alpha = clamp(1.0 - lifetimePercentageToFragment, 0.0, 1.0);

    // Generate a random value based on particle ID and fragment's local position for color variation within the particle
    vec2 localCoords = gl_PointCoord;// gl_PointCoord gives the local coordinates within the particle (0.0 to 1.0)
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Apply the color variation to the base color
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);// Vary color by ±10%

    // Conditionally fade based on the fadeToColor flag
    vec3 finalColorRGB;
    if (particleFadeToColor) {
        // Fade to the specified fadeColor over the particle's lifetime
        finalColorRGB = mix(variedColor, particleFadeColor, lifetimePercentageToFragment);
    } else {
        // Fade out by alpha (no color transition)
        finalColorRGB = variedColor;
    }

    // Output the final color with the calculated alpha
    finalColor = vec4(finalColorRGB, alpha);
}
