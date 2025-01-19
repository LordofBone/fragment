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
// Lighting mode selector: 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;
uniform bool shadowingEnabled;

uniform float surfaceDepth;
uniform float shadowStrength;

uniform mat4 model;
uniform mat4 lightSpaceMatrix;

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

    vec3 reflectDir = reflect(-viewDir, finalNormal);
    vec3 refractDir = refract(-viewDir, finalNormal, 1.0 / 1.33);

    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    float fresnel = pow(1.0 - dot(viewDir, finalNormal), 3.0);
    vec3 envColor = mix(refraction, reflection, fresnel);

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
        // If not, do Diffuse-only
        vec3 diffuseColor = computeDiffuseLighting(finalNormal, viewDir, FragPos, envColor);
        diffuseColor = mix(diffuseColor, diffuseColor * (1.0 - shadow), shadowStrength);
        color += diffuseColor;
    }
    else if (lightingMode >= 1)
    {
        // If set, do Phong lighting
        vec3 phongColor = computePhongLighting(finalNormal, viewDir, FragPos, envColor);
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color += phongColor;
    }

    envColor = mix(envColor, envColor * (1.0 - shadow), shadowStrength);
    color += envColor * environmentMapStrength;

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
