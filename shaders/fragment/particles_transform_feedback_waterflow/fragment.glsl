#version 430

in vec3 fragColor;// The color passed from the vertex shader
in float particleLifetime;// Particle's current lifetime (0.0 to 1.0)

out vec4 color;// Final output color

// Uniforms for water-like effects
uniform vec3 lightDirection;// Direction of light for specular highlights
uniform vec3 viewDirection;// Direction of the viewer/camera
uniform float refractionFactor;// Refraction intensity
uniform float reflectionFactor;// Reflection intensity
uniform float waterShininess;// Shininess for specular highlights

void main() {
    // Simulate water reflection by calculating reflection based on the light and view directions
    vec3 reflectDir = reflect(-lightDirection, normalize(fragColor));
    float reflection = max(dot(reflectDir, viewDirection), 0.0);

    // Simulate water refraction by bending the light through the particles
    float refraction = 1.0 - pow(1.0 - dot(viewDirection, fragColor), 2.0);

    // Blend the reflection and refraction to get a water-like effect
    vec3 waterEffect = mix(fragColor * refractionFactor, fragColor * reflectionFactor * reflection, 0.5);

    // Add a simple fade-out effect based on the particle's lifetime
    float fade = 1.0 - particleLifetime;

    // Add some specular highlights to simulate shiny water
    vec3 specular = pow(reflection, waterShininess) * vec3(1.0);

    // Combine all effects
    vec3 finalColor = mix(fragColor * fade, waterEffect, 0.5) + specular * fade;

    // Output the final color with alpha for transparency
    color = vec4(finalColor, fade);// Fade based on lifetime
}
