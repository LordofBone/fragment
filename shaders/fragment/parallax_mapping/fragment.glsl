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
uniform sampler2D shadowMap;

// Additional toggles
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
// Lighting mode selector: 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;
uniform bool shadowingEnabled;

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
    vec3 normal = texture(normalMap, newTexCoords, textureLodLevel).rgb;
    normal = normalize(normal * 2.0 - 1.0);

    vec3 worldViewDir = normalize(viewPosition - FragPos);

    // Reflection from environment
    vec3 reflectDir = reflect(-worldViewDir, normal);
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

    if (lightingMode == 0)
    {
        finalColor = computeDiffuseLighting(normal, viewDir, FragPos, baseColor);
    }
    else if (lightingMode == 1)
    {
        finalColor = computePhongLighting(normal, viewDir, FragPos, baseColor);
    }
    else if (lightingMode == 2)
    {
        // PBR (includes environment reflection inside)
        finalColor = computePBRLighting(normal, viewDir, FragPos, baseColor);
    }

    finalColor *= (1.0 - shadow);

    vec3 result = finalColor;

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
