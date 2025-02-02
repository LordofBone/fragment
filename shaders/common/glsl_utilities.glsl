#ifndef COMMON_FUNCS_GLSL
#define COMMON_FUNCS_GLSL

// ---------------------------------------------------
// Global Uniforms and Samplers
// ---------------------------------------------------
uniform float textureLodLevel;
uniform sampler2D normalMap;

uniform samplerCube environmentMap;// Cubemap with MIP levels
uniform float environmentMapStrength;
uniform float envMapLodLevel;// Used by sampleEnvironmentMapLod()

uniform sampler2D screenTexture;

uniform bool usePlanarNormalDistortion;
uniform float distortionStrength;
uniform float refractionStrength;
uniform bool screenFacingPlanarTexture;
uniform float planarFragmentViewThreshold;

uniform bool flipPlanarHorizontal;// Flip screen texture horizontally
uniform bool flipPlanarVertical;// Flip screen texture vertically

// Add a uniform that tells the shader whether the object is a surface.
uniform bool surfaceMapping;// if true, use fragPos.x and fragPos.z for bounds check

// ---------------------------------------------------
// Parallax Occlusion Mapping (POM) Uniforms
// ---------------------------------------------------
uniform float pomHeightScale;
uniform int pomMinSteps;
uniform int pomMaxSteps;
uniform sampler2D displacementMap;
uniform bool invertDisplacementMap;
uniform bool useCheckerPattern;
uniform float parallaxEyeOffsetScale;
uniform float parallaxMaxDepthClamp;
uniform float maxForwardOffset;// Maximum forward offset (in NDC)
uniform bool enableFragDepthAdjustment;

// ---------------------------------------------------
// Liquid Simulation / Wave Uniforms
// ---------------------------------------------------
uniform float time;
uniform float waveSpeed;
uniform float waveAmplitude;
uniform float waveDetail;
uniform float randomness;
uniform float texCoordFrequency;
uniform float texCoordAmplitude;

// ---------------------------------------------------
// Global Lighting Uniforms
// ---------------------------------------------------
uniform float ambientStrength;// 0.0 => no ambient, 1.0 => full ambient intensity
uniform vec3 ambientColor;
uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];
uniform float lightOrthoLeft[10];
uniform float lightOrthoRight[10];
uniform float lightOrthoBottom[10];
uniform float lightOrthoTop[10];
uniform float legacyRoughness;
uniform float legacyOpacity;

// ---------------------------------------------------
// Extended PBR Material Structure
// ---------------------------------------------------
struct Material {
    vec3 ambient;// from Ka
    vec3 diffuse;// from Kd
    vec3 specular;// from Ks
    vec3 emissive;// from Ke
    float fresnelExponent;// from Pfe (non-standard parameter)
    int illuminationModel;// from illum

// "Core" PBR fields
    float roughness;// 'Pr' in Blender MTL
    float metallic;// 'Pm' in Blender MTL

// Additional MTL parameters
    float ior;// Ni (index of refraction)
    float transparency;// d (alpha/dissolve) (currently unused)
    float clearcoat;// Pc
    float clearcoatRoughness;// Pcr
    float sheen;// Ps
    float anisotropy;// aniso
    float anisotropyRot;// anisor
    vec3 transmission;// Tf
};
uniform Material material;

// ---------------------------------------------------
// Helper Functions to Make Code DRY
// ---------------------------------------------------

// ---------------------------------------------------
// Environment Map Sampling Functions
// ---------------------------------------------------
vec4 sampleEnvironmentMap(vec3 envMapTexCoords)
{
    return texture(environmentMap, envMapTexCoords);
}

vec4 sampleEnvironmentMapLod(vec3 envMapTexCoords)
{
    return textureLod(environmentMap, envMapTexCoords, envMapLodLevel);
}

// Returns 1.0 if fragPos is within the i-th light's orthogonal bounds.
// If surfaceMapping is true, use fragPos.x and fragPos.z instead of fragPos.x and fragPos.y.
float lightWithinBounds(int i, vec3 fragPos) {
    if (surfaceMapping) {
        return 1.0;// bypass bounds check for surfaces
    } else {
        return step(lightOrthoLeft[i], fragPos.x) *
        step(fragPos.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], fragPos.y) *
        step(fragPos.y, lightOrthoTop[i]);
    }
}

