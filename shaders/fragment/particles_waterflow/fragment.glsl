#version 430

in vec3 fragColor;// Base color from vertex shader (input color)
in float lifetimePercentageToFragment;// Particle's lifetime percentage passed from vertex shader
flat in float particleIDOut;// Particle ID passed from the vertex shader
in vec3 fragPos;// Particle's position in world space, passed from vertex shader

out vec4 finalColor;

// Uniforms for water-like effects
uniform vec3 lightPositions[10];// Array of light positions in world space
uniform vec3 lightColors[10];// Array of light colors
uniform float lightStrengths[10];// Array of light strengths
uniform vec3 viewPosition;// Position of the camera/viewer in world space
uniform float waterShininess = 9.0;// Default shininess for specular highlights
uniform bool phongShading;// Flag to control Phong shading
uniform bool smoothEdges;// Flag to control smooth edges

// Pseudo-random function based on particle ID and fragment coordinates
float generateRandomValue(vec2 uv, float id) {
    return fract(sin(dot(uv + id, vec2(12.9898, 78.233))) * 43758.5453);
}

vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor) {
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = lightPositions[i] - fragPos;
        float distance = length(lightDir);
        lightDir = normalize(lightDir);

        // Light attenuation
        float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));

        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];

        vec3 reflectDir = reflect(-lightDir, normal);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), waterShininess);
        specular += attenuation * spec * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

void main() {
    // Generate a random value based on particle ID and fragment's local position for color variation within the particle
    vec2 localCoords = gl_PointCoord;// gl_PointCoord gives the local coordinates within the particle (0.0 to 1.0)
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Apply the color variation to the base color
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);// Vary color by ±10%

    // Compute per-fragment normal vector to simulate a spherical particle
    vec2 centeredCoord = gl_PointCoord - 0.25;// Now ranges from -0.5 to 0.5
    float distSquared = dot(centeredCoord, centeredCoord) * 4.0;// Now ranges from 0.0 to 1.0

    if (distSquared > 1.0 + 1e-5) {
        discard;
    }

    vec3 normal = vec3(centeredCoord, sqrt(1.0 - distSquared));
    normal = normalize(normal);

    // Compute view direction
    vec3 viewDir = normalize(viewPosition - fragPos);

    vec3 finalColorVec;

    // Calculate lighting using Phong model if enabled
    if (phongShading) {
        finalColorVec = computePhongLighting(normal, viewDir, fragPos, variedColor);
    } else {
        // Simple diffuse lighting
        vec3 ambient = 0.1 * variedColor;
        vec3 diffuse = vec3(0.0);
        for (int i = 0; i < 10; ++i) {
            vec3 lightDir = lightPositions[i] - fragPos;
            float distance = length(lightDir);
            lightDir = normalize(lightDir);

            // Light attenuation
            float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));

            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += attenuation * lightColors[i] * diff * variedColor * lightStrengths[i];
        }
        finalColorVec = ambient + diffuse;
    }

    // Calculate alpha based on lifetime and smooth edges
    float alpha;
    if (smoothEdges) {
        alpha = clamp(1.0 - lifetimePercentageToFragment - distSquared, 0.0, 1.0);
    } else {
        alpha = clamp(1.0 - lifetimePercentageToFragment, 0.0, 1.0);
    }

    // Output the final color with fading alpha for transparency
    finalColor = vec4(finalColorVec, alpha);
}
