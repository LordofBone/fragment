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
// Flip toggles
// ------------------------------------------------------
uniform bool flipPlanarHorizontal;// If true, flip horizontally
uniform bool flipPlanarVertical;// If true, flip vertically

// ------------------------------------------------------
// Normal-distortion toggle
// ------------------------------------------------------
uniform bool usePlanarNormalDistortion;// if true => add normal-based distortion

void main()
{
    // ------------------------------------------------------
    // 1) Compute baseTexCoords for local maps
    //    (Optionally flip them if you also want normalMap sampling to respect flips)
    // ------------------------------------------------------
    vec2 baseTexCoords = TexCoords;

    // (Optional) If you want the normal map to be flipped as well:
    // if (flipPlanarHorizontal) {
    //     baseTexCoords.x = 1.0 - baseTexCoords.x;
    // }
    // if (flipPlanarVertical) {
    //     baseTexCoords.y = 1.0 - baseTexCoords.y;
    // }

    // ------------------------------------------------------
    // 2) Calculate the normal from normalMap (in tangent space => world space)
    // ------------------------------------------------------
    vec3 normalFromMap = texture(normalMap, baseTexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalFromMap);

    // ------------------------------------------------------
    // 3) Reflection environment
    // ------------------------------------------------------
    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 reflectDir = reflect(viewDir, (warped ? FragPos : normal));
    reflectDir = normalize(reflectDir);

    // A fallback color if the environment map has no coverage
    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 envColor = vec3(0.0);
    float ndotv = dot(viewDir, normal);

    if (ndotv > 0.0)
    {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        // If the returned envColor is very close to 0, blend in fallback
        envColor = mix(fallbackColor, envColor, step(0.05, length(envColor)));
    }
    else
    {
        // If the reflection is basically on the backside, just use fallback
        envColor = fallbackColor;
    }

    envColor *= (environmentMapStrength * reflectionStrength);

    // ------------------------------------------------------
    // 4) Local diffuse (for local lighting calculation)
    // ------------------------------------------------------
    vec3 diffuseColor = texture(diffuseMap, baseTexCoords, textureLodLevel).rgb;

    // ------------------------------------------------------
    // 5) Decide final coords to sample from screenTexture
    //    - If screenFacingPlanarTexture==true => reflection-based coords
    //      else => planar base coords
    // ------------------------------------------------------
    vec2 reflectionTexCoords = (reflectDir.xy + vec2(1.0)) * 0.5;
    vec2 baseOrReflectionCoords = (screenFacingPlanarTexture
    ? reflectionTexCoords
    : TexCoords);

    // ------------------------------------------------------
    // 6) Distortion (optionally) from the normal map
    //    - If usePlanarNormalDistortion == false => no distortion
    //    - If true => read normal map again *or* reuse normalFromMap RG
    //      (below we re-sample for clarity, but you could optimize)
    // ------------------------------------------------------
    vec2 distortion = vec2(0.0);
    if (usePlanarNormalDistortion)
    {
        // Distortion is typically from the normalMap RG channel
        vec2 normalRG = texture(normalMap, baseTexCoords).rg * 2.0 - 1.0;
        distortion = normalRG * distortionStrength;
    }

    // Combine baseOrReflectionCoords with distortion
    vec2 finalScreenCoords = baseOrReflectionCoords + distortion;

    // ------------------------------------------------------
    // 7) Flip finalScreenCoords if requested
    //    (so flipping affects the final background sample)
    // ------------------------------------------------------
    if (flipPlanarHorizontal)
    {
        finalScreenCoords.x = 1.0 - finalScreenCoords.x;
    }
    if (flipPlanarVertical)
    {
        finalScreenCoords.y = 1.0 - finalScreenCoords.y;
    }

    // Clamp so we don’t sample outside 0..1
    finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);

    // ------------------------------------------------------
    // 8) Sample the screenTexture
    // ------------------------------------------------------
    vec3 backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
    if (length(backgroundColor) < 0.05)
    {
        backgroundColor = fallbackColor;
    }

    // ------------------------------------------------------
    // 9) Shadow Calculation (if enabled)
    // ------------------------------------------------------
    float shadow = 0.0;
    if (shadowingEnabled)
    {
        shadow = ShadowCalculationStandard(FragPosLightSpace, shadowMap);
    }

    // ------------------------------------------------------
    // 10) Local lighting (Phong or Diffuse)
    // ------------------------------------------------------
    vec3 lighting;
    if (phongShading)
    {
        lighting = computePhongLighting(normal, viewDir, FragPos, diffuseColor);
    }
    else
    {
        lighting = computeDiffuseLighting(normal, FragPos, diffuseColor);
    }

    lighting *= (1.0 - shadow);

    // ------------------------------------------------------
    // 11) Combine “background” vs. local lighting + environment
    // ------------------------------------------------------
    vec3 result = mix(backgroundColor, lighting, opacity) + envColor;

    // ------------------------------------------------------
    // 12) Tone mapping & gamma (if enabled)
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
