#version 430

in vec3 fragColor;// Base color from vertex shader (input color)
in float lifetimePercentage;// Particle's lifetime percentage passed from vertex shader
flat in float particleIDOut;// Particle ID passed from the vertex shader

out vec4 finalColor;

// Uniforms for water-like effects with default values
uniform vec3 lightDirection = vec3(0.0, -1.0, 0.0);// Default light direction (downward)
uniform vec3 viewDirection = vec3(0.0, 0.0, 1.0);// Default view direction (forward)
uniform float refractionFactor = 0.5;// Default refraction intensity
uniform float reflectionFactor = 0.5;// Default reflection intensity
uniform float waterShininess = 9.0;// Default shininess for specular highlights

// Pseudo-random function based on particle ID and fragment coordinates
float generateRandomValue(vec2 uv, float id) {
    return fract(sin(dot(uv + id, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    // Calculate alpha based on the lifetime of the particle (fading effect)
    float alpha = clamp(1.0 - lifetimePercentage, 0.0, 1.0);

    // Generate a random value based on particle ID and fragment's local position for color variation within the particle
    vec2 localCoords = gl_PointCoord;// gl_PointCoord gives the local coordinates within the particle (0.0 to 1.0)
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Apply the color variation to the base color
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);// Vary color by ±10%

    // Simulate water reflection by calculating reflection based on the light and view directions
    vec3 reflectDir = reflect(-lightDirection, normalize(variedColor));
    float reflection = max(dot(reflectDir, viewDirection), 0.0);

    // Simulate water refraction by bending the light through the particles
    float refraction = 1.0 - pow(1.0 - dot(viewDirection, variedColor), 2.0);

    // Blend the reflection and refraction to get a water-like effect
    vec3 waterEffect = mix(variedColor * refractionFactor, variedColor * reflectionFactor * reflection, 0.5);

    // Add specular highlights to simulate shiny water
    vec3 specular = pow(reflection, waterShininess) * vec3(1.0);

    // Combine all effects with a fade-out based on the particle's lifetime
    vec3 finalColorVec = mix(variedColor * alpha, waterEffect, 0.5) + specular * alpha;

    // Output the final color with fading alpha for transparency
    finalColor = vec4(finalColorVec, alpha);
}
