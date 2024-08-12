#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform samplerCube environmentMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];
uniform float textureLodLevel;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float envSpecularStrength;

uniform mat4 view;

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

    vec4 viewFragPos = view * vec4(FragPos, 1.0);
    vec3 viewDir = normalize(-viewFragPos.xyz);

    vec3 reflectDir = reflect(viewDir, normal);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);

    float fresnel = pow(1.0 - dot(viewDir, normal), 3.0);
    vec3 reflection = mix(envColor, vec3(1.0), fresnel);

    vec3 result = lighting + reflection * envSpecularStrength;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
