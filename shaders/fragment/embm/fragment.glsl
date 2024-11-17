#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
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

vec3 computeDiffuseLighting(vec3 normal, vec3 FragPos, vec3 diffuseColor) {
    vec3 ambient = 0.1 * diffuseColor;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += lightColors[i] * diff * diffuseColor * lightStrengths[i];
    }

    return ambient + diffuse;
}

float ShadowCalculation(vec4 fragPosLightSpace)
{
    // Perform perspective divide
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    // Transform to [0,1] range
    projCoords = projCoords * 0.5 + 0.5;
    // Get closest depth value from light's perspective (using [0,1] range fragPosLightSpace as coords)
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    // Get depth of current fragment from light's perspective
    float currentDepth = projCoords.z;
    // Check whether current fragment is in shadow
    float bias = 0.005;
    float shadow = currentDepth - bias > closestDepth ? 1.0 : 0.0;

    // Optionally, use Percentage-Closer Filtering (PCF) for softer shadows
    // float shadow = 0.0;
    // vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    // for(int x = -1; x <= 1; ++x)
    // {
    //     for(int y = -1; y <= 1; ++y)
    //     {
    //         float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
    //         shadow += currentDepth - bias > pcfDepth ? 1.0 : 0.0;
    //     }
    // }
    // shadow /= 9.0;

    return shadow;
}

void main()
{
    vec3 normal = normalize(Normal + texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0);
    float height = texture(displacementMap, TexCoords, textureLodLevel).r;

    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 reflectDir = reflect(viewDir, normal);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 lighting = vec3(0.0);

    // Calculate shadow
    float shadow = ShadowCalculation(FragPosLightSpace);

    if (phongShading) {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    } else {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    // Apply shadow to lighting
    lighting = (1.0 - shadow) * lighting;

    vec3 result = lighting + envColor * height;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
