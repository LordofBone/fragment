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

// TBN rows (world space)
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

// 0 => diffuse, 1 => Phong, 2 => ...
uniform int lightingMode;
uniform bool shadowingEnabled;

// Wave / geometry parameters
uniform float surfaceDepth;
uniform float shadowStrength;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;

// If you want a base color for the water:
uniform vec3 waterBaseColor;// e.g. (0,0.3,0.4)

void main()
{
    // ---------------------------------------------------------
    // Reconstruct TBN (world space -> tangent space is transpose)
    // We need TBN to convert a tangent-space normal back to world space
    //   Because T, B, N are in world space, TBN transforms T->world, etc.
    //   So waveNormalTangent -> waveNormalWorld = TBN * waveNormalTangent
    // ---------------------------------------------------------
    mat3 TBN = mat3(TBNrow0, TBNrow1, TBNrow2);

    // 1) World-space view direction
    vec3 viewDir = normalize(cameraPos - FragPos);

    // ---------------------------------------------------------
    // 2) Procedural POM
    // ---------------------------------------------------------
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;

    if (pomHeightScale > 0.0)
    {
        // We already have "TangentViewPos" for the view in tangent space
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);

        workingTexCoords = ProceduralParallaxOcclusionMapping(
        TexCoords,
        tangentViewDir,
        depthOffset
        );
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    // ---------------------------------------------------------
    // 3) Build wave normal in TANGENT space
    // ---------------------------------------------------------
    WaveOutput wo = computeWave(workingTexCoords);

    // waveHeightX, waveHeightY
    float waveHeightX = wo.waveHeightX;
    float waveHeightY = wo.waveHeightY;

    // Build waveNormalTangent
    vec3 waveNormalTangent = vec3(0.0, 0.0, 1.0);
    waveNormalTangent.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    waveNormalTangent = normalize(waveNormalTangent);

    float waveHeight = 0.5 * waveAmplitude * (waveHeightX + waveHeightY);

    // ---------------------------------------------------------
    // 4) Convert wave normal to WORLD space
    // ---------------------------------------------------------
    vec3 finalNormal = normalize(TBN * waveNormalTangent);

    // ---------------------------------------------------------
    // 5) Reflection/Refraction in world space
    // ---------------------------------------------------------
    vec3 reflectDir = reflect(-viewDir, finalNormal);
    vec3 refractDir = refract(-viewDir, finalNormal, 1.0/1.33);// Water IOR approx 1.33

    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    float fresnel = pow(1.0 - dot(viewDir, finalNormal), 3.0);
    // "envColor" is your reflection/refraction blend
    vec3 envColor = mix(refraction, reflection, fresnel);

    // ---------------------------------------------------------
    // 6) Shadows (displaced)
    // ---------------------------------------------------------
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
        lightPositions[0], // pick your main directional light or pass one
        0.05,
        0.005,
        shadowStrength,
        surfaceDepth
        );
    }

    // ---------------------------------------------------------
    // 7) "No Double-Add" approach to lighting
    //    - We'll pass a "base water color" to the diffuse/Phong function
    //    - Then we add environment reflection at the end
    // ---------------------------------------------------------
    vec3 color = vec3(0.0);

    if (lightingMode == 0)
    {
        // e.g., Diffuse lighting with "waterBaseColor"
        vec3 diffuseColor = computeDiffuseLighting(finalNormal, viewDir, FragPos, waterBaseColor);
        // Shadow attenuation
        diffuseColor = mix(diffuseColor, diffuseColor*(1.0 - shadow), shadowStrength);
        color = diffuseColor;
    }
    else
    {
        // e.g., Phong lighting with "waterBaseColor"
        vec3 phongColor = computePhongLighting(finalNormal, viewDir, FragPos, waterBaseColor);
        // Shadow
        phongColor = mix(phongColor, phongColor*(1.0 - shadow), shadowStrength);
        color = phongColor;
    }

    // Now add the environment reflection/refraction
    // You can modulate it by shadow or fresnel, etc.
    vec3 envTerm = envColor * environmentMapStrength;

    // Optionally apply shadow to environment as well
    envTerm = mix(envTerm, envTerm*(1.0 - shadow), shadowStrength);

    color += envTerm;

    // ---------------------------------------------------------
    // 8) Tone & Gamma
    // ---------------------------------------------------------
    if (applyToneMapping)
    {
        color = toneMapping(color);
    }
    if (applyGammaCorrection)
    {
        color = pow(color, vec3(1.0/2.2));
    }

    FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
