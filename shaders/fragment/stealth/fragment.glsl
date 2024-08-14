#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos[10];

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
uniform float transparency;
uniform bool phongShading;// Add this uniform to control Phong shading

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

vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 FragPos, vec3 diffuseColor) {
    vec3 ambient = 0.1 * diffuseColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specularColor = vec3(1.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += lightColors[i] * diff * diffuseColor * lightStrengths[i];

        vec3 reflectDir = reflect(-lightDir, normal);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
        specular += spec * specularColor * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

void main()
{
    vec3 normal = normalize(Normal + texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0);
    float height = texture(displacementMap, TexCoords, textureLodLevel).r;

    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 reflectDir = reflect(viewDir, normal);

    vec3 envColor = vec3(0.0);
    if (envMapLodLevel > 0.0) {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
    }

    // Apply distortion using the normal map
    vec2 distortedCoords = TexCoords + normal.xy * 0.1;// Adjust distortion strength here
    vec3 backgroundColor = texture(screenTexture, distortedCoords).rgb;

    // If Phong shading is enabled, compute lighting, otherwise, use diffuse color
    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 lighting = phongShading ? computePhongLighting(normal, viewDir, FragPos, diffuseColor) : diffuseColor;

    // Mix the distorted background with the lighting and environment reflection
    vec3 result = mix(backgroundColor, lighting, 0.5) + envColor * 0.3;// Adjust blending factors here

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, transparency);
}
