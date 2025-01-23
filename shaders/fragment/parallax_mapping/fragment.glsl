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

// ---------------------------------------------------------------------
// More advanced Parallax Depth Correction scaling
// (Tweak them if you find offsets are too large/small.)
// ---------------------------------------------------------------------
uniform float parallaxEyeOffsetScale = 1.0;
uniform float parallaxMaxDepthClamp  = 0.99;

void main()
{
    // --------------------------------------------------------------
    // 1) Reconstruct TBN
    //    TBN transforms from tangent space --> world space
    // --------------------------------------------------------------
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);

    // --------------------------------------------------------------
    // 2) Parallax Occlusion Mapping in tangent space
    // --------------------------------------------------------------
    vec3 viewDirTangent = normalize(TangentViewPos - TangentFragPos);

    float depthOffset = 0.0;// This will be updated by POM
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
    // 3) Sample normal map in tangent space -> transform to world space
    // --------------------------------------------------------------
    vec3 normalTex = texture(normalMap, parallaxCoords, textureLodLevel).rgb;
    normalTex = normalTex * 2.0 - 1.0;// tangent-space normal in [-1..1]
    vec3 finalNormal = normalize(TBN * normalTex);// -> world space

    // --------------------------------------------------------------
    // 4) World-space view direction (for reflection, lighting)
    // --------------------------------------------------------------
    vec3 worldViewDir = normalize(viewPosition - FragPos);

    // --------------------------------------------------------------
    // 5) Environment reflection (if desired)
    //    (We'll remove "double-add" by not passing env color to lighting.)
    // --------------------------------------------------------------
    vec3 reflectDir = reflect(-worldViewDir, finalNormal);
    reflectDir = normalize(reflectDir);

    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
    envColor *= environmentMapStrength;// scale if you want

    // --------------------------------------------------------------
    // 6) Shadows
    // --------------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // --------------------------------------------------------------
    // 7) Compute base color & local lighting
    //    (No double-add: We pass only "baseColor" to the lighting function.)
    // --------------------------------------------------------------
    vec3 baseColor = texture(diffuseMap, parallaxCoords, textureLodLevel).rgb;
    vec3 lightingColor = vec3(0.0);

    // a) If using "Diffuse" lighting
    if (lightingMode == 0)
    {
        lightingColor = computeDiffuseLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }
    // b) If using "Phong" lighting
    else if (lightingMode == 1)
    {
        lightingColor = computePhongLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }
    // c) If using "PBR"
    else if (lightingMode == 2)
    {
        // We'll assume "computePBRLighting" doesn't add env reflection inside,
        // or if it does, you'll skip adding envColor below. Up to you.
        lightingColor = computePBRLighting(finalNormal, worldViewDir, FragPos, baseColor);
    }

    // Apply shadow attenuation
    lightingColor *= (1.0 - shadow);

    // Add the environment reflection (only once)
    // If your PBR or Phong function already includes reflection, skip this
    lightingColor += envColor * (1.0 - shadow);

    // Combine final color
    vec3 finalColor = lightingColor;

    // --------------------------------------------------------------
    // 8) ToneMapping & Gamma
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

    // Write out color
    FragColor = vec4(finalColor, 1.0);

    // --------------------------------------------------------------
    // 9) Depth Correction (more accurate approach)
    //    We approximate the parallax offset in eye space, then reproject
    //    to find the new depth for gl_FragDepth.
    // --------------------------------------------------------------
    if (pomHeightScale > 0.0 && depthOffset != 0.0)
    {
        // (A) Build approximate eye-space position of this fragment
        //     (before POM offset)
        vec4 eyePos = view * vec4(FragPos, 1.0);// old eye-space

        // (B) Convert the parallax offset from tangent space -> world -> eye space

        // The offset in tangent space is "depthOffset * normalize(viewDirTangent)"
        // but that's not exactly correct since POM can shift coords in the X/Y of tangent space too.
        // We'll do a simplified approach:
        //   "offsetTangent" = depthOffset * (0, 0, -1)  (the parallax is mostly along negative Z in tangent space)
        //   Then transform to world, then to eye space.

        vec3 offsetTangent = vec3(0.0, 0.0, -depthOffset);
        // scale the offset if needed
        offsetTangent *= parallaxEyeOffsetScale;

        // Convert tangent->world
        vec3 offsetWorld = TBN * offsetTangent;
        // Convert world->eye
        vec4 offsetEye = view * vec4(offsetWorld, 0.0);

        // (C) Adjust the eyePos by that offset
        vec4 newEyePos = eyePos + offsetEye;

        // (D) Reproject to clip space
        vec4 clipPos = projection * newEyePos;
        // Don't forget perspective divide
        float ndcDepth = clipPos.z / clipPos.w;

        // (E) Store in gl_FragDepth
        // clamp to [0..1]
        ndcDepth = clamp(ndcDepth, 0.0, parallaxMaxDepthClamp);
        gl_FragDepth = ndcDepth;
    }
    else
    {
        // If no POM or no offset, we can just leave gl_FragDepth as is,
        // or write the original
        gl_FragDepth = gl_FragCoord.z;
    }
}
