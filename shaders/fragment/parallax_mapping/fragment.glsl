#version 330 core
#include "common_funcs.glsl"

// ---------------------------------------------------------------------
// Vertex -> Fragment Inputs
// ---------------------------------------------------------------------
in vec2 TexCoords;// Base texture coordinates
in vec3 FragPos;// World-space fragment position
in vec3 Normal;// (Optional) world-space normal from VS
in vec3 TangentFragPos;// Tangent-space fragment position (for POM)
in vec3 TangentViewPos;// Tangent-space view position (for POM)
in vec4 FragPosLightSpace;// For shadow mapping
in float FragPosW;// Clip-space W if needed

// TBN rows to reconstruct T->world, B->world, N->world
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
uniform sampler2D normalMap;
uniform sampler2D shadowMap;

// Toggles & settings
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool shadowingEnabled;

// 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;

// Camera & transforms
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;
uniform vec3 viewPosition;

// More advanced Parallax Depth Correction
uniform float parallaxEyeOffsetScale = 1.0;
uniform float parallaxMaxDepthClamp  = 0.99;

// ---------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------
void main()
{
    // --------------------------------------------------------------
    // 1) Reconstruct TBN (tangent->world)
    // --------------------------------------------------------------
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);

    // --------------------------------------------------------------
    // 2) Parallax Occlusion Mapping in tangent space
    // --------------------------------------------------------------
    vec3 viewDirTangent = normalize(TangentViewPos - TangentFragPos);

    float depthOffset = 0.0;
    vec2 parallaxCoords = TexCoords;

    if (pomHeightScale > 0.0)
    {
        parallaxCoords = ParallaxOcclusionMapping(
        TexCoords,
        viewDirTangent,
        depthOffset
        );
        parallaxCoords = clamp(parallaxCoords, 0.0, 1.0);
    }

    // --------------------------------------------------------------
    // 3) Sample normal map in tangent space -> convert to world space
    // --------------------------------------------------------------
    vec3 normalTex = texture(normalMap, parallaxCoords, textureLodLevel).rgb;
    normalTex = normalTex * 2.0 - 1.0;// tangent-space normal in [-1..1]
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
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // --------------------------------------------------------------
    // 6) Local lighting
    //    (We let compute*Lighting handle environment reflection, if an environment map is present.)
    // --------------------------------------------------------------
    vec3 baseColor = texture(diffuseMap, parallaxCoords, textureLodLevel).rgb;
    vec3 lightingColor = vec3(0.0);

    if (lightingMode == 0)
    {
        // Diffuse lighting (which internally might do reflection)
        lightingColor = computeDiffuseLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }
    else if (lightingMode == 1)
    {
        // Phong lighting (which internally might do reflection)
        lightingColor = computePhongLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }
    else if (lightingMode == 2)
    {
        // PBR lighting
        lightingColor = computePBRLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }

    // Apply shadow
    lightingColor *= (1.0 - shadow);

    // --------------------------------------------------------------
    // NOTE: We do NOT add environment reflection here again
    // (we removed the "lightingColor += envColor" line).
    // This prevents double-counting reflection.
    // --------------------------------------------------------------

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
        finalColor = pow(finalColor, vec3(1.0 / 2.2));
    }

    finalColor = clamp(finalColor, 0.0, 1.0);
    FragColor = vec4(finalColor, 1.0);

    // --------------------------------------------------------------
    // 8) Depth Correction (Approx. Eye-Space Reprojection)
    // --------------------------------------------------------------
    if (pomHeightScale > 0.0 && depthOffset != 0.0)
    {
        // (A) The old eye-space position
        vec4 eyePos = view * vec4(FragPos, 1.0);

        // (B) Offset in tangent space
        // A simplified approach: offset along negative Z in tangent space
        vec3 offsetTangent = vec3(0.0, 0.0, -depthOffset);
        offsetTangent *= parallaxEyeOffsetScale;

        // Convert tangent->world->eye
        vec3 offsetWorld = TBN * offsetTangent;
        vec4 offsetEye   = view * vec4(offsetWorld, 0.0);

        // (C) Adjust the eye-space position
        vec4 newEyePos = eyePos + offsetEye;

        // (D) Reproject to clip space
        vec4 clipPos = projection * newEyePos;
        float ndcDepth = clipPos.z / clipPos.w;

        // (E) Store new depth
        ndcDepth = clamp(ndcDepth, 0.0, parallaxMaxDepthClamp);
        gl_FragDepth = ndcDepth;
    }
    else
    {
        gl_FragDepth = gl_FragCoord.z;
    }
}
