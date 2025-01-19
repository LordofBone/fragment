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

// Light/camera uniforms
uniform vec3 viewPosition;

// Another uniform controlling how many MIPs your env map might have
//uniform float envMapLodLevel;       // Might be used in old method

// Feature toggles
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool shadowingEnabled;

// Instead of bool `phongShading`, we have an int:
uniform int lightingMode;// 0 => diffuse, 1 => Phong, 2 => PBR

void main()
{
    // 1) Build the normal from the tangent-space normal map
    //    (assuming a normalMap is present, otherwise skip)
    vec3 normalTangent = texture(normalMap, TexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 N = normalize(TBN * normalTangent);

    // 2) View direction
    vec3 V = normalize(viewPosition - FragPos);

    // 3) Base diffuse color from texture
    vec3 baseColor = texture(diffuseMap, TexCoords, textureLodLevel).rgb;

    // 4) Shadow factor (0..1). If shadowingEnabled is false, shadow=0
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // 5) Lighting
    vec3 lighting = vec3(0.0);
    if (lightingMode == 0)
    {
        // Pure diffuse
        lighting = computeDiffuseLighting(N, V, FragPos, baseColor);
    }
    else if (lightingMode == 1)
    {
        // Legacy Phong
        lighting = computePhongLighting(N, V, FragPos, baseColor);
    }
    else if (lightingMode == 2)
    {
        // PBR (includes environment reflection inside)
        lighting = computePBRLighting(N, V, FragPos, baseColor);
    }

    // 6) Apply shadow: (1.0 - shadow)
    lighting *= (1.0 - shadow);

    // 7) For modes 0 or 1, add environment map *outside* the lighting function
    //    (like your old method). For mode 2, the environment reflection
    //    is already integrated in computePBRLighting.
    vec3 result;
    if (lightingMode == 2)
    {
        // PBR already includes environment reflection
        result = lighting;
    }
    else
    {
        // Old approach: reflect direction + separate environment pass
        //        vec3 reflectDir = reflect(-V, N);
        //        // We might use envMapLodLevel as a uniform for the old approach:
        ////        vec3 envColor   = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        //        vec3 envColor = sampleEnvironmentMapLod(reflectDir).rgb;
        //
        //        // Then blend in that environment color additively
        //        // "mix(lighting, lighting + envColor, environmentMapStrength)"
        //        result = mix(lighting, lighting + envColor, environmentMapStrength);

        result = lighting;
    }

    // 8) Tone mapping
    if (applyToneMapping)
    {
        result = toneMapping(result);
    }

    // 9) Gamma correction
    if (applyGammaCorrection)
    {
        // typical sRGB gamma ~2.2
        result = pow(result, vec3(1.0/2.2));
    }

    // 10) Clamp & output
    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
