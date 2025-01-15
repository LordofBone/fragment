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
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float opacity;
uniform bool phongShading;
uniform float distortionStrength;
uniform float reflectionStrength;
uniform float environmentMapStrength;
uniform bool screenFacingPlanarTexture;
uniform bool warped;
uniform bool shadowingEnabled;

// ------------------------------------------------------
// NEW: Flip toggles
// ------------------------------------------------------
uniform bool flipPlanarHorizontal;// If true, flip in X
uniform bool flipPlanarVertical;// If true, flip in Y

void main()
{
    // 1) Start with base TexCoords
    vec2 baseTexCoords = TexCoords;

    // 2) Optionally flip horizontally or vertically
    //    (If you want to comment/uncomment, treat them as #ifdef or pass in booleans from host)
    if (flipPlanarHorizontal) {
        baseTexCoords.x = 1.0 - baseTexCoords.x;
    }
    if (flipPlanarVertical) {
        baseTexCoords.y = 1.0 - baseTexCoords.y;
    }

    // ------------------------------------------------------
    // Normal from normalMap (tangent space => world space)
    // ------------------------------------------------------
    vec3 normalFromMap = texture(normalMap, baseTexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalFromMap);

    // ------------------------------------------------------
    // Basic reflection environment
    // ------------------------------------------------------
    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 reflectDir = reflect(viewDir, warped ? FragPos : normal);
    reflectDir = normalize(reflectDir);

    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 envColor = vec3(0.0);
    float ndotv = dot(viewDir, normal);

    if (ndotv > 0.0) {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        // If envColor is near zero, we fallback
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
    // "Screen-distorted" background: how we fetch the screenTexture
    // ------------------------------------------------------
    // Reflection-based coords for a "fake" reflection
    vec2 reflectionTexCoords = (reflectDir.xy + vec2(1.0)) * 0.5;

    // Distortion from normalMap's red/green
    vec2 normalDistortion = (texture(normalMap, baseTexCoords).rg * 2.0 - 1.0) * distortionStrength;

    vec2 distortedCoords;
    if (screenFacingPlanarTexture) {
        // If we want to map reflection direction onto the planar texture
        distortedCoords = reflectionTexCoords + normalDistortion;
    }
    else {
        // Otherwise, just distort the base uv
        distortedCoords = baseTexCoords + normalDistortion;
    }

    // Make sure coords remain in [0..1]
    distortedCoords = clamp(distortedCoords, 0.0, 1.0);

    // Sample screenTexture
    vec3 backgroundColor = texture(screenTexture, distortedCoords).rgb;
    if (length(backgroundColor) < 0.05) {
        backgroundColor = fallbackColor;
    }

    // ------------------------------------------------------
    // Optional shadow calculation
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
    }
    else {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    lighting *= (1.0 - shadow);

    // ------------------------------------------------------
    // Combine background vs. local lighting
    // ------------------------------------------------------
    vec3 result = mix(backgroundColor, lighting, opacity) + envColor;

    // ------------------------------------------------------
    // Tone & gamma
    // ------------------------------------------------------
    if (applyToneMapping) {
        result = toneMapping(result);
    }
    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    FragColor = vec4(clamp(result, 0.0, 1.0), opacity);
}
