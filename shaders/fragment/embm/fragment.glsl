#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform vec3 viewPosition;
uniform float lightStrengths[10];
uniform float textureLodLevel;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;

vec3 Uncharted2Tonemap(vec3 x) {
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;
    return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F))-E/F;
}

vec3 toneMapping(vec3 color) {
    vec3 curr = Uncharted2Tonemap(color * 2.0);
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

float ShadowCalculation(vec4 fragPosLightSpace)
{
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    float currentDepth = projCoords.z;
    float bias = 0.005;

    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    for (int x = -1; x <= 1; ++x) {
        for (int y = -1; y <= 1; ++y) {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y)*texelSize).r;
            shadow += (currentDepth - bias > pcfDepth) ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;
    return shadow;
}

vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 FragPos, vec3 diffuseColor) {
    vec3 ambient = 0.1 * diffuseColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specularColor = vec3(1.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * diffuseColor * lightColors[i] * lightStrengths[i];

        vec3 reflectDir = reflect(-lightDir, normal);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
        specular += spec * specularColor * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeDiffuseLighting(vec3 normal, vec3 FragPos, vec3 diffuseColor) {
    vec3 ambient = 0.1 * diffuseColor;
    vec3 diffuse = vec3(0.0);
    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * diffuseColor * lightColors[i] * lightStrengths[i];
    }
    return ambient + diffuse;
}

void main()
{
    // Sample tangent-space normal
    vec3 normalTangent = texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalTangent);

    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;

    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPosLightSpace);
    }

    vec3 lighting = vec3(0.0);
    if (phongShading) {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    } else {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    lighting = (1.0 - shadow) * lighting;

    // Mix lighting and environment color. You previously used "envColor * height"
    // If you want a specific formula, adjust as desired:
    vec3 result = lighting + envColor;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
