#version 330 core
#include "common_funcs.glsl"

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
uniform sampler2D normalMap;
uniform sampler2D shadowMap;

// Toggles
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool shadowingEnabled;

// 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;

// Parallax
uniform float parallaxEyeOffsetScale = 1.0;
uniform float parallaxMaxDepthClamp  = 0.99;

// Depth clamp settings
uniform float maxForwardOffset = 1.0;// How far forward we allow the surface to move (in NDC)

// Camera transforms
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;
uniform vec3 viewPosition;

// comment out if you want to skip clamping
//#define CLAMP_POM_DEPTH

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
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // --------------------------------------------------------------
    // 6) Local lighting
    // --------------------------------------------------------------
    vec3 baseColor = texture(diffuseMap, parallaxCoords, textureLodLevel).rgb;
    vec3 lightingColor = vec3(0.0);

    if (lightingMode == 0)
    {
        lightingColor = computeDiffuseLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }
    else if (lightingMode == 1)
    {
        lightingColor = computePhongLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }
    else
    {
        lightingColor = computePBRLighting(finalNormal, worldViewDir, FragPos, baseColor);
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
    FragColor = vec4(finalColor, 1.0);

    // --------------------------------------------------------------
    // 8) Depth Correction (Approx. Eye-Space Reprojection)
    //    w/ optional clamping
    // --------------------------------------------------------------

    // depth adjustment with Approx. Eye-Space Reprojection currently diabled for models as it can cause artifacts
    //    if (pomHeightScale > 0.0 && depthOffset != 0.0)
    //    {
    //        vec4 eyePos = view * vec4(FragPos, 1.0);
    //
    //        // offset in tangent space
    //        vec3 offsetTangent = vec3(0.0, 0.0, -depthOffset) * parallaxEyeOffsetScale;
    //        // tangent->world->eye
    //        vec3 offsetWorld = TBN * offsetTangent;
    //        vec4 offsetEye   = view * vec4(offsetWorld, 0.0);
    //
    //        // new eye position
    //        vec4 newEyePos = eyePos + offsetEye;
    //
    //        // reproject
    //        vec4 clipPos = projection * newEyePos;
    //        float ndcDepth = clipPos.z / clipPos.w;
    //        ndcDepth = clamp(ndcDepth, 0.0, parallaxMaxDepthClamp);
    //
    //        float oldZ = gl_FragCoord.z;
    //
    //        #ifdef CLAMP_POM_DEPTH
    //        // only allow a small forward shift
    //        float allowedMinZ = oldZ - maxForwardOffset;
    //        if (ndcDepth < allowedMinZ)
    //        {
    //            ndcDepth = allowedMinZ;
    //        }
    //        #endif
    //
    //        gl_FragDepth = ndcDepth;
    //    }
    //    else
    //    {
    //        gl_FragDepth = gl_FragCoord.z;
    //    }

    // so we currently just directly write the depth value without any correction
    gl_FragDepth = gl_FragCoord.z;
}