// Flips and applies normal-based distortion to texture coordinates.
// Returns the modified (clamped) screen texture coordinates.
vec2 flipAndDistortTexCoords(vec2 texCoords) {
    vec2 finalCoords = texCoords;
    if (flipPlanarHorizontal) {
        finalCoords.x = 1.0 - finalCoords.x;
    }
    if (flipPlanarVertical) {
        finalCoords.y = 1.0 - finalCoords.y;
    }
    if (usePlanarNormalDistortion) {
        vec2 nrg = texture(normalMap, texCoords, textureLodLevel).rg * 2.0 - 1.0;
        finalCoords += (nrg * distortionStrength);
    }
    return clamp(finalCoords, 0.0, 1.0);
}

// Applies the screen texture transparency step. This function samples the
// screen texture using the (flipped/distorted) coordinates, does an optional
// screen-facing check, and then mixes the provided lighting result with the
// background color based on legacyOpacity.
vec3 applyScreenTexture(vec3 normal, vec3 viewDir, vec2 texCoords, vec3 lightingResult) {
    vec2 finalCoords = flipAndDistortTexCoords(texCoords);
    vec3 fallbackColor = vec3(0.0);
    vec3 backgroundColor = fallbackColor;
    if (screenFacingPlanarTexture) {
        float facing = dot(normal, viewDir);
        if (facing > planarFragmentViewThreshold) {
            backgroundColor = texture(screenTexture, finalCoords).rgb;
        }
    } else {
        backgroundColor = texture(screenTexture, finalCoords).rgb;
    }
    if (length(backgroundColor) < 0.05) {
        backgroundColor = fallbackColor;
    }
    return mix(backgroundColor, lightingResult, legacyOpacity);
}

// Helper to add environment reflection to a lighting result.
// Computes a reflection vector from viewDir and normal, then samples the
// environment map (using a fixed LOD via envMapLodLevel) and mixes the result
// into the lighting result based on environmentMapStrength.
// (Non‐PBR functions use this fixed LOD method.)
vec3 applyEnvironmentReflection(vec3 normal, vec3 viewDir, vec3 lightingResult) {
    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 envColor = sampleEnvironmentMapLod(reflectDir).rgb;
    // In diffuse, you might want to scale by a roughness factor—
    // here we simply mix by environmentMapStrength.
    return mix(lightingResult, lightingResult + envColor, environmentMapStrength);
}

// ---------------------------------------------------
// Improved Integer-based Hash and Rand Functions
// ---------------------------------------------------
uint hash(uint x)
{
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}

float rand(uint seed)
{
    return float(hash(seed)) / 4294967295.0;
}

// ---------------------------------------------------
// Pseudo-random Function for Color Variation
// ---------------------------------------------------
float generateRandomValue(vec2 uv, float id)
{
    return fract(sin(dot(uv + id, vec2(12.9898, 78.233))) * 43758.5453);
}

// ---------------------------------------------------
// Noise and Smooth Noise Functions
// ---------------------------------------------------
float noise(vec2 p)
{
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float smoothNoise(vec2 p)
{
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
    mix(noise(i + vec2(0.0, 0.0)), noise(i + vec2(1.0, 0.0)), f.x),
    mix(noise(i + vec2(0.0, 1.0)), noise(i + vec2(1.0, 1.0)), f.x),
    f.y
    );
}

// ---------------------------------------------------
// Fluid Forces Calculation
// ---------------------------------------------------
vec3 calculateFluidForces(
vec3 velocity,
vec3 adjustedGravity,
float fluidPressure,
float fluidViscosity,
float fluidForceMultiplier
)
{
    float gravityNorm = length(adjustedGravity);
    float computedMaxFluidForce = gravityNorm * fluidForceMultiplier;
    vec3 pressureForce = -velocity * fluidPressure;
    vec3 viscosityForce = -velocity * fluidViscosity;
    vec3 totalFluidForce = pressureForce + viscosityForce;
    float forceMag = length(totalFluidForce);
    if (forceMag > computedMaxFluidForce && forceMag > 0.0) {
        totalFluidForce = normalize(totalFluidForce) * computedMaxFluidForce;
    }
    return totalFluidForce;
}

