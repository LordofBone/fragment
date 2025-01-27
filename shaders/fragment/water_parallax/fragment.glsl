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
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);
    vec3 viewDir = normalize(cameraPos - FragPos);

    // (1) POM
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;
    if (pomHeightScale > 0.0)
    {
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);
        workingTexCoords = ProceduralParallaxOcclusionMapping(TexCoords, tangentViewDir, depthOffset);
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    // (2) Wave normal in tangent space
    WaveOutput wo = computeWave(workingTexCoords);
    float waveHeightX = wo.waveHeightX;
    float waveHeightY = wo.waveHeightY;

    vec3 waveNormalTangent = vec3(0.0, 0.0, 1.0);
    waveNormalTangent.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    waveNormalTangent = normalize(waveNormalTangent);

    float waveHeight = 0.5 * waveAmplitude * (waveHeightX + waveHeightY);

    // world-space normal
    vec3 finalNormal = normalize(TBN * waveNormalTangent);

    // environment reflection
    vec3 reflectDir = reflect(-viewDir, finalNormal);
    vec3 refractDir = refract(-viewDir, finalNormal, 1.0 / 1.33);
    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;
    float fresnel = pow(1.0 - dot(viewDir, finalNormal), 3.0);
    vec3 envColor = mix(refraction, reflection, fresnel);

    // shadows
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
        0.005,
        shadowStrength,
        surfaceDepth
        );
    }

    // local lighting
    vec3 color = vec3(0.0);
    if (lightingMode == 0)
    {
        vec3 diffuseColor = computeDiffuseLighting(finalNormal, viewDir, FragPos, waterBaseColor, TexCoords);
        diffuseColor = mix(diffuseColor, diffuseColor * (1.0 - shadow), shadowStrength);
        color = diffuseColor;
    }
    else
    {
        vec3 phongColor = computePhongLighting(finalNormal, viewDir, FragPos, waterBaseColor, TexCoords);
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color = phongColor;
    }

    // add environment reflection
    vec3 envTerm = envColor * environmentMapStrength;
    envTerm = mix(envTerm, envTerm * (1.0 - shadow), shadowStrength);
    color += envTerm;

    // tone/gamma
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);

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
