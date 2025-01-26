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
    // 1) Reconstruct TBN
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);

    // 2) View direction in world space
    vec3 viewDir = normalize(cameraPos - FragPos);

    // 3) Parallax Occlusion Mapping
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;

    if (pomHeightScale > 0.0)
    {
        // tangent-space view direction
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);

        workingTexCoords = ProceduralParallaxOcclusionMapping(
        TexCoords,
        tangentViewDir,
        depthOffset
        );
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    // 4) Wave-based distortion in tangent space
    vec2 waveTexCoords = workingTexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);

    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    // Start with "up" in tangent space
    vec3 waveNormalTangent = vec3(0.0, 0.0, 1.0);

    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);

    waveNormalTangent.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    waveNormalTangent = normalize(waveNormalTangent);

    float waveHeight = waveAmplitude * 0.5 * (waveHeightX + waveHeightY);

    // 5) Convert wave normal to WORLD space
    vec3 finalNormal = normalize(TBN * waveNormalTangent);

    // 6) Environment reflection (if desired)
    vec3 reflectDir = reflect(-viewDir, finalNormal);
    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    float fresnel = pow(1.0 - dot(viewDir, finalNormal), 3.0);

    // 7) Lava base color
    //    Blend between lavaBaseColor and lavaBrightColor
    float noiseValue = smoothNoise(TexCoords * 5.0 + time * 0.5);
    vec3 lavaColor = mix(lavaBaseColor, lavaBrightColor, noiseValue);

    // Combine lava + reflection gently
    // (reduce reflection with a small factor if you prefer)
    vec3 combinedColor = mix(lavaColor, reflection, fresnel * 0.2);

    // 8) Shadows (displaced)
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
        lightPositions[0],
        0.05,
        0.0005,
        shadowStrength,
        surfaceDepth
        );
    }

    // 9) Local lighting
    vec3 color;
    if (lightingMode == 0)
    {
        // Diffuse-only
        vec3 diffuseColor = computeDiffuseLighting(finalNormal, viewDir, FragPos, combinedColor);
        diffuseColor = mix(diffuseColor, diffuseColor * (1.0 - shadow), shadowStrength);
        color = diffuseColor;
    }
    else
    {
        // Phong
        vec3 phongColor = computePhongLighting(finalNormal, viewDir, FragPos, combinedColor);
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color = phongColor;
    }

    // 10) Additional procedural stuff: bubbles, rocks, etc.
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

    // 11) Tone-mapping & gamma
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0/2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);

    // ---------------------------------------------------
    // 12) Optional Depth Correction w/ clamp
    // ---------------------------------------------------
    if (pomHeightScale > 0.0 && depthOffset != 0.0 && enableFragDepthAdjustment) {
        vec4 eyePos = view * vec4(FragPos, 1.0);

        // Call the centralized function
        adjustFragDepth(
        eyePos,
        projection,
        vec4(FragPos, 1.0),
        vec3[](TBNrow0, TBNrow1, TBNrow2),
        depthOffset,
        gl_FragDepth
        );
    } else {
        gl_FragDepth = gl_FragCoord.z;
    }
}
