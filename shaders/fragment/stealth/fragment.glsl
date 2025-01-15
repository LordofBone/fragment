#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

// Textures
uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D screenTexture;
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

// (lightPositions, lightColors, lightStrengths are in common_funcs.glsl)
uniform vec3 viewPosition;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float opacity;
uniform bool phongShading;
uniform float distortionStrength;
uniform float reflectionStrength;
uniform float environmentMapStrength;
uniform bool screenFacingPlanarTexture;
uniform bool warped;
uniform bool shadowingEnabled;

void main()
{
    vec2 baseTexCoords = TexCoords;

    // Normal
    vec3 normalFromMap = texture(normalMap, baseTexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalFromMap);

    vec3 viewDir = normalize(viewPosition - FragPos);

    // Reflect direction
    vec3 reflectDir = reflect(viewDir, warped ? FragPos : normal);
    reflectDir = normalize(reflectDir);

    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 envColor = vec3(0.0);

    if (dot(viewDir, normal) > 0.0)
    {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        envColor = mix(fallbackColor, envColor, step(0.05, length(envColor)));
    }
    else
    {
        envColor = fallbackColor;
    }

    envColor *= environmentMapStrength * reflectionStrength;

    vec3 diffuseColor = texture(diffuseMap, baseTexCoords, textureLodLevel).rgb;

    // Screen-distorted background
    vec2 reflectionTexCoords = (reflectDir.xy + vec2(1.0)) * 0.5;
    vec2 normalDistortion = (texture(normalMap, baseTexCoords).rg * 2.0 - 1.0) * distortionStrength;
    vec2 distortedCoords = screenFacingPlanarTexture ?
    reflectionTexCoords + normalDistortion :
    baseTexCoords + normalDistortion;

    vec3 backgroundColor = texture(screenTexture, clamp(distortedCoords, 0.0, 1.0)).rgb;
    if (length(backgroundColor) < 0.05)
    {
        backgroundColor = fallbackColor;
    }

    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // Lighting
    vec3 lighting;
    if (phongShading)
    {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    }
    else
    {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }
    lighting *= (1.0 - shadow);

    // Combine
    vec3 result = mix(backgroundColor, lighting, opacity) + envColor;

    if (applyToneMapping)
    {
        result = toneMapping(result);
    }
    if (applyGammaCorrection)
    {
        result = pow(result, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(result, 0.0, 1.0), opacity);
}
