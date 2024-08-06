#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform samplerCube environmentMap;

uniform vec3 lightPositions[10];// Support for up to 10 lights
uniform vec3 lightColors[10];
uniform vec3 viewPosition;
uniform float lightStrengths[10];// Strength for each light
uniform float textureLodLevel;// LOD level for textures
uniform float envMapLodLevel;// LOD level for environment map
uniform bool applyToneMapping;// Enable/disable tone mapping
uniform bool applyGammaCorrection;// Enable/disable gamma correction

vec3 Uncharted2Tonemap(vec3 x) {
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;

    return ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F;
}

vec3 toneMapping(vec3 color) {
    vec3 curr = Uncharted2Tonemap(color * 2.0);// Pre-exposure
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

void main()
{
    // Retrieve normal from normal map
    vec3 normal = texture(normalMap, TexCoords, textureLodLevel).rgb;
    normal = normalize(normal * 2.0 - 1.0);// Transform normal vector to range [-1, 1]

    // Retrieve height from displacement map
    float height = texture(displacementMap, TexCoords, textureLodLevel).r;

    // Calculate view direction
    vec3 viewDir = normalize(viewPosition - FragPos);

    // Calculate the reflection vector
    vec3 reflectDir = reflect(viewDir, normal);

    // Retrieve the environment color with anisotropic filtering
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    // Calculate ambient lighting
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords, textureLodLevel).rgb;

    // Initialize diffuse and specular lighting
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    // Loop through all lights
    for (int i = 0; i < 10; i++) {
        // Calculate light direction
        vec3 lightDir = normalize(lightPositions[i] - FragPos);

        // Calculate diffuse lighting
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * texture(diffuseMap, TexCoords, textureLodLevel).rgb * lightColors[i] * lightStrengths[i];

        // Calculate specular lighting
        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normal, halfwayDir), 0.0), 64.0);
        specular += spec * lightColors[i] * lightStrengths[i];
    }

    // Combine results in HDR
    vec3 result = ambient + diffuse + specular + envColor * height;

    // Apply tone mapping if enabled
    if (applyToneMapping) {
        result = toneMapping(result);
    }

    // Apply gamma correction if enabled
    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    // Clamp final color to avoid exceeding brightness levels
    result = clamp(result, 0.0, 1.0);

    FragColor = vec4(result, 1.0);
}