// ---------------------------------------------------
// Cubemap Sampling Helpers: Tent, Bicubic, Lanczos
// ---------------------------------------------------
vec4 sampleCubemapTent(samplerCube cubemap, vec3 dir, float offset)
{
    vec4 center = texture(cubemap, dir);
    vec3 right = normalize(cross(dir, vec3(0.0, 1.0, 0.0)));
    vec3 up = normalize(cross(right, dir));
    vec3 dir1 = normalize(dir + offset * right);
    vec3 dir2 = normalize(dir - offset * right);
    vec3 dir3 = normalize(dir + offset * up);
    vec4 col1 = texture(cubemap, dir1);
    vec4 col2 = texture(cubemap, dir2);
    vec4 col3 = texture(cubemap, dir3);
    return (center * 0.4 + col1 * 0.2 + col2 * 0.2 + col3 * 0.2);
}

float catmullRom1D(float x)
{
    x = abs(x);
    float x2 = x * x;
    float x3 = x * x2;
    if (x <= 1.0) {
        return 1.5 * x3 - 2.5 * x2 + 1.0;
    } else if (x < 2.0) {
        return -0.5 * x3 + 2.5 * x2 - 4.0 * x + 2.0;
    }
    return 0.0;
}

float bicubicWeight2D(float u, float v)
{
    return catmullRom1D(u) * catmullRom1D(v);
}

vec4 sampleCubemapBicubic(samplerCube cubemap, vec3 dir, float baseOffset)
{
    vec3 fwd = normalize(dir);
    vec3 tempUp = abs(fwd.y) < 0.99 ? vec3(0, 1, 0) : vec3(1, 0, 0);
    vec3 side = normalize(cross(fwd, tempUp));
    vec3 up = normalize(cross(side, fwd));
    vec4 accumColor = vec4(0.0);
    float accumWeight = 0.0;
    for (int i = 0; i < 4; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            float offU = float(i) - 1.5;
            float offV = float(j) - 1.5;
            float w = bicubicWeight2D(offU, offV);
            vec3 sampleDir = fwd + (offU * baseOffset) * side + (offV * baseOffset) * up;
            sampleDir = normalize(sampleDir);
            vec4 c = texture(cubemap, sampleDir);
            accumColor += c * w;
            accumWeight += w;
        }
    }
    if (accumWeight > 0.0)
    return accumColor / accumWeight;
    else
    return texture(cubemap, dir);
}

float lanczos1D(float x, float lobes)
{
    x = abs(x);
    if (x < 1e-5)
        return 1.0;
    if (x > lobes)
        return 0.0;
    float pi_x = 3.14159265359 * x;
    float pi_xL = pi_x / lobes;
    return (sin(pi_x) / pi_x) * (sin(pi_xL) / pi_xL);
}

float lanczos2D(float u, float v, float lobes)
{
    return lanczos1D(u, lobes) * lanczos1D(v, lobes);
}

vec4 sampleCubemapLanczos(
samplerCube cubemap,
vec3 dir,
float baseOffset,
float lobes,
int sampleRadius,
float stepSize
)
{
    vec3 fwd = normalize(dir);
    vec3 tempUp = (abs(fwd.y) < 0.99) ? vec3(0, 1, 0) : vec3(1, 0, 0);
    vec3 side = normalize(cross(fwd, tempUp));
    vec3 up = normalize(cross(side, fwd));
    vec4 accumColor = vec4(0.0);
    float accumWeight = 0.0;
    float minRange = -float(sampleRadius);
    float maxRange = float(sampleRadius) + 0.001;
    for (float i = minRange; i <= maxRange; i += stepSize)
    {
        for (float j = minRange; j <= maxRange; j += stepSize)
        {
            float w = lanczos2D(i, j, lobes);
            vec3 sampleDir = fwd + (i * baseOffset) * side + (j * baseOffset) * up;
            sampleDir = normalize(sampleDir);
            vec4 c = texture(cubemap, sampleDir);
            accumColor += c * w;
            accumWeight += w;
        }
    }
    if (accumWeight > 0.0)
    return accumColor / accumWeight;
    else
    return texture(cubemap, dir);
}

