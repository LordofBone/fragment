#version 330 core
#include "common_funcs.glsl"

// --------------------------------------------
// Inputs from the vertex shader
// --------------------------------------------
in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

// For POM
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos;

in vec4 FragPosLightSpace;

// --------------------------------------------
// Output
// --------------------------------------------
out vec4 FragColor;

// --------------------------------------------
// Uniforms
// --------------------------------------------
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;
uniform vec3 cameraPos;

// Toggling
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;

// Shadow parameters
uniform float surfaceDepth;
uniform float shadowStrength;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;

// Reflection intensity
uniform float environmentMapStrength;

// --------------------------------------------
// Main
// --------------------------------------------
void main()
{
    vec3 viewDir = normalize(cameraPos - FragPos);

    // 1) POM (Procedural Parallax Occlusion Mapping)
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;

    // If pomHeightScale > 0, apply the procedural parallax
    if (pomHeightScale > 0.0)
    {
        // Convert the view direction into tangent space
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);

        // Use your ProceduralParallaxOcclusionMapping from common_funcs.glsl
        workingTexCoords = ProceduralParallaxOcclusionMapping(
        TexCoords,
        tangentViewDir,
        depthOffset
        );
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    // 2) Wave-based distortion for lava
    vec2 waveTexCoords = workingTexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    // 3) Procedural wave normal (like lava)
    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);
    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    // 4) Reflection from environment
    vec3 reflectDir = reflect(-viewDir, normalMap);
    vec3 reflection = texture(environmentMap, reflectDir).rgb * environmentMapStrength;
    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);

    // 5) Lava base color
    vec3 baseColor   = vec3(1.0, 0.3, 0.0);
    vec3 brightColor = vec3(1.0, 0.7, 0.0);

    float noiseValue = smoothNoise(TexCoords * 5.0 + time * 0.5);
    vec3 lavaColor = mix(baseColor, brightColor, noiseValue);

    // Mix lava + reflection (fresnel-based)
    vec3 color = mix(lavaColor, reflection, fresnel * 0.2);

    // 6) Shadow (displaced for lava)
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationDisplaced(
        FragPos, // world-space pos
        normalMap,
        waveHeight,
        shadowMap,
        lightSpaceMatrix,
        model,
        lightPositions[0], // pick your main light
        0.05, // biasFactor
        0.0005, // minBias
        shadowStrength,
        surfaceDepth
        );
    }

    // 7) Local lighting (Phong or diffuse)
    if (phongShading)
    {
        // Use lava color as base color
        vec3 phongColor = computePhongLighting(normalMap, viewDir, FragPos, color);
        // Mix in partial darkness from shadow
        color = mix(color, color * (1.0 - shadow * 0.5), 0.5) + phongColor * 0.5;
    }
    else
    {
        // Basic darkening by shadow
        color = mix(color, color * (1.0 - shadow * 0.5), 1.0);
    }

    // 8) Bubbles
    float bubbleNoise = smoothNoise(TexCoords * 10.0 + time * 2.0);
    if (bubbleNoise > 0.8)
    {
        color = brightColor;
    }

    // 9) Rocks
    float rockNoise = smoothNoise(TexCoords * 20.0 + time * 0.1);
    if (rockNoise > 0.9)
    {
        color = mix(color, vec3(0.2, 0.2, 0.2), rockNoise - 0.9);
    }

    // 10) Tone-mapping & gamma
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color=clamp(color, 0.0, 1.0);
    FragColor=vec4(color, 1.0);
}
