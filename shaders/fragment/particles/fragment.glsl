#version 430

in vec3 fragColor;// Base color from vertex shader (input color)
in float lifetimePercentageToFragment;// Particle's lifetime percentage passed from vertex shader
flat in float particleIDOut;// Particle ID passed from the vertex shader
in vec3 fragPos;// Particle's position in world space, passed from vertex shader

out vec4 finalColor;

// Uniforms for controlling fade behavior
uniform vec3 particleFadeColor;// Color to fade to when fadeToColor is false
uniform bool particleFadeToColor;// Boolean flag to decide if particles fade by alpha or fade to fadeColor
uniform bool smoothEdges;// Flag to control smooth edges

// Lighting and shading uniforms
uniform vec3 lightPositions[10];// Array of light positions in world space
uniform vec3 lightColors[10];// Array of light colors
uniform float lightStrengths[10];// Array of light strengths
uniform vec3 viewPosition;// Position of the camera/viewer in world space
uniform float opacity;// Base opacity of the particle color
uniform float shininess;// Shininess factor for specular reflection
uniform bool phongShading;// Flag to control Phong shading

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

        // Diffuse shading
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];

        // Blinn-Phong specular shading
        vec3 halfwayDir = normalize(lightDir + viewDir);
        float specAngle = max(dot(normal, halfwayDir), 0.0);
        float spec = pow(specAngle, shininess);
        specular += attenuation * spec * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeDiffuseLighting(vec3 normal, vec3 fragPos, vec3 baseColor) {
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = lightPositions[i] - fragPos;
        float distance = length(lightDir);
        lightDir = normalize(lightDir);

        // Light attenuation
        float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));

        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];
    }

    return ambient + diffuse;
}

void main() {
    // Generate a random value based on particle ID and fragment's local position for color variation within the particle
    vec2 localCoords = gl_PointCoord;// gl_PointCoord gives the local coordinates within the particle (0.0 to 1.0)
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Apply the color variation to the base color
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);// Vary color by ±10%

    // Conditionally fade based on the fadeToColor flag
    vec3 baseColor;
    if (particleFadeToColor) {
        // Fade to the specified fadeColor over the particle's lifetime
        baseColor = mix(variedColor, particleFadeColor, lifetimePercentageToFragment);
    } else {
        // No color transition
        baseColor = variedColor;
    }

    // Compute per-fragment normal vector to simulate a spherical particle
    vec2 centeredCoord = gl_PointCoord * 2.0 - 0.10;// Ranges from -1.0 to 1.0
    float distSquared = dot(centeredCoord, centeredCoord);

    if (distSquared > 1.0) {
        discard;// Outside the circle, discard the fragment
    }

    float z = sqrt(max(1.0 - distSquared, 0.0));
    vec3 normal = vec3(centeredCoord, z);
    normal = normalize(normal);

    // Compute view direction
    vec3 viewDir = normalize(viewPosition - fragPos);

    // Select between Phong lighting and diffuse-only lighting
    vec3 finalColorRGB;
    if (phongShading) {
        finalColorRGB = computePhongLighting(normal, viewDir, fragPos, baseColor);
    } else {
        finalColorRGB = computeDiffuseLighting(normal, fragPos, baseColor);
    }

    // Calculate alpha based on lifetime, smooth edges, and base opacity
    float alphaBase;
    if (smoothEdges) {
        float edgeFactor = 1.0 - distSquared;
        alphaBase = edgeFactor * (1.0 - lifetimePercentageToFragment);
    } else {
        alphaBase = 1.0 - lifetimePercentageToFragment;
    }

    // Incorporate `opacity` parameter
    float alpha = clamp(alphaBase * opacity, 0.0, 1.0);

    // Output the final color with the calculated alpha
    finalColor = vec4(finalColorRGB, alpha);
}