//vec4 sampleEnvironmentMap(vec3 envMapTexCoords)
//{
//    return texture(environmentMap, envMapTexCoords);
//}
//
//vec4 sampleEnvironmentMapLod(vec3 envMapTexCoords)
//{
//    return textureLod(environmentMap, envMapTexCoords, envMapLodLevel);
//}

// ---------------------------------------------------
// Tone Mapping Functions (Uncharted2)
// ---------------------------------------------------
vec3 Uncharted2Tonemap(vec3 x)
{
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;
    return ((x * (A * x + C * B) + D * E) /
    (x * (A * x + B) + D * F)) - E / F;
}

vec3 toneMapping(vec3 color)
{
    vec3 curr = Uncharted2Tonemap(color * 2.0);
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

// ---------------------------------------------------
// Standard PCF Shadow Calculation (Non-displaced)
// ---------------------------------------------------
float ShadowCalculationStandard(
vec4 fragPosLightSpace,
sampler2D shadowMap
) {
    float shadow = 0.0;
    for (int i = 0; i < 10; ++i) {
        vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
        projCoords = projCoords * 0.5 + 0.5;
        float withinBounds =
        step(lightOrthoLeft[i], projCoords.x) *
        step(projCoords.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], projCoords.y) *
        step(projCoords.y, lightOrthoTop[i]) *
        step(0.0, projCoords.z) *
        step(projCoords.z, 1.0);
        if (withinBounds > 0.0) {
            float closestDepth = texture(shadowMap, projCoords.xy).r;
            float currentDepth = projCoords.z;
            float bias = 0.005;
            vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
            float lightShadow = 0.0;
            for (int x = -1; x <= 1; ++x) {
                for (int y = -1; y <= 1; ++y) {
                    float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
                    lightShadow += (currentDepth - bias > pcfDepth) ? 1.0 : 0.0;
                }
            }
            lightShadow /= 9.0;
            shadow += lightShadow * lightStrengths[i];
        }
    }
    shadow = clamp(shadow / 10.0, 0.0, 1.0);
    return shadow;
}

// ---------------------------------------------------
// Displaced/Wave-Based Shadow Calculation
// ---------------------------------------------------
float ShadowCalculationDisplaced(
vec3 fragPosWorld,
vec3 normal,
float waveHeight,
sampler2D shadowMap,
mat4 lightSpaceMatrix,
mat4 model,
vec3 lightPos,
float biasFactor,
float minBias,
float shadowStrength,
float surfaceDepth
)
{
    vec3 displacedPos = fragPosWorld;
    displacedPos.y += waveHeight;
    vec4 fragPosLightSpace = lightSpaceMatrix * model * vec4(displacedPos, 1.0);
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;
    if (projCoords.x < 0.0 || projCoords.x > 1.0 ||
    projCoords.y < 0.0 || projCoords.y > 1.0 ||
    projCoords.z < 0.0 || projCoords.z > 1.0)
    {
        return 0.0;
    }
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    float currentDepth = projCoords.z;
    float bias = max(biasFactor * (1.0 - dot(normal, normalize(lightPos - displacedPos))), minBias);
    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    int samples = 3;
    for (int x = -samples; x <= samples; x++) {
        for (int y = -samples; y <= samples; y++) {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            float comparison = currentDepth - bias - pcfDepth;
            shadow += smoothstep(0.0, 0.005, comparison);
        }
    }
    shadow /= float((samples * 2 + 1) * (samples * 2 + 1));
    shadow *= exp(-surfaceDepth * 0.1) * shadowStrength;
    shadow = clamp(shadow, 0.0, 1.0);
    return shadow;
}

// ---------------------------------------------------
// Basic Ambient Lighting
// ---------------------------------------------------
vec3 computeAmbientColor(vec3 baseColor)
{
    return baseColor * ambientColor * ambientStrength;
}

