#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

// For POM
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos;

in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform samplerCube environmentMap;
uniform vec3 cameraPos;
uniform vec3 ambientColor;

// The shadow map & toggles
uniform sampler2D shadowMap;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;

// Wave/geometry parameters
uniform float surfaceDepth;
uniform float shadowStrength;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;

// Reflection intensity
uniform float environmentMapStrength;

void main()
{
    vec3 viewDir = normalize(cameraPos - FragPos);

    // ---------------------------------------------------------
    // 1) Procedural POM
    // ---------------------------------------------------------
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;

    // If pomHeightScale > 0, do ProceduralParallaxOcclusionMapping
    // (Declared in common_funcs.glsl)
    if (pomHeightScale > 0.0)
    {
        // Transform the view direction into tangent space
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);

        workingTexCoords = ProceduralParallaxOcclusionMapping(
        TexCoords,
        tangentViewDir,
        depthOffset
        );
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    // ---------------------------------------------------------
    // 2) Wave calculations using workingTexCoords
    // ---------------------------------------------------------
    vec2 waveTexCoords = workingTexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);

    // Offset the waveTexCoords
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    // Build a procedural wave normal
    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);
    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    // ---------------------------------------------------------
    // 3) Reflection & refraction
    // ---------------------------------------------------------
    // Reflect & refract with the wave-based normal
    vec3 reflectDir = reflect(-viewDir, normalMap);
    vec3 refractDir = refract(-viewDir, normalMap, 1.0 / 1.33);// ~IOR for water

    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    // Fresnel effect
    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);
    vec3 envColor = mix(refraction, reflection, fresnel);

    // ---------------------------------------------------------
    // 4) Shadows (displaced)
    // ---------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationDisplaced(
        FragPos, // world-space frag pos
        normalMap, // wave-based normal
        waveHeight,
        shadowMap,
        lightSpaceMatrix,
        model,
        lightPositions[0], // pick a main light for bias
        0.05, // bias factor
        0.005, // min bias
        shadowStrength,
        surfaceDepth
        );
    }

    // ---------------------------------------------------------
    // 5) Combine lighting
    // ---------------------------------------------------------
    vec3 color = vec3(0.0);

    // Optionally compute some local Phong lighting for the water
    if (phongShading)
    {
        // Base “water color” or ambientColor as desired
        vec3 phongColor = computePhongLighting(normalMap, viewDir, FragPos, vec3(0.2, 0.5, 1.0));
        // Apply shadow
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color += phongColor;
    }

    // Also apply environment reflection/refraction, attenuated by shadow
    envColor = mix(envColor, envColor * (1.0 - shadow), shadowStrength);
    color += envColor * environmentMapStrength;

    // ---------------------------------------------------------
    // 6) Tone & Gamma
    // ---------------------------------------------------------
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
