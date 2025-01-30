#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

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

// Water base color
uniform vec3 waterBaseColor;

void main()
{
    vec2 waveTexCoords = TexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);

    vec3 normalDetail = vec3(0.0, 0.0, 1.0);
    normalDetail.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalDetail = normalize(normalDetail);

    vec3 finalNormal = normalize(TBN * normalDetail);
    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    vec3 viewDir = normalize(cameraPos - FragPos);

    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationDisplaced(
        FragPos,
        finalNormal,
        waveHeight,
        shadowMap,
        lightSpaceMatrix,
        model,
        lightPositions[0], // pick a main light for bias
        0.05,
        0.005,
        shadowStrength,
        surfaceDepth
        );
    }

    vec3 color = vec3(0.0);
    // Lighting
    if (lightingMode == 0)
    {
        // Diffuse-only
        color = computeDiffuseLighting(finalNormal, viewDir, FragPos, waterBaseColor, TexCoords);
    }
    else if (lightingMode >= 1)
    {
        // Phong lighting
        color = computePhongLighting(finalNormal, viewDir, FragPos, waterBaseColor, TexCoords);
    }

    // Apply shadow
    color = mix(color, color * (1.0 - shadow), shadowStrength);

    // Tone Mapping and Gamma Correction
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }

    // Incorporate `legacyOpacity` parameter
    float alpha = clamp(legacyOpacity, 0.0, 1.0);

    FragColor = vec4(clamp(color, 0.0, 1.0), alpha);
}
