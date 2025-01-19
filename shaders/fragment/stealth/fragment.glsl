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
uniform sampler2D shadowMap;

// ------------------------------------------------------
// Uniforms for toggles / settings
// ------------------------------------------------------
uniform vec3 viewPosition;

uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float opacity;
// Lighting mode selector: 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;
uniform float distortionStrength;
uniform float reflectionStrength;
uniform bool screenFacingPlanarTexture;
uniform float planarFragmentViewThreshold;
uniform bool shadowingEnabled;

// ------------------------------------------------------
// Flip toggles
// ------------------------------------------------------
uniform bool flipPlanarHorizontal;// If true, flip horizontally
uniform bool flipPlanarVertical;// If true, flip vertically

// ------------------------------------------------------
// Normal-distortion toggle
//   If true => add normal.xy * distortionStrength
//   If false => no offset
// ------------------------------------------------------
uniform bool usePlanarNormalDistortion;


void main()
{
    // ------------------------------------------------------
    // 1) Base TexCoords for local diffuse & normal maps
    //    (Optionally flip them here if you also want to flip your normalMap)
    // ------------------------------------------------------
    vec2 baseTexCoords = TexCoords;
    // if (flipPlanarHorizontal) {
    //     baseTexCoords.x = 1.0 - baseTexCoords.x;
    // }
    // if (flipPlanarVertical) {
    //     baseTexCoords.y = 1.0 - baseTexCoords.y;
    // }

    // ------------------------------------------------------
    // 2) Compute the normal from normalMap (tangent space => world space)
    // ------------------------------------------------------
    vec3 normalFromMap = texture(normalMap, baseTexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalFromMap);

    // ------------------------------------------------------
    // 3) Environment reflections (no effect on screen texture coords)
    // ------------------------------------------------------
    vec3 viewDir = normalize(viewPosition - FragPos);

    // For environment reflection: standard reflection about normal
    vec3 reflectDir = reflect(viewDir, normal);
    reflectDir = normalize(reflectDir);

    // A fallback color if environment map has no coverage
    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);

    // Sample environment
    float ndotv = dot(normal, viewDir);
    vec3 envColor = vec3(0.0);

    if (ndotv > 0.0)
    {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        // Blend in fallback if the envColor is near black
        envColor = mix(fallbackColor, envColor, step(0.05, length(envColor)));
    }
    else
    {
        // If the reflection is basically on the backside, just use fallback
        envColor = fallbackColor;
    }

    envColor *= (environmentMapStrength * reflectionStrength);

    // ------------------------------------------------------
    // 4) Local diffuse color (for local lighting)
    // ------------------------------------------------------
    vec3 diffuseColor = texture(diffuseMap, baseTexCoords, textureLodLevel).rgb;

    // ------------------------------------------------------
    // 5) Start with (optionally) flipped TexCoords for the screenTexture
    //    (We won't do reflection-based coords here,
    //     because reflection sampling for screen texture
    //     is effectively a "distortion" you can't turn off.)
    // ------------------------------------------------------
    vec2 finalScreenCoords = TexCoords;

    // Flip if requested
    if (flipPlanarHorizontal)
    {
        finalScreenCoords.x = 1.0 - finalScreenCoords.x;
    }
    if (flipPlanarVertical)
    {
        finalScreenCoords.y = 1.0 - finalScreenCoords.y;
    }

    // ------------------------------------------------------
    // 6) If usePlanarNormalDistortion == true, offset by normal.xy
    // ------------------------------------------------------
    if (usePlanarNormalDistortion)
    {
        // We can re-sample normalMap.rg or reuse normalFromMap.rg
        // (the latter is in world space though; typically you want tangent space's RG)
        // For clarity, just re-sample:
        vec2 nrg = texture(normalMap, baseTexCoords, textureLodLevel).rg * 2.0 - 1.0;
        finalScreenCoords += (nrg * distortionStrength);
    }

    // ------------------------------------------------------
    // 7) Screen-facing logic
    //    If screenFacingPlanarTexture == true => only apply screenTexture if facing camera
    //    else => always apply it
    // ------------------------------------------------------
    vec3 backgroundColor = fallbackColor;// default
    float facing = dot(normal, viewDir);

    if (screenFacingPlanarTexture)
    {
        if (facing > planarFragmentViewThreshold)// fragment faces camera
        {
            // clamp coords before sampling
            finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
            backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
        }
    }
    else
    {
        // clamp coords before sampling
        finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
        backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
    }

    // If the sampled color is near black, revert to fallback
    if (length(backgroundColor) < 0.05)
    {
        backgroundColor = fallbackColor;
    }

    // ------------------------------------------------------
    // 8) Shadow Calculation (if enabled)
    // ------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // ------------------------------------------------------
    // 9) Local lighting (Phong or Diffuse)
    // ------------------------------------------------------
    vec3 lighting;
    if (lightingMode == 0)
    {
        lighting = computeDiffuseLighting(normal, viewDir, FragPos, diffuseColor);
    }
    else if (lightingMode == 1)
    {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    }
    else if (lightingMode == 2)
    {
        // PBR (includes environment reflection inside)
        lighting = computePBRLighting(normal, viewDir, FragPos, diffuseColor);
    }

    lighting *= (1.0 - shadow);

    // ------------------------------------------------------
    // 10) Combine background vs. local lighting + environment
    // ------------------------------------------------------
    vec3 result = mix(backgroundColor, lighting, opacity) + envColor;

    // ------------------------------------------------------
    // 11) Tone mapping & gamma (if enabled)
    // ------------------------------------------------------
    if (applyToneMapping)
    {
        result = toneMapping(result);
    }
    if (applyGammaCorrection)
    {
        result = pow(result, vec3(1.0 / 2.2));
    }

    // ------------------------------------------------------
    // Final
    // ------------------------------------------------------
    FragColor = vec4(clamp(result, 0.0, 1.0), opacity);
}
