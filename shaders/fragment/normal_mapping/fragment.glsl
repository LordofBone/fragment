#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D shadowMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform vec3 viewPosition;
uniform float lightStrengths[10];
uniform float textureLodLevel;

uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;
uniform vec3 ambientColor;

// Tone mapping functions
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

    // PCF
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

vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 FragPos, vec2 TexCoords) {
    vec3 diffuseColor = texture(diffuseMap, TexCoords).rgb;
    vec3 ambient = 0.1 * diffuseColor + ambientColor * diffuseColor;
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

vec3 computeDiffuseLighting(vec3 normal, vec3 FragPos, vec2 TexCoords) {
    vec3 diffuseColor = texture(diffuseMap, TexCoords).rgb;
    vec3 ambient = 0.1 * diffuseColor + ambientColor * diffuseColor;
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
    // Sample the tangent-space normal
    vec3 normalTangent = texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    // Transform it to world space
    vec3 normal = normalize(TBN * normalTangent);

    // For simplicity, assume the camera is at viewPosition (passed as a uniform if needed)
    // If not provided, you can assume the camera at (0,0,0) and adjust calculations
    // Let's assume we have a uniform vec3 viewPosition somewhere outside:
    // If not, just define it or pass it in:

    vec3 viewDir = normalize(viewPosition - FragPos);

    vec3 color;
    if (phongShading) {
        color = computePhongLighting(normal, viewDir, FragPos, TexCoords);
    } else {
        color = computeDiffuseLighting(normal, FragPos, TexCoords);
    }

    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPosLightSpace);
    }
    color = (1.0 - shadow) * color;

    if (applyToneMapping) {
        color = toneMapping(color);
    }

    if (applyGammaCorrection) {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
