#version 330 core
#include "common_funcs.glsl"

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
uniform sampler2D shadowMap;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;

uniform int lightingMode;
uniform bool shadowingEnabled;
uniform float surfaceDepth;
uniform float shadowStrength;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;
uniform mat4 view;
uniform mat4 projection;

// Water base color
uniform vec3 waterBaseColor;

void main()
{
    //------------------------------------------------------------
    // (A) Classic wave coords => used for shadow displacement
    //------------------------------------------------------------
    vec2 waveTexCoordsClassic = TexCoords;
    float noiseClassic = smoothNoise(waveTexCoordsClassic * randomness);

    waveTexCoordsClassic.x += sin(time * waveSpeed
    + TexCoords.y * texCoordFrequency
    + noiseClassic)
    * texCoordAmplitude;
    waveTexCoordsClassic.y += cos(time * waveSpeed
    + TexCoords.x * texCoordFrequency
    + noiseClassic)
    * texCoordAmplitude;

    // Compute simple wave variation for shadow offset
    float waveHeightXClassic = sin(waveTexCoordsClassic.y * 10.0);
    float waveHeightYClassic = cos(waveTexCoordsClassic.x * 10.0);

    // Final “classic” wave height
    float waveHeightClassic = 0.5 * waveAmplitude
    * (waveHeightXClassic + waveHeightYClassic);


    //------------------------------------------------------------
    // (B) Possibly do Parallax Occlusion Mapping (POM)
    //------------------------------------------------------------
    // We'll store final coords for the “visual wave normal”
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;

    if (pomHeightScale > 0.0)
    {
        // For tangent-space parallax
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);

        workingTexCoords = ProceduralParallaxOcclusionMapping(
        TexCoords,
        tangentViewDir,
        depthOffset
        );

        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    //------------------------------------------------------------
    // (C) More advanced wave normal (from “computeWave”)
    //------------------------------------------------------------
    WaveOutput wo = computeWave(workingTexCoords);
    float waveHeightX = wo.waveHeightX;
    float waveHeightY = wo.waveHeightY;

    // Build a local tangent-space normal
    vec3 waveNormalTangent = vec3(0.0, 0.0, 1.0);
    waveNormalTangent.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    waveNormalTangent = normalize(waveNormalTangent);

    // Convert to world-space
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);
    vec3 finalNormal = normalize(TBN * waveNormalTangent);

    //------------------------------------------------------------
    // (D) Reflection & Refraction
    //------------------------------------------------------------
    vec3 viewDir = normalize(cameraPos - FragPos);
    vec3 reflectDir = reflect(-viewDir, finalNormal);
    vec3 refractDir = refract(-viewDir, finalNormal, 1.0 / 1.33);

    // Sample environment
    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    // Fresnel
    float fresnel = pow(1.0 - dot(viewDir, finalNormal), 3.0);
    vec3 envColor = mix(refraction, reflection, fresnel);

    //------------------------------------------------------------
    // (E) Shadow Calculation using waveHeightClassic
    //------------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationDisplaced(
        FragPos,
        finalNormal,
        waveHeightClassic, // note: using the “classic” wave
        shadowMap,
        lightSpaceMatrix,
        model,
        lightPositions[0], // pick first light
        0.05, // biasFactor
        0.005, // minBias
        shadowStrength,
        surfaceDepth
        );
    }

    //------------------------------------------------------------
    // (F) Combine environment with user water color
    //------------------------------------------------------------
    // e.g. a 50/50 mix
    vec3 combinedBase = mix(waterBaseColor, envColor, 0.5);

    //------------------------------------------------------------
    // (G) Local Lighting
    //------------------------------------------------------------
    vec3 color = vec3(0.0);

    if (lightingMode == 0)
    {
        // Diffuse lighting
        color = computeDiffuseLighting(
        finalNormal,
        viewDir,
        FragPos,
        combinedBase,
        TexCoords
        );
    }
    else if (lightingMode >= 1)
    {
        // Phong
        color = computePhongLighting(
        finalNormal,
        viewDir,
        FragPos,
        combinedBase,
        TexCoords
        );
    }

    // Apply shadow
    color = mix(color, color * (1.0 - shadow), shadowStrength);

    //------------------------------------------------------------
    // (H) Tone & Gamma
    //------------------------------------------------------------
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0/2.2));
    }

    //------------------------------------------------------------
    // (I) Final with legacy opacity
    //------------------------------------------------------------
    float alpha = clamp(legacyOpacity, 0.0, 1.0);
    FragColor = vec4(clamp(color, 0.0, 1.0), alpha);

    //------------------------------------------------------------
    // (J) Depth Correction if POM
    //------------------------------------------------------------
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
