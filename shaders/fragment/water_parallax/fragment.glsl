#version 330 core
#include "glsl_utilities.glsl"

// ---------------------------------------------------------
// Vertex -> Fragment inputs
// ---------------------------------------------------------
in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos;
in vec4 FragPosLightSpace;
in float FragPosW;

// TBN rows
in vec3 TBNrow0;
in vec3 TBNrow1;
in vec3 TBNrow2;

// ---------------------------------------------------------
// Outputs
// ---------------------------------------------------------
out vec4 FragColor;

// ---------------------------------------------------------
// Uniforms
// ---------------------------------------------------------
uniform vec3 cameraPos;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;

uniform int lightingMode;
uniform bool shadowingEnabled;
uniform float surfaceDepth;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;
uniform mat4 view;
uniform mat4 projection;

// Water base color
uniform vec3 waterBaseColor;

void main()
{
    //--------------------------------------------
    // (A) Reconstruct TBN + view direction
    //--------------------------------------------
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);
    vec3 viewDir = normalize(cameraPos - FragPos);

    //--------------------------------------------
    // (B) "Classic" wave coords for shadow displacement
    //--------------------------------------------
    vec2 waveTexCoordsClassic = TexCoords;
    float noiseClassic = smoothNoise(waveTexCoordsClassic * randomness);

    waveTexCoordsClassic.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseClassic) * texCoordAmplitude;
    waveTexCoordsClassic.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseClassic) * texCoordAmplitude;

    // "Classic" wave height for shadow offset
    float waveHeightXClassic = sin(waveTexCoordsClassic.y * 10.0);
    float waveHeightYClassic = cos(waveTexCoordsClassic.x * 10.0);
    float waveHeightClassic = 0.5 * waveAmplitude * (waveHeightXClassic + waveHeightYClassic);

    //--------------------------------------------
    // (C) Parallax Occlusion Mapping (POM)
    //--------------------------------------------
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;
    if (pomHeightScale > 0.0)
    {
        // tangent-space view direction
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);
        workingTexCoords = ProceduralParallaxOcclusionMapping(TexCoords, tangentViewDir, depthOffset);
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    //--------------------------------------------
    // (D) "Visual" wave coords & normal in tangent space
    //--------------------------------------------
    vec2 waveTexCoords = workingTexCoords;
    float noiseFactor  = smoothNoise(waveTexCoords * randomness);

    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    // Tangent-space normal (start with "up")
    vec3 waveNormalTangent = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);

    waveNormalTangent.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    waveNormalTangent = normalize(waveNormalTangent);

    // For possible highlight
    float waveHeightVisual = 0.5 * waveAmplitude * (waveHeightX + waveHeightY);

    // Convert wave normal to WORLD space
    vec3 finalNormal = normalize(TBN * waveNormalTangent);

    //--------------------------------------------
    // (E) Basic environment reflection
    //--------------------------------------------
    vec3 reflectDir  = reflect(-viewDir, finalNormal);
    float fresnel    = pow(1.0 - dot(viewDir, finalNormal), 3.0);

    //--------------------------------------------
    // (F) Shadows (displaced)
    //--------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        // Use waveHeightClassic for consistent Y offset
        shadow = ShadowCalculationDisplaced(
        FragPos,
        finalNormal,
        waveHeightClassic,
        lightSpaceMatrix,
        model,
        lightPositions[0], // pick first light
        0.05, // biasFactor
        0.0005, // minBias
        surfaceDepth
        );
    }

    //--------------------------------------------
    // (G) Local lighting
    //--------------------------------------------
    vec3 color;
    if (lightingMode == 0)// diffuse
    {
        vec3 diffuseColor = computeDiffuseLighting(finalNormal, viewDir, FragPos, waterBaseColor, TexCoords);
        color = diffuseColor;
    }
    else if (lightingMode >= 1)// Phong
    {
        vec3 phongColor = computePhongLighting(finalNormal, viewDir, FragPos, waterBaseColor, TexCoords);
        color = phongColor;
    }

    // 6) Apply shadow attenuation
    color *= (1.0 - shadow);

    //--------------------------------------------
    // (H) Tone & Gamma
    //--------------------------------------------
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }
    color = clamp(color, 0.0, 1.0);

    //--------------------------------------------
    // (I) legacyOpacity
    //--------------------------------------------
    float alpha = clamp(legacyOpacity, 0.0, 1.0);
    FragColor = vec4(color, alpha);

    //--------------------------------------------
    // (J) Optional Depth Correction if POM
    //--------------------------------------------
    if (pomHeightScale > 0.0 && depthOffset != 0.0 && enableFragDepthAdjustment)
    {
        vec4 eyePos = view * vec4(FragPos, 1.0);
        adjustFragDepth(
        eyePos,
        projection,
        vec4(FragPos, 1.0),
        vec3[](TBNrow0, TBNrow1, TBNrow2),
        depthOffset,
        gl_FragDepth
        );
    }
    else
    {
        gl_FragDepth = gl_FragCoord.z;
    }
}
