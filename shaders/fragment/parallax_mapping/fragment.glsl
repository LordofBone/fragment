#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentLightPos;
in vec3 TangentViewPos;
in vec3 TangentFragPos;
in vec4 FragPosLightSpace;
in float FragPosW;

out vec4 FragColor;

// Textures
uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

// Additional toggles
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;
uniform float envSpecularStrength;

uniform mat4 view;
uniform mat4 projection;
uniform vec3 viewPosition;

void main()
{
    // Transform view direction into tangent space
    vec3 viewDir = normalize(TangentViewPos - TangentFragPos);

    // Apply Enhanced POM with Depth Correction
    float depthOffset = 0.0;
    vec2 newTexCoords = ParallaxOcclusionMapping(TexCoords, viewDir, depthOffset);

    // Recompute normal
    vec3 norm = texture(normalMap, newTexCoords, textureLodLevel).rgb;
    norm = normalize(norm * 2.0 - 1.0);

    vec3 worldViewDir = normalize(viewPosition - FragPos);

    // Reflection from environment
    vec3 reflectDir = reflect(-worldViewDir, norm);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    // Shadow
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // Lighting
    vec3 finalColor;
    vec3 baseColor = texture(diffuseMap, newTexCoords, textureLodLevel).rgb;

    if (phongShading)
    {
        finalColor = computePhongLighting(norm, worldViewDir, FragPos, baseColor);
    }
    else
    {
        finalColor = computeDiffuseLighting(norm, FragPos, baseColor);
    }

    finalColor *= (1.0 - shadow);

    // Fresnel
    float fresnel = pow(1.0 - dot(worldViewDir, norm), 3.0);
    vec3 reflection = mix(envColor, vec3(1.0), fresnel);

    // Combine
    vec3 result = finalColor + reflection * envSpecularStrength;

    if (applyToneMapping)
    {
        result = toneMapping(result);
    }
    if (applyGammaCorrection)
    {
        result = pow(result, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(result, 0.0, 1.0), 1.0);

    // Depth Correction
    float correctedDepth = clamp(gl_FragCoord.z - depthOffset, 0.0, 1.0);
    gl_FragDepth = correctedDepth;
}
