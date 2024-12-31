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
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

// Light/camera uniforms
uniform vec3 viewPosition;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;
uniform float environmentMapStrength;

void main()
{
    // Sample tangent-space normal
    vec3 normalTangent = texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalTangent);

    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;

    // Reflection from environment
    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    // Shadow
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // Lighting
    vec3 lighting = vec3(0.0);
    if (phongShading)
    {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    }
    else
    {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    lighting = (1.0 - shadow) * lighting;

    // Blend with environment
    vec3 result = mix(lighting, lighting + envColor, environmentMapStrength);

    if (applyToneMapping)
    {
        result = toneMapping(result);
    }
    if (applyGammaCorrection)
    {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
