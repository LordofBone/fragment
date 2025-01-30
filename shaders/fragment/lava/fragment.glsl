#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

// Camera/uniforms
uniform vec3 cameraPos;

// Toggling
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform int lightingMode;// 0=diffuse,1=phong,2=maybe pbr
uniform bool shadowingEnabled;

// Shadow
uniform sampler2D shadowMap;
uniform float surfaceDepth;
uniform float shadowStrength;

uniform mat4 model;
uniform mat4 lightSpaceMatrix;

// Lava color uniforms
uniform vec3 lavaBaseColor;// e.g. (1.0, 0.3, 0.0)
uniform vec3 lavaBrightColor;// e.g. (1.0, 0.7, 0.0)

void main()
{
    //------------------------------------------------
    // 1) Wave coords
    //------------------------------------------------
    vec2 waveTexCoords = TexCoords;
    float noiseFactor   = smoothNoise(waveTexCoords * randomness);

    waveTexCoords.x += sin(time * waveSpeed
    + TexCoords.y * texCoordFrequency
    + noiseFactor)
    * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed
    + TexCoords.x * texCoordFrequency
    + noiseFactor)
    * texCoordAmplitude;

    // 2) Procedural normal
    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);

    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    float waveHeight = 0.5 * waveAmplitude * (waveHeightX + waveHeightY);

    //------------------------------------------------
    // 3) Reflection
    //------------------------------------------------
    vec3 viewDir   = normalize(cameraPos - FragPos);
    vec3 reflectDir= reflect(-viewDir, normalMap);

    float fresnel   = pow(1.0 - dot(viewDir, normalMap), 3.0);

    //------------------------------------------------
    // 4) Lava base color + bright color
    //------------------------------------------------
    float noiseValue = smoothNoise(TexCoords * 5.0 + time * 0.5);
    vec3 lavaColor   = mix(lavaBaseColor, lavaBrightColor, noiseValue);

    //------------------------------------------------
    // 5) Shadow
    //------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationDisplaced(
        FragPos,
        normalMap,
        waveHeight,
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

    //------------------------------------------------
    // 6) Local lighting
    //------------------------------------------------
    vec3 color = vec3(0.0);
    if (lightingMode == 0)
    {
        // Diffuse
        color = computeDiffuseLighting(normalMap, viewDir, FragPos, lavaBaseColor, TexCoords);
    }
    else
    {
        // Phong (or if lightingMode >=2 => PBR)
        color = computePhongLighting(normalMap, viewDir, FragPos, lavaBaseColor, TexCoords);
    }

    // Apply shadow
    color = mix(color, color * (1.0 - shadow * 0.5), shadowStrength);

    //------------------------------------------------
    // 7) Additional procedural: bubbles/rocks
    //------------------------------------------------
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

    //------------------------------------------------
    // 8) Tone & Gamma
    //------------------------------------------------
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0/2.2));
    }

    // clamp for safety
    color = clamp(color, 0.0, 1.0);

    //------------------------------------------------
    // 9) legacyOpacity
    //------------------------------------------------
    float alpha = clamp(legacyOpacity, 0.0, 1.0);

    FragColor = vec4(color, alpha);
}
