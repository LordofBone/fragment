#version 330 core
#include "common_funcs.glsl"

// --------------------------------------------
// Inputs from the vertex shader
// --------------------------------------------
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

// --------------------------------------------
// Output
// --------------------------------------------
out vec4 FragColor;

// --------------------------------------------
// Uniforms
// --------------------------------------------
uniform sampler2D shadowMap;
uniform vec3 cameraPos;

// Toggling
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform int lightingMode;
uniform bool shadowingEnabled;

// Shadow parameters
uniform float surfaceDepth;
uniform float shadowStrength;
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;

// Additional color style
uniform vec3 lavaBaseColor;// e.g. (1.0, 0.3, 0.0)
uniform vec3 lavaBrightColor;// e.g. (1.0, 0.7, 0.0)

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
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);
        workingTexCoords = ProceduralParallaxOcclusionMapping(TexCoords, tangentViewDir, depthOffset);
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    //--------------------------------------------
    // (D) "Visual" wave coords & normal in tangent space
    //--------------------------------------------
    vec2 waveTexCoords = workingTexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);

    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    vec3 waveNormalTangent = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);

    waveNormalTangent.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    waveNormalTangent = normalize(waveNormalTangent);

    float waveHeightVisual = 0.5 * waveAmplitude * (waveHeightX + waveHeightY);

    // Convert wave normal to WORLD space
    vec3 finalNormal = normalize(TBN * waveNormalTangent);

    //--------------------------------------------
    // (E) Basic environment reflection
    //--------------------------------------------
    vec3 reflectDir  = reflect(-viewDir, finalNormal);
    float fresnel    = pow(1.0 - dot(viewDir, finalNormal), 3.0);

    //--------------------------------------------
    // (F) Lava color + reflection
    //--------------------------------------------
    float noiseValue = smoothNoise(TexCoords * 5.0 + time * 0.5);
    vec3 lavaColor   = mix(lavaBaseColor, lavaBrightColor, noiseValue);

    //--------------------------------------------
    // (G) Shadows (displaced)
    //--------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationDisplaced(
        FragPos,
        finalNormal,
        waveHeightClassic,
        shadowMap,
        lightSpaceMatrix,
        model,
        lightPositions[0], // pick first light
        0.05, // biasFactor
        0.0005, // minBias
        shadowStrength,
        surfaceDepth
        );
    }

    //--------------------------------------------
    // (H) Local lighting
    //--------------------------------------------
    vec3 color;
    if (lightingMode == 0)// diffuse
    {
        vec3 diffuseColor = computeDiffuseLighting(finalNormal, viewDir, FragPos, lavaBaseColor, TexCoords);
        diffuseColor = mix(diffuseColor, diffuseColor * (1.0 - shadow), shadowStrength);
        color = diffuseColor;
    }
    else if (lightingMode >= 1)// Phong
    {
        vec3 phongColor = computePhongLighting(finalNormal, viewDir, FragPos, lavaBaseColor, TexCoords);
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color = phongColor;
    }

    //--------------------------------------------
    // (I) Additional procedural effects (bubbles, rocks)
    //--------------------------------------------
    float bubbleNoise = smoothNoise(TexCoords * 10.0 + time * 2.0);
    if (bubbleNoise > 0.8)
    {
        color = lavaBrightColor;
    }

    float rockNoise = smoothNoise(TexCoords * 20.0 + time * 0.1);
    if (rockNoise > 0.9)
    {
        color = mix(color, vec3(0.2, 0.2, 0.2), rockNoise - 0.9);
    }

    //--------------------------------------------
    // (J) Tone & Gamma
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
    // (K) legacyOpacity
    //--------------------------------------------
    float alpha = clamp(legacyOpacity, 0.0, 1.0);
    FragColor = vec4(color, alpha);

    //--------------------------------------------
    // (L) Optional Depth Correction if POM
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
