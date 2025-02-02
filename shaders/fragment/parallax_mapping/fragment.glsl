#version 330 core
#include "glsl_utilities.glsl"

// ---------------------------------------------------------------------
// Vertex -> Fragment Inputs
// ---------------------------------------------------------------------
in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec4 FragPosLightSpace;
in float FragPosW;

// TBN rows
in vec3 TBNrow0;
in vec3 TBNrow1;
in vec3 TBNrow2;

// ---------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------
out vec4 FragColor;

// ---------------------------------------------------------------------
// Uniforms
// ---------------------------------------------------------------------
uniform sampler2D diffuseMap;
uniform sampler2D shadowMap;

// Toggles
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool shadowingEnabled;

// 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;

// Camera transforms
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;
uniform vec3 viewPosition;

void main()
{
    // --------------------------------------------------------------
    // 1) Reconstruct TBN (tangent->world)
    // --------------------------------------------------------------
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);

    // --------------------------------------------------------------
    // 2) Parallax Occlusion Mapping in tangent space
    // --------------------------------------------------------------
    float depthOffset = 0.0;
    vec3 viewDirTangent = normalize(TangentViewPos - TangentFragPos);
    vec2 parallaxCoords = TexCoords;

    if (pomHeightScale > 0.0)
    {
        parallaxCoords = ParallaxOcclusionMapping(TexCoords, viewDirTangent, depthOffset);
        parallaxCoords = clamp(parallaxCoords, 0.0, 1.0);
    }

    // --------------------------------------------------------------
    // 3) Sample normal map in tangent space -> world space
    // --------------------------------------------------------------
    vec3 normalTex = texture(normalMap, parallaxCoords, textureLodLevel).rgb;
    normalTex = normalTex * 2.0 - 1.0;
    vec3 finalNormal = normalize(TBN * normalTex);

    // --------------------------------------------------------------
    // 4) World-space view direction
    // --------------------------------------------------------------
    vec3 worldViewDir = normalize(viewPosition - FragPos);

    // --------------------------------------------------------------
    // 5) Shadows
    // --------------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap, FragPos);
    }

    // --------------------------------------------------------------
    // 6) Local lighting
    // --------------------------------------------------------------
    vec3 baseColor = texture(diffuseMap, parallaxCoords, textureLodLevel).rgb;
    vec3 lightingColor = vec3(0.0);

    if (lightingMode == 0)
    {
        lightingColor = computeDiffuseLighting(finalNormal, worldViewDir, FragPos, baseColor, TexCoords);
    }
    else if (lightingMode == 1)
    {
        lightingColor = computePhongLighting(finalNormal, worldViewDir, FragPos, baseColor, TexCoords);
    }
    else
    {
        lightingColor = computePBRLighting(finalNormal, worldViewDir, FragPos, baseColor, TexCoords);
    }

    // Shadow
    lightingColor *= (1.0 - shadow);

    vec3 finalColor = lightingColor;

    // --------------------------------------------------------------
    // 7) ToneMapping & Gamma
    // --------------------------------------------------------------
    if (applyToneMapping)
    {
        finalColor = toneMapping(finalColor);
    }
    if (applyGammaCorrection)
    {
        finalColor = pow(finalColor, vec3(1.0/2.2));
    }

    finalColor = clamp(finalColor, 0.0, 1.0);

    // 12) Incorporate `legacyOpacity` parameter
    float alpha = clamp(legacyOpacity, 0.0, 1.0);

    FragColor = vec4(finalColor, alpha);

    // ---------------------------------------------------
    // 13) Optional Depth Correction w/ clamp
    // ---------------------------------------------------
    if (pomHeightScale > 0.0 && depthOffset != 0.0 && enableFragDepthAdjustment) {
        vec4 eyePos = view * vec4(FragPos, 1.0);

        // Call the centralized function
        adjustFragDepth(
        eyePos,
        projection,
        vec4(FragPos, 1.0),
        vec3[](TBNrow0, TBNrow1, TBNrow2),
        depthOffset,
        gl_FragDepth
        );
    } else {
        gl_FragDepth = gl_FragCoord.z;
    }
}
