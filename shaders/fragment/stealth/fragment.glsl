#version 330 core
#include "common_funcs.glsl"

// ------------------------------------------------------
// Vertex inputs
// ------------------------------------------------------
in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

// ------------------------------------------------------
// Fragment outputs
// ------------------------------------------------------
out vec4 FragColor;

// ------------------------------------------------------
// Uniform Samplers
// ------------------------------------------------------
uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D screenTexture;
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

// ------------------------------------------------------
// Uniforms for toggles / settings
// ------------------------------------------------------
uniform vec3 viewPosition;

uniform float envMapLodLevel;
uniform bool  applyToneMapping;
uniform bool  applyGammaCorrection;
uniform float opacity;
uniform bool  phongShading;
uniform float distortionStrength;
uniform float reflectionStrength;
uniform float environmentMapStrength;
uniform bool  screenFacingPlanarTexture;
uniform bool  warped;
uniform bool  shadowingEnabled;

// ------------------------------------------------------
// NEW: Flip toggles
// ------------------------------------------------------
uniform bool flipHorizontal;// If true, flip in X
uniform bool flipVertical;// If true, flip in Y

// ------------------------------------------------------
// NEW: Normal-distortion toggle
// ------------------------------------------------------
uniform bool usePlanarNormalDistortion;// true => use "distortedCoords", false => use base coords

void main()
{
    // 1) Start with base TexCoords
    vec2 baseTexCoords = TexCoords;

    // 2) Optionally flip horizontally or vertically
    if (flipHorizontal) {
        baseTexCoords.x = 1.0 - baseTexCoords.x;
    }
    if (flipVertical) {
        baseTexCoords.y = 1.0 - baseTexCoords.y;
    }

    // ------------------------------------------------------
    // Normal from normalMap (tangent space => world space)
    // ------------------------------------------------------
    vec3 normalFromMap = texture(normalMap, baseTexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalFromMap);

    // ------------------------------------------------------
    // Reflection environment
    // ------------------------------------------------------
    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 reflectDir = reflect(viewDir, warped ? FragPos : normal);
    reflectDir = normalize(reflectDir);

    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 envColor = vec3(0.0);
    float ndotv = dot(viewDir, normal);

    if (ndotv > 0.0) {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        envColor = mix(fallbackColor, envColor, step(0.05, length(envColor)));
    }
    else {
        envColor = fallbackColor;
    }

    envColor *= environmentMapStrength * reflectionStrength;

    // ------------------------------------------------------
    // Diffuse color from diffuseMap
    // ------------------------------------------------------
    vec3 diffuseColor = texture(diffuseMap, baseTexCoords, textureLodLevel).rgb;

    // ------------------------------------------------------
    // Screen-distorted background:
    //   1) Reflection-based coords for a "fake" reflection => reflectionTexCoords
    //   2) Distortion from normalMap's RG => normalDistortion
    //   3) If screenFacingPlanarTexture is true => use reflectionTexCoords, else use baseTexCoords
    // ------------------------------------------------------
    vec2 reflectionTexCoords = (reflectDir.xy + vec2(1.0)) * 0.5;
    vec2 normalDist = (texture(normalMap, baseTexCoords).rg * 2.0 - 1.0) * distortionStrength;

    vec2 coordsForScreen;
    if (screenFacingPlanarTexture) {
        coordsForScreen = reflectionTexCoords;
    } else {
        coordsForScreen = baseTexCoords;
    }

    // If usePlanarNormalDistortion is false, skip adding normalDist
    vec2 finalScreenCoords = usePlanarNormalDistortion
    ? coordsForScreen + normalDist
    : coordsForScreen;

    // Make sure coords remain in [0..1]
    finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);

    vec3 backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
    if (length(backgroundColor) < 0.05) {
        backgroundColor = fallbackColor;
    }

    // ------------------------------------------------------
    // Shadow calculation
    // ------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // ------------------------------------------------------
    // Local lighting (Phong or Diffuse)
    // ------------------------------------------------------
    vec3 lighting;
    if (phongShading) {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    } else {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    lighting *= (1.0 - shadow);

    // ------------------------------------------------------
    // Combine background vs. local lighting
    // ------------------------------------------------------
    vec3 result = mix(backgroundColor, lighting, opacity) + envColor;

    // ------------------------------------------------------
    // Tone & Gamma
    // ------------------------------------------------------
    if (applyToneMapping) {
        result = toneMapping(result);
    }
    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(result, 0.0, 1.0), opacity);
}