// ---------------------------------------------------
// Compute Diffuse Lighting with Opacity and Environment Reflection
// ---------------------------------------------------
vec3 computeDiffuseLighting(
vec3 normal,
vec3 viewDir,
vec3 fragPos,
vec3 baseColor,
vec2 texCoords
) {
    vec3 ambient = computeAmbientColor(baseColor);
    vec3 diffuse = vec3(0.0);
    for (int i = 0; i < 10; ++i) {
        if (lightWithinBounds(i, fragPos) > 0.0) {
            vec3 lightDir = normalize(lightPositions[i] - fragPos);
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];
        }
    }
    vec3 result = ambient + diffuse;
    // Add environment reflection using a fixed LOD from the uniform
    result = mix(result, result + sampleEnvironmentMapLod(reflect(-viewDir, normal)).rgb,
    environmentMapStrength * clamp(1.0 - (legacyRoughness / 100.0), 0.0, 1.0));
    return applyScreenTexture(normal, viewDir, texCoords, result);
}

// ---------------------------------------------------
// Compute Phong Lighting with Opacity and Environment Reflection
// ---------------------------------------------------
vec3 computePhongLighting(
vec3 normal,
vec3 viewDir,
vec3 fragPos,
vec3 baseColor,
vec2 texCoords
) {
    vec3 ambient = computeAmbientColor(baseColor);
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specularColor = vec3(1.0);
    for (int i = 0; i < 10; ++i) {
        if (lightWithinBounds(i, fragPos) > 0.0) {
            vec3 lightDir = normalize(lightPositions[i] - fragPos);
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];
            vec3 halfwayDir = normalize(lightDir + viewDir);
            float spec = pow(max(dot(normal, halfwayDir), 0.0), legacyRoughness);
            specular += spec * specularColor * lightColors[i] * lightStrengths[i];
        }
    }
    vec3 result = ambient + diffuse + specular;
    // Add environment reflection (no roughness scaling here)
    result = mix(result, result + sampleEnvironmentMapLod(reflect(-viewDir, normal)).rgb,
    environmentMapStrength);
    return applyScreenTexture(normal, viewDir, texCoords, result);
}

// ---------------------------------------------------
// Particle-specific Diffuse Lighting with Distance Attenuation
// ---------------------------------------------------
vec3 computeParticleDiffuseLighting(vec3 normal, vec3 fragPos, vec3 baseColor)
{
    vec3 ambient = computeAmbientColor(baseColor);
    vec3 diffuse = vec3(0.0);
    for (int i = 0; i < 10; i++) {
        if (lightWithinBounds(i, fragPos) > 0.0) {
            vec3 lightVec = lightPositions[i] - fragPos;
            float distance = length(lightVec);
            vec3 lightDir = normalize(lightVec);
            float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];
        }
    }
    return ambient + diffuse;
}

// ---------------------------------------------------
// Particle-specific Phong Lighting with Distance Attenuation
// ---------------------------------------------------
vec3 computeParticlePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor)
{
    vec3 ambient = computeAmbientColor(baseColor);
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    for (int i = 0; i < 10; ++i) {
        if (lightWithinBounds(i, fragPos) > 0.0) {
            vec3 lightVec = lightPositions[i] - fragPos;
            float distance = length(lightVec);
            vec3 lightDir = normalize(lightVec);
            float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];
            vec3 halfwayDir = normalize(lightDir + viewDir);
            float specAngle = max(dot(normal, halfwayDir), 0.0);
            float spec = pow(specAngle, max(legacyRoughness, 0.0));
            specular += attenuation * spec * lightColors[i] * lightStrengths[i];
        }
    }
    return ambient + diffuse + specular;
}

// ---------------------------------------------------
// Common PBR Helpers (GGX, Smith, Schlick)
// ---------------------------------------------------
float DistributionGGX(vec3 N, vec3 H, float roughness)
{
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = 3.14159265359 * denom * denom;
    return a2 / denom;
}

