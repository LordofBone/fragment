#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

// Textures / uniforms
uniform vec3 cameraPos;

// Toggling
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
// Lighting mode selector: 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;
uniform bool shadowingEnabled;

// Shadow stuff
uniform sampler2D shadowMap;
uniform float surfaceDepth;
uniform float shadowStrength;

// Transforms
uniform mat4 model;
uniform mat4 lightSpaceMatrix;

void main()
{
    // Wave coords
    vec2 waveTexCoords = TexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    // Procedural normal
    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);
    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    vec3 viewDir = normalize(cameraPos - FragPos);
    vec3 reflectDir = reflect(-viewDir, normalMap);

    // Reflection
    vec3 reflection = texture(environmentMap, reflectDir).rgb * environmentMapStrength;
    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);

    // Lava base color
    vec3 baseColor = vec3(1.0, 0.3, 0.0);
    vec3 brightColor = vec3(1.0, 0.7, 0.0);
    float noiseValue = smoothNoise(TexCoords * 5.0 + time * 0.5);
    vec3 lavaColor = mix(baseColor, brightColor, noiseValue);

    // Mix lava + reflection based on Fresnel
    vec3 envColor = mix(lavaColor, reflection, fresnel * 0.2);

    // Shadow
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
        lightPositions[0], // pick the first light for bias
        0.05,
        0.0005,
        shadowStrength,
        surfaceDepth
        );
    }

    // Lighting
    vec3 color = vec3(0.0);
    if (lightingMode == 0)
    {
        // Diffuse lighting
        color = computeDiffuseLighting(normalMap, viewDir, FragPos, envColor, TexCoords);
    }
    else if (lightingMode >= 1)
    {
        // Phong lighting
        color = computePhongLighting(normalMap, viewDir, FragPos, envColor, TexCoords);
    }

    // Apply shadow
    color = mix(color, color * (1.0 - shadow * 0.5), shadowStrength);

    // Bubbles
    float bubbleNoise = smoothNoise(TexCoords * 10.0 + time * 2.0);
    if (bubbleNoise > 0.8)
    {
        color = brightColor;
    }

    // Rocks
    float rockNoise = smoothNoise(TexCoords * 20.0 + time * 0.1);
    if (rockNoise > 0.9)
    {
        color = mix(color, vec3(0.2, 0.2, 0.2), rockNoise - 0.9);
    }

    // Tone Mapping and Gamma Correction
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
