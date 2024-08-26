#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform sampler2D screenTexture;
uniform samplerCube environmentMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform vec3 viewPosition;
uniform float lightStrengths[10];
uniform float textureLodLevel;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float opacity;
uniform bool phongShading;
uniform float distortionStrength;
uniform float reflectionStrength;
uniform vec3 ambientColor;
uniform bool screenFacingPlanarTexture;

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
    vec3 curr = Uncharted2Tonemap(color * 2.0);
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

vec3 computeLighting(vec3 normal, vec3 viewDir, vec3 FragPos, vec3 diffuseColor) {
    vec3 ambient = ambientColor * diffuseColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specularColor = vec3(1.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += lightColors[i] * diff * diffuseColor * lightStrengths[i];

        if (phongShading) {
            vec3 reflectDir = reflect(-lightDir, normal);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
            specular += spec * specularColor * lightColors[i] * lightStrengths[i];
        }
    }

    return ambient + diffuse + specular;
}

void main() {
    vec2 flippedTexCoords = vec2(TexCoords.x, 1.0 - TexCoords.y);

    // Calculate normal and height for displacement mapping
    vec3 normal = normalize(Normal + texture(normalMap, flippedTexCoords, textureLodLevel).rgb * 2.0 - 1.0);
    float height = texture(displacementMap, flippedTexCoords, textureLodLevel).r;

    // Calculate view and reflection directions
    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 reflectDir = reflect(viewDir, normal);

    // Normalize reflection vector to avoid extreme clamping issues
    reflectDir = normalize(reflectDir);

    vec3 envColor = vec3(0.0);
    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);

    if (dot(viewDir, normal) > 0.0) {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        envColor = mix(fallbackColor, envColor, step(0.05, length(envColor)));
    } else {
        envColor = fallbackColor;
    }

    vec3 backgroundColor = vec3(0.0);

    // Unified distortion logic for screen-facing and non-screen-facing planar textures
    vec2 reflectionTexCoords = (reflectDir.xy + vec2(1.0)) * 0.5;
    vec2 normalDistortion = (texture(normalMap, flippedTexCoords).rg * 2.0 - 1.0) * distortionStrength;

    // Apply distortion based on the normal map without affecting texture stretching
    vec2 distortedCoords = screenFacingPlanarTexture ? reflectionTexCoords + normalDistortion : flippedTexCoords + normalDistortion;

    backgroundColor = texture(screenTexture, clamp(distortedCoords, 0.0, 1.0)).rgb;

    // If backgroundColor is near black, use fallback color
    if (length(backgroundColor) < 0.05) {
        backgroundColor = fallbackColor;
    }

    vec3 diffuseColor = texture(diffuseMap, flippedTexCoords, textureLodLevel).rgb;
    vec3 lighting = computeLighting(normal, viewDir, FragPos, diffuseColor);

    vec3 result = mix(backgroundColor, lighting, opacity) + envColor * reflectionStrength;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);

    FragColor = vec4(result, opacity);
}