float GeometrySchlickGGX(float NdotV, float k)
{
    return NdotV / (NdotV * (1.0 - k) + k);
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness)
{
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx1 = GeometrySchlickGGX(NdotV, k);
    float ggx2 = GeometrySchlickGGX(NdotL, k);
    return ggx1 * ggx2;
}

vec3 fresnelSchlick(float cosTheta, vec3 F0)
{
    return F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
}

vec3 fresnelSchlickExponent(float cosTheta, vec3 F0, float exponent)
{
    vec3 base = F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
    return pow(base, vec3(exponent));
}

// ---------------------------------------------------
// Additional PBR Helpers
// ---------------------------------------------------
vec3 computeF0FromIOR(float ior)
{
    float r0 = (ior - 1.0) / (ior + 1.0);
    r0 *= r0;
    return vec3(r0);
}

vec3 computeF0Combined(vec3 baseColor, float metallic, vec3 specular, float ior)
{
    vec3 dielectricF0 = computeF0FromIOR(ior);
    vec3 baseF0 = mix(dielectricF0, baseColor, metallic);
    baseF0 = max(baseF0, specular);
    return baseF0;
}

// ---------------------------------------------------
// Compute PBR Lighting with Extended Material Parameters
// ---------------------------------------------------
const float PI = 3.14159265359;
const float MAX_MIPS = 5.0;// For environment map MIP

vec3 computePBRLighting(
vec3 N,
vec3 V,
vec3 fragPos,
vec3 baseColor,
vec2 texCoords
) {
    float effectiveRoughness = clamp(material.roughness, 0.0, 1.0);
    vec3 localLighting = vec3(0.0);
    vec3 F0 = computeF0Combined(baseColor, material.metallic, material.specular, material.ior);
    for (int i = 0; i < 10; i++) {
        if (lightWithinBounds(i, fragPos) > 0.0) {
            vec3 L = normalize(lightPositions[i] - fragPos);
            vec3 H = normalize(V + L);
            float NdotL = max(dot(N, L), 0.0);
            float D = DistributionGGX(N, H, effectiveRoughness);
            float G = GeometrySmith(N, V, L, effectiveRoughness);
            float NdotV = max(dot(N, V), 0.0);
            float HdotV = max(dot(H, V), 0.0);
            vec3 F = fresnelSchlick(HdotV, F0);
            float denom = 4.0 * NdotV * NdotL + 0.0001;
            vec3 specular = (D * G * F) / denom;
            vec3 kS = F;
            vec3 kD = (vec3(1.0) - kS) * (1.0 - material.metallic);
            vec3 diffuse = kD * baseColor;
            localLighting += (diffuse + specular) * lightColors[i] * lightStrengths[i] * NdotL;
        }
    }
    float NdotV = max(dot(N, V), 0.0);
    vec3 reflectDir = reflect(-V, N);
    float mipLevel = effectiveRoughness * MAX_MIPS;
    vec3 envSample = textureLod(environmentMap, reflectDir, mipLevel).rgb;
    float exponent = material.fresnelExponent;
    vec3 F_env = fresnelSchlickExponent(NdotV, F0, exponent);
    float G_approx = 1.0;
    vec3 environmentSpec = envSample * F_env * G_approx;
    float reflectionFactor = environmentMapStrength * clamp(1.0 - effectiveRoughness, 0.0, 1.0);
    vec3 environmentContribution = environmentSpec * reflectionFactor;
    vec3 clearcoatContrib = vec3(0.0);
    if (material.clearcoat > 0.001) {
        float ccRough = clamp(material.clearcoatRoughness, 0.0, 1.0);
        vec3 H_cc = normalize(V + reflect(-V, N));
        float NdotV_cc = max(dot(N, V), 0.0);
        float D_cc = DistributionGGX(N, H_cc, ccRough);
        float G_cc = GeometrySmith(N, V, -V, ccRough);
        vec3 F0_cc = vec3(0.25);
        vec3 F_cc = fresnelSchlick(NdotV_cc, F0_cc);
        float denom_cc = 4.0 * NdotV_cc * NdotV_cc + 0.0001;
        vec3 spec_cc = (D_cc * G_cc * F_cc) / denom_cc;
        spec_cc *= material.clearcoat;
        clearcoatContrib = spec_cc * environmentMapStrength;
    }
    vec3 sheenContrib = vec3(0.0);
    if (material.sheen > 0.001) {
        float edgeFactor = pow(1.0 - NdotV, 5.0);
        vec3 sheenColor = mix(baseColor, vec3(1.0), 0.5);
        sheenContrib = sheenColor * edgeFactor * material.sheen;
    }
    vec3 finalColor = localLighting + environmentContribution + clearcoatContrib + sheenContrib;
    finalColor += material.emissive;
    vec3 ambientTerm = computeAmbientColor(finalColor);
    finalColor += ambientTerm;
    float averageTf = (material.transmission.r + material.transmission.g + material.transmission.b) / 3.0;
    if (averageTf > 0.001) {
        vec2 finalScreenCoords = texCoords;
        if (usePlanarNormalDistortion) {
            float refractionRatio = 1.0 / material.ior;
            vec3 refractDir = refract(-V, N, refractionRatio);
            vec2 refOffset = refractDir.xy * 0.5;
            finalScreenCoords += (refOffset * refractionStrength);
        }
        if (flipPlanarHorizontal) {
            finalScreenCoords.x = 1.0 - finalScreenCoords.x;
        }
        if (flipPlanarVertical) {
            finalScreenCoords.y = 1.0 - finalScreenCoords.y;
        }
        if (usePlanarNormalDistortion) {
            vec2 nrg = texture(normalMap, texCoords).rg * 2.0 - 1.0;
            finalScreenCoords += (nrg * distortionStrength);
        }
        finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
        vec3 fallbackColor = vec3(0.0);
        vec3 refr2D;
        if (screenFacingPlanarTexture) {
            refr2D = (dot(N, V) > planarFragmentViewThreshold) ? texture(screenTexture, finalScreenCoords).rgb : fallbackColor;
        } else {
            refr2D = texture(screenTexture, finalScreenCoords).rgb;
        }
        if (length(refr2D) < 0.05)
            refr2D = fallbackColor;
        refr2D *= material.transmission;
        finalColor = mix(finalColor, refr2D, averageTf);
    }
    return finalColor;
}

