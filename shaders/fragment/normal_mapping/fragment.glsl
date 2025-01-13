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
uniform sampler2D shadowMap;

// Additional uniforms
uniform vec3 viewPosition;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;

void main()
{
    // Sample tangent-space normal
    vec3 normalTangent = texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalTangent);

    vec3 viewDir = normalize(viewPosition - FragPos);

    // Base color
    vec3 diffuseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 color;

    if (phongShading)
    {
        // Use shared function
        color = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
        // Optionally add your custom ambient
        // color += ambientColor * diffuseColor; // if desired
    }
    else
    {
        color = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    // Shadow
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    color *= (1.0 - shadow);

    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
