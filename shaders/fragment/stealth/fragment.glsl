#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos[10];

out vec4 FragColor;

uniform mat4 model;// Model transformation matrix

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform sampler2D screenTexture;// The screen texture for background distortion
uniform samplerCube environmentMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform vec3 viewPosition;
uniform float lightStrengths[10];
uniform float textureLodLevel;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float transparency;// Control overall transparency
uniform bool phongShading;// Control Phong shading
uniform float distortionStrength;// Control distortion strength
uniform float reflectionStrength;// Control reflection strength

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
    // Transform FragPos by the model matrix (if needed)
    vec3 transformedFragPos = vec3(model * vec4(FragPos, 1.0));

    // Transform the normal by the model matrix (if needed)
    vec3 transformedNormal = normalize(mat3(transpose(inverse(model))) * Normal);

    vec3 normal = normalize(transformedNormal + texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0);
    float height = texture(displacementMap, TexCoords, textureLodLevel).r;

    vec3 viewDir = normalize(viewPosition - transformedFragPos);
    vec3 reflectDir = reflect(viewDir, normal);

    vec3 envColor = vec3(0.0);
    if (envMapLodLevel > 0.0) {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
    }

    // Apply distortion using the normal map
    vec2 distortedCoords = TexCoords + normal.xy * distortionStrength;// Use uniform for distortion strength
    vec3 backgroundColor = texture(screenTexture, distortedCoords).rgb;

    // If Phong shading is enabled, compute lighting, otherwise, use diffuse color
    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 lighting = phongShading ? computePhongLighting(normal, viewDir, transformedFragPos, diffuseColor) : diffuseColor;

    // Blend background distortion and lighting with controlled reflection strength
    vec3 result = mix(backgroundColor, lighting, transparency) + envColor * reflectionStrength;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);

    // Set the final color with configurable transparency
    FragColor = vec4(result, transparency);
}