// ---------------------------------------------------
// Wave Computation Helpers
// ---------------------------------------------------
struct WaveOutput {
    vec2  waveTexCoords;// Offset texture coordinates
    float waveHeightX;
    float waveHeightY;
    float waveVal;// Combined wave value
};

WaveOutput computeWave(vec2 baseTexCoords)
{
    WaveOutput wo;
    vec2 waveTexCoords = baseTexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + baseTexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + baseTexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    wo.waveTexCoords = waveTexCoords;
    float waveHeightX = sin(waveTexCoords.y * waveDetail);
    float waveHeightY = cos(waveTexCoords.x * waveDetail);
    wo.waveHeightX = waveHeightX;
    wo.waveHeightY = waveHeightY;
    float waveVal = 0.5 * (waveHeightX + waveHeightY);
    waveVal *= waveAmplitude;
    wo.waveVal = waveVal;
    return wo;
}

float proceduralDisplacement(vec2 coords)
{
    WaveOutput wo = computeWave(coords);
    float finalH = 0.5 + 0.5 * wo.waveVal;
    finalH = clamp(finalH, 0.0, 1.0);
    return finalH;
}

// ---------------------------------------------------
// Parallax Occlusion Mapping (POM)
// ---------------------------------------------------
vec2 ParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset)
{
    float numLayers = mix(float(pomMaxSteps), float(pomMinSteps), abs(viewDir.z));
    float layerDepth = 1.0 / numLayers;
    float currentLayerDepth = 0.0;
    vec2 P = viewDir.xy * pomHeightScale;
    vec2 deltaTexCoords = P / numLayers;
    vec2 currentTexCoords = texCoords;
    float currentDepthMapValue = texture(displacementMap, currentTexCoords, textureLodLevel).r;
    if (invertDisplacementMap) {
        currentDepthMapValue = 1.0 - currentDepthMapValue;
    }
    float depthFromTexture = currentDepthMapValue;
    while (currentLayerDepth < depthFromTexture) {
        currentTexCoords -= deltaTexCoords;
        currentDepthMapValue = texture(displacementMap, currentTexCoords, textureLodLevel).r;
        if (invertDisplacementMap) {
            currentDepthMapValue = 1.0 - currentDepthMapValue;
        }
        depthFromTexture = currentDepthMapValue;
        currentLayerDepth += layerDepth;
    }
    vec2 prevTexCoords = currentTexCoords + deltaTexCoords;
    float prevLayerDepth = currentLayerDepth - layerDepth;
    float prevDepthFromTexture = texture(displacementMap, prevTexCoords, textureLodLevel).r;
    if (invertDisplacementMap) {
        prevDepthFromTexture = 1.0 - prevDepthFromTexture;
    }
    float weight = (depthFromTexture - currentLayerDepth) /
    ((depthFromTexture - currentLayerDepth) - (prevDepthFromTexture - prevLayerDepth));
    vec2 finalTexCoords = mix(currentTexCoords, prevTexCoords, weight);
    depthOffset = pomHeightScale * (1.0 - mix(currentLayerDepth, prevLayerDepth, weight)) * 0.0001;
    return finalTexCoords;
}

vec2 ProceduralParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset)
{
    float numLayers = mix(float(pomMaxSteps), float(pomMinSteps), abs(viewDir.z));
    float layerDepth = 1.0 / numLayers;
    float currentLayerDepth = 0.0;
    vec2 P = viewDir.xy * pomHeightScale;
    vec2 deltaTexCoords = P / numLayers;
    vec2 currentTexCoords = texCoords;
    float currentDepth = proceduralDisplacement(currentTexCoords);
    if (invertDisplacementMap) currentDepth = 1.0 - currentDepth;
    float depthFromTexture = currentDepth;
    while (currentLayerDepth < depthFromTexture) {
        currentTexCoords -= deltaTexCoords;
        currentDepth = proceduralDisplacement(currentTexCoords);
        if (invertDisplacementMap) currentDepth = 1.0 - currentDepth;
        depthFromTexture = currentDepth;
        currentLayerDepth += layerDepth;
    }
    vec2 prevTexCoords = currentTexCoords + deltaTexCoords;
    float prevLayerDepth = currentLayerDepth - layerDepth;
    float prevDepth = proceduralDisplacement(prevTexCoords);
    if (invertDisplacementMap) prevDepth = 1.0 - prevDepth;
    float weight = (depthFromTexture - currentLayerDepth) /
    ((depthFromTexture - currentLayerDepth) - (prevDepth - prevLayerDepth));
    vec2 finalTexCoords = mix(currentTexCoords, prevTexCoords, weight);
    depthOffset = pomHeightScale * (1.0 - mix(currentLayerDepth, prevLayerDepth, weight)) * 0.0001;
    return finalTexCoords;
}

// ---------------------------------------------------
// Adjust Fragment Depth with Optional Clamping
// ---------------------------------------------------
void adjustFragDepth(
vec4 viewPos,
mat4 projectionMatrix,
vec4 fragPosWorld,
vec3 TBN[3],
float depthOffset,
inout float fragDepth
) {
    vec4 eyePos = viewPos;
    vec3 offsetTangent = vec3(0.0, 0.0, -depthOffset);
    vec3 offsetWorld = mat3(TBN[0], TBN[1], TBN[2]) * offsetTangent;
    vec4 offsetEye = vec4(offsetWorld, 0.0);
    vec4 newEyePos = eyePos + offsetEye;
    vec4 clipPos = projectionMatrix * newEyePos;
    float ndcDepth = clipPos.z / clipPos.w;
    ndcDepth = clamp(ndcDepth, 0.0, parallaxMaxDepthClamp);
    float oldZ = fragDepth;
    float allowedMinZ = oldZ - maxForwardOffset;
    if (ndcDepth < allowedMinZ) {
        ndcDepth = allowedMinZ;
    }
    fragDepth = fragDepth;
}

#endif// COMMON_FUNCS_GLSL
