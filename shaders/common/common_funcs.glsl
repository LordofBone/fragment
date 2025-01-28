#ifndef COMMON_FUNCS_GLSL
#define COMMON_FUNCS_GLSL

// ---------------------------------------------------
// Global uniforms
// ---------------------------------------------------
uniform float textureLodLevel;

// Now we have a float controlling the ambient brightness.
uniform float ambientStrength;// 0.0 => no ambient, 1.0 => full ambient intensity

// Normal map
uniform sampler2D normalMap;

// ---------------------------------------------------
// Environment mapping uniforms
// ---------------------------------------------------
uniform samplerCube environmentMap;// A cubemap with MIP levels
uniform float environmentMapStrength;
uniform float envMapLodLevel;

// ---------------------------------------------------
// Screen-space texture mapping uniforms
// ---------------------------------------------------
uniform sampler2D screenTexture;

// ---------------------------------------------------
// Planar texture mapping uniforms
// ---------------------------------------------------
uniform bool usePlanarNormalDistortion;
uniform float distortionStrength;
uniform float refractionStrength;
uniform bool screenFacingPlanarTexture;
uniform float planarFragmentViewThreshold;

// ------------------------------------------------------
// Flip toggles
// ------------------------------------------------------
uniform bool flipPlanarHorizontal;// If true, flip horizontally
uniform bool flipPlanarVertical;// If true, flip vertically

// ---------------------------------------------------
// Parallax Occlusion Mapping (POM) uniforms
// ---------------------------------------------------
uniform float pomHeightScale;
uniform int pomMinSteps;
uniform int pomMaxSteps;
uniform sampler2D displacementMap;
uniform bool invertDisplacementMap;
uniform bool useCheckerPattern;
uniform float parallaxEyeOffsetScale;
uniform float parallaxMaxDepthClamp;
uniform float maxForwardOffset;// How far forward we allow the surface to move (in NDC)
uniform bool enableFragDepthAdjustment;

// ---------------------------------------------------
// Liquid simulation uniforms
// ---------------------------------------------------
uniform float time;
uniform float waveSpeed;
uniform float waveAmplitude;
uniform float waveDetail;
uniform float randomness;
uniform float texCoordFrequency;
uniform float texCoordAmplitude;

// ---------------------------------------------------
// Global uniform arrays for lights
// ---------------------------------------------------
uniform vec3 ambientColor;
uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];
uniform float lightOrthoLeft[10];
uniform float lightOrthoRight[10];
uniform float lightOrthoBottom[10];
uniform float lightOrthoTop[10];
uniform float legacy_roughness;
uniform float legacy_opacity;

///////////////////////////////////////////////////////////
// Extended PBR Material Struct for .mtl Data
///////////////////////////////////////////////////////////
struct Material {
// Basic old-school fields
    vec3 ambient;// from Ka
    vec3 diffuse;// from Kd
    vec3 specular;// from Ks
    float shininess;// from Ns
    vec3 emissive;// from Ke
    float fresnelExponent;// from Pfe (non-standard parameter)
    int illuminationModel;// from illum

// "Core" PBR fields
    float roughness;// 'Pr' in Blender MTL (0.0–1.0 range typically)
    float metallic;// 'Pm' in Blender MTL (0.0–1.0 range typically)

// Additional MTL data (not fully used here but stored)
    float ior;// Ni (index of refraction), e.g. 1.45
    float transparency;// d (a typical alpha/dissolve in MTL)
    float clearcoat;// Pc
    float clearcoatRoughness;// Pcr
    float sheen;// Ps
    float anisotropy;// aniso
    float anisotropyRot;// anisor
    vec3 transmission;// Tf
};

uniform Material material;

// ---------------------------------------------------
// Improved integer-based hash & rand
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
    // Returns [0..1]
    return float(hash(seed)) / 4294967295.0;
}

// ---------------------------------------------------
// Pseudo-random function for color variation
// ---------------------------------------------------
float generateRandomValue(vec2 uv, float id)
{
    return fract(sin(dot(uv + id, vec2(12.9898, 78.233))) * 43758.5453);
}

// ---------------------------------------------------
// Noise & Smooth Noise
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

/*******************************************************
 *  Fluid Forces (Explicit Parameters)
 *    velocity          : the particle’s current velocity
 *    adjustedGravity   : pass in if you want to base clamping on gravity’s magnitude
 *    fluidPressure     : how strong the "pressure" drag is
 *    fluidViscosity    : how strong the "viscous" drag is
 *    fluidForceMultiplier : used for computing max fluid force
 *******************************************************/
vec3 calculateFluidForces(
vec3 velocity,
vec3 adjustedGravity,
float fluidPressure,
float fluidViscosity,
float fluidForceMultiplier
)
{
    // 1) gravityNorm from the adjustedGravity
    float gravityNorm = length(adjustedGravity);

    // 2) computedMaxFluidForce
    float computedMaxFluidForce = gravityNorm * fluidForceMultiplier;

    // 3) Pressure ~ -velocity * fluidPressure
    vec3 pressureForce = -velocity * fluidPressure;

    // 4) Viscosity ~ -velocity * fluidViscosity
    vec3 viscosityForce = -velocity * fluidViscosity;

    vec3 totalFluidForce = pressureForce + viscosityForce;

    // 5) Clamp if above computedMaxFluidForce
    float forceMag = length(totalFluidForce);
    if (forceMag > computedMaxFluidForce && forceMag > 0.0)
    {
        totalFluidForce = normalize(totalFluidForce) * computedMaxFluidForce;
    }

    return totalFluidForce;
}

// ----------------------------------------------------------------------
// A simple "tent" (pyramid) filter for cubemaps
// Samples 4 nearby directions and does a weighted average
// 'dir' is your 3D direction for the cubemap
// 'offset' is how big of an angular offset you want
// ----------------------------------------------------------------------
vec4 sampleCubemapTent(samplerCube cubemap, vec3 dir, float offset)
{
    // The base color at the exact direction
    vec4 center = texture(cubemap, dir);

    // We'll pick 3 offsets in a triangular pattern around 'dir'.
    // In practice, you might pick 8 offsets for a more thorough filter.
    // Or do a small random distribution if you want a "soft" look.
    vec3 right = normalize(cross(dir, vec3(0.0, 1.0, 0.0)));
    vec3 up    = normalize(cross(right, dir));

    // Sample directions
    vec3 dir1 = normalize(dir + offset * right);
    vec3 dir2 = normalize(dir - offset * right);
    vec3 dir3 = normalize(dir + offset * up);

    // Grab the colors
    vec4 col1 = texture(cubemap, dir1);
    vec4 col2 = texture(cubemap, dir2);
    vec4 col3 = texture(cubemap, dir3);

    // Weighted average: center has a higher weight
    return (center * 0.4 + col1 * 0.2 + col2 * 0.2 + col3 * 0.2);
}

//////////////////////////////////////////////////////
// Bicubic helpers
//////////////////////////////////////////////////////

float catmullRom1D(float x)
{
    x = abs(x);
    float x2 = x*x;
    float x3 = x*x2;

    if (x <= 1.0) {
        // 1.5x^3 - 2.5x^2 + 1.0
        return 1.5*x3 - 2.5*x2 + 1.0;
    }
    else if (x < 2.0) {
        // -0.5x^3 + 2.5x^2 - 4x + 2
        return -0.5*x3 + 2.5*x2 - 4.0*x + 2.0;
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
    vec3 up   = normalize(cross(side, fwd));

    vec4 accumColor = vec4(0.0);
    float accumWeight = 0.0;

    // 4x4
    for (int i = 0; i < 4; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            float offU = float(i) - 1.5;
            float offV = float(j) - 1.5;
            float w = bicubicWeight2D(offU, offV);

            vec3 sampleDir = fwd + (offU * baseOffset)*side + (offV * baseOffset)*up;
            sampleDir = normalize(sampleDir);

            vec4 c = texture(cubemap, sampleDir);

            accumColor  += c * w;
            accumWeight += w;
        }
    }

    if (accumWeight > 0.0)
    return accumColor / accumWeight;
    else
    return texture(cubemap, dir);
}

//////////////////////////////////////////////////////
// Lanczos helpers
//////////////////////////////////////////////////////

float lanczos1D(float x, float lobes)
{
    x = abs(x);
    if (x < 1e-5)
        return 1.0;
    if (x > lobes)
        return 0.0;
    float pi_x = 3.14159265359 * x;
    float pi_xL= pi_x / lobes;
    return (sin(pi_x)/(pi_x)) * (sin(pi_xL)/(pi_xL));
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
    vec3 tempUp = (abs(fwd.y)<0.99)? vec3(0, 1, 0): vec3(1, 0, 0);
    vec3 side   = normalize(cross(fwd, tempUp));
    vec3 up     = normalize(cross(side, fwd));

    vec4 accumColor= vec4(0.0);
    float accumWeight=0.0;

    float minRange= -float(sampleRadius);
    float maxRange=  float(sampleRadius)+0.001;

    for (float i=minRange; i<=maxRange; i+= stepSize)
    {
        for (float j=minRange; j<=maxRange; j+= stepSize)
        {
            float w= lanczos2D(i, j, lobes);
            vec3 sampleDir= fwd+ (i*baseOffset)*side+ (j*baseOffset)*up;
            sampleDir= normalize(sampleDir);

            vec4 c= texture(cubemap, sampleDir);

            accumColor+= c*w;
            accumWeight+= w;
        }
    }

    if (accumWeight>0.0)
    return accumColor/ accumWeight;
    else
    return texture(cubemap, dir);
}

vec4 sampleEnvironmentMap(vec3 envMapTexCoords)
{
    return texture(environmentMap, envMapTexCoords);
}

vec4 sampleEnvironmentMapLod(vec3 envMapTexCoords)
{
    return textureLod(environmentMap, envMapTexCoords, envMapLodLevel);
}

// ---------------------------------------------------
// Tone Mapping (Uncharted2)
// ---------------------------------------------------
vec3 Uncharted2Tonemap(vec3 x)
{
    float A=0.15;
    float B=0.50;
    float C=0.10;
    float D=0.20;
    float E=0.02;
    float F=0.30;
    return ((x*(A*x + C*B)+ D*E)/
    (x*(A*x + B)+ D*F))- E/F;
}

vec3 toneMapping(vec3 color)
{
    vec3 curr = Uncharted2Tonemap(color*2.0);
    vec3 whiteScale = 1.0/Uncharted2Tonemap(vec3(11.2));
    return curr* whiteScale;
}

// ---------------------------------------------------
// Standard PCF Shadow Calculation (no displacement)
// ---------------------------------------------------
float ShadowCalculationStandard(
vec4 fragPosLightSpace,
sampler2D shadowMap
) {
    float shadow = 0.0;

    for (int i = 0; i < 10; ++i) {
        // Transform the fragment position into light space
        vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
        projCoords = projCoords * 0.5 + 0.5;

        // Check if the fragment is within the orthogonal bounds of the current light
        float withinBounds =
        step(lightOrthoLeft[i], projCoords.x) *
        step(projCoords.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], projCoords.y) *
        step(projCoords.y, lightOrthoTop[i]) *
        step(0.0, projCoords.z) *
        step(projCoords.z, 1.0);

        if (withinBounds > 0.0) {
            // Retrieve the closest depth from the shadow map
            float closestDepth = texture(shadowMap, projCoords.xy).r;
            float currentDepth = projCoords.z;

            // Bias to reduce shadow acne
            float bias = 0.005;

            // Perform Percentage Closer Filtering (PCF)
            vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
            float lightShadow = 0.0;

            for (int x = -1; x <= 1; ++x) {
                for (int y = -1; y <= 1; ++y) {
                    float pcfDepth = texture(
                    shadowMap, projCoords.xy + vec2(x, y) * texelSize
                    ).r;
                    lightShadow += (currentDepth - bias > pcfDepth) ? 1.0 : 0.0;
                }
            }
            lightShadow /= 9.0;

            // Accumulate shadow influence for the current light
            shadow += lightShadow * lightStrengths[i];
        }
    }

    // Normalize the shadow by the number of active lights
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
    vec3 displacedPos= fragPosWorld;
    displacedPos.y+= waveHeight;

    vec4 fragPosLightSpace= lightSpaceMatrix* model* vec4(displacedPos, 1.0);
    vec3 projCoords= fragPosLightSpace.xyz/ fragPosLightSpace.w;
    projCoords= projCoords*0.5+0.5;

    if (projCoords.x<0.0|| projCoords.x>1.0||
    projCoords.y<0.0|| projCoords.y>1.0||
    projCoords.z<0.0|| projCoords.z>1.0)
    {
        return 0.0;
    }

    float closestDepth= texture(shadowMap, projCoords.xy).r;
    float currentDepth= projCoords.z;
    float bias= max(biasFactor* (1.0- dot(normal, normalize(lightPos- displacedPos))), minBias);

    float shadow=0.0;
    vec2 texelSize=1.0/ textureSize(shadowMap, 0);
    int samples=3;
    for (int x=-samples;x<=samples;x++)
    {
        for (int y=-samples;y<=samples;y++)
        {
            float pcfDepth= texture(shadowMap, projCoords.xy+ vec2(x, y)*texelSize).r;
            float comparison= currentDepth- bias- pcfDepth;
            shadow+= smoothstep(0.0, 0.005, comparison);
        }
    }
    shadow/= float((samples*2+1)*(samples*2+1));

    // Attenuate by surface depth
    shadow*= exp(-surfaceDepth*0.1)* shadowStrength;
    shadow= clamp(shadow, 0.0, 1.0);
    return shadow;
}

// ---------------------------------------------------
// Basic Ambient + Strength
// ---------------------------------------------------
vec3 computeAmbientColor(vec3 baseColor)
{
    // Multiply the base color by the global ambientColor uniform
    // and scale by ambientStrength
    return baseColor * ambientColor * ambientStrength;
}

// ---------------------------------------------------
// Compute Diffuse Lighting with opacity
// ---------------------------------------------------
vec3 computeDiffuseLighting(
vec3 normal,
vec3 viewDir,
vec3 fragPos,
vec3 baseColor,
vec2 texCoords
) {
    // 1) Ambient (using your global ambientColor * ambientStrength)
    vec3 ambient  = computeAmbientColor(baseColor);

    // 2) Accumulate diffuse from up to 10 lights, with bounding checks
    vec3 diffuse  = vec3(0.0);

    for (int i = 0; i < 10; ++i)
    {
        vec3 lightDir = normalize(lightPositions[i] - fragPos);

        // Determine if the fragment is within the light's ortho bounds
        float withinBounds =
        step(lightOrthoLeft[i], fragPos.x) *
        step(fragPos.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], fragPos.y) *
        step(fragPos.y, lightOrthoTop[i]);

        if (withinBounds > 0.0)
        {
            vec3 lightDir = normalize(lightPositions[i] - fragPos);
            // Lambertian diffuse
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];
        }
    }

    // 3) Combine the local lighting
    vec3 result = ambient + diffuse;

    // 4) Environment reflection (legacy approach)
    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 envColor   = sampleEnvironmentMapLod(reflectDir).rgb;// user-defined sampler

    // 5) Roughness factor? if we want a "legacy_roughness" uniform
    //    We'll do a simple "roughnessFactor" => less reflection if high roughness
    float roughnessFactor = clamp(1.0 - (legacy_roughness / 100.0), 0.0, 1.0);

    // 6) Blend environment reflection inversely based on roughness
    result = mix(result, result + envColor, environmentMapStrength * roughnessFactor);

    // -----------------------------------------------------------------------
    // 7) Screen Texture transparency part:  we build a background color
    // -----------------------------------------------------------------------
    vec2 finalScreenCoords = texCoords;

    // 7a) Flip if requested
    if (flipPlanarHorizontal)
    {
        finalScreenCoords.x = 1.0 - finalScreenCoords.x;
    }
    if (flipPlanarVertical)
    {
        finalScreenCoords.y = 1.0 - finalScreenCoords.y;
    }

    // 7b) Normal-based distortion if usePlanarNormalDistortion
    if (usePlanarNormalDistortion)
    {
        // Re-sample normal map in tangent space to get RG
        vec2 nrg = texture(normalMap, texCoords, textureLodLevel).rg * 2.0 - 1.0;
        finalScreenCoords += (nrg * distortionStrength);
    }

    // 7c) Screen-facing check
    float facing = dot(normal, viewDir);
    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 backgroundColor = fallbackColor;

    if (screenFacingPlanarTexture)
    {
        if (facing > planarFragmentViewThreshold)
        {
            finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
            backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
        }
    }
    else
    {
        finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
        backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
    }

    // If background is near black => fallback
    if (length(backgroundColor) < 0.05)
    {
        backgroundColor = fallbackColor;
    }

    // 7d) legacy_opacity => how much "lighting" vs. "backgroundColor"
    // If legacy_opacity==1 => fully the object, 0 => fully background
    vec3 finalOut = mix(backgroundColor, result, legacy_opacity);

    // Return
    return finalOut;
}

// ---------------------------------------------------
// Compute Phong Lighting with opacity
// ---------------------------------------------------
vec3 computePhongLighting(
vec3 normal,
vec3 viewDir,
vec3 fragPos,
vec3 baseColor,
vec2 texCoords
) {
    // 1) Ambient
    vec3 ambient  = computeAmbientColor(baseColor);
    vec3 diffuse  = vec3(0.0);
    vec3 specular = vec3(0.0);

    // White spec color
    vec3 specularColor = vec3(1.0);

    // 2) Up to 10 lights with bounding checks
    for (int i = 0; i < 10; ++i)
    {
        vec3 lightDir = normalize(lightPositions[i] - fragPos);

        // Determine if the fragment is within the light's ortho bounds
        float withinBounds =
        step(lightOrthoLeft[i], fragPos.x) *
        step(fragPos.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], fragPos.y) *
        step(fragPos.y, lightOrthoTop[i]);

        if (withinBounds > 0.0)
        {
            vec3 lightDir = normalize(lightPositions[i] - fragPos);

            // Diffuse
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];

            // Blinn–Phong spec with user-defined roughness
            vec3 halfwayDir = normalize(lightDir + viewDir);
            float spec = pow(max(dot(normal, halfwayDir), 0.0), legacy_roughness);
            specular += spec * specularColor * lightColors[i] * lightStrengths[i];
        }
    }

    // 3) Combine local lighting
    vec3 result = ambient + diffuse + specular;

    // 4) Environment reflection
    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 envColor   = sampleEnvironmentMapLod(reflectDir).rgb;// user-defined call

    // Possibly scale by environmentMapStrength
    result = mix(result, result + envColor, environmentMapStrength);

    // -----------------------------------------------------------------------
    // 5) Screen Texture transparency part
    // -----------------------------------------------------------------------
    vec2 finalScreenCoords = texCoords;

    // a) Flip if needed
    if (flipPlanarHorizontal)
    {
        finalScreenCoords.x = 1.0 - finalScreenCoords.x;
    }
    if (flipPlanarVertical)
    {
        finalScreenCoords.y = 1.0 - finalScreenCoords.y;
    }

    // b) Normal-based distortion
    if (usePlanarNormalDistortion)
    {
        vec2 nrg = texture(normalMap, texCoords, textureLodLevel).rg * 2.0 - 1.0;
        finalScreenCoords += (nrg * distortionStrength);
    }

    // c) Screen-facing check
    float facing = dot(normal, viewDir);
    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 backgroundColor = fallbackColor;

    if (screenFacingPlanarTexture)
    {
        if (facing > planarFragmentViewThreshold)
        {
            finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
            backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
        }
    }
    else
    {
        finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
        backgroundColor = texture(screenTexture, finalScreenCoords).rgb;
    }

    if (length(backgroundColor) < 0.05)
    {
        backgroundColor = fallbackColor;
    }

    // d) Mix based on legacy_opacity
    vec3 finalOut = mix(backgroundColor, result, legacy_opacity);

    return finalOut;
}

////////////////////////////////////////////////////////////////////////
// 1) Common PBR Helpers (GGX, Smith, Schlick)
////////////////////////////////////////////////////////////////////////
/*
(1) DistributionGGX:
    - Computes the microfacet normal distribution (GGX).
    - 'roughness' controls how wide the lobe is.
*/
float DistributionGGX(vec3 N, vec3 H, float roughness)
{
    float a  = roughness * roughness;
    float a2 = a * a;
    float NdotH  = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = 3.14159265359 * denom * denom;
    return a2 / denom;
}

/*
(2) GeometrySchlickGGX:
    - Approximates geometric shadowing/masking with a k factor.
    - Typically k = (roughness+1)^2 / 8.
*/
float GeometrySchlickGGX(float NdotV, float k)
{
    return NdotV / (NdotV * (1.0 - k) + k);
}

/*
(3) GeometrySmith:
    - Combines geometry terms for view & light directions using above function.
*/
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

/*
(4) FresnelSchlick:
    - Approximates Fresnel effect via Schlick's formula.
    - 'cosTheta' is typically dot(H, V) or dot(N, V).
*/
vec3 fresnelSchlick(float cosTheta, vec3 F0)
{
    return F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
}

// A variant of fresnelSchlick that applies an extra exponent to tweak the ramp:
vec3 fresnelSchlickExponent(float cosTheta, vec3 F0, float exponent)
{
    // Standard Schlick
    vec3 base = F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);

    // Then raise it to an exponent to intensify or soften the ramp
    // e.g., exponent > 1 => reflection intensifies near edges
    //       exponent < 1 => reflection is more uniform
    return pow(base, vec3(exponent));
}

////////////////////////////////////////////////////////////////////////
// 2) Additional Helpers
////////////////////////////////////////////////////////////////////////
/*
(5) combineRoughnessAndShininess:
    - Because old .mtl 'Ns' (shininess) conflicts with modern 'roughness',
      we do a simple hack to combine them. Higher 'shininess' => lower roughness.
*/
float combineRoughnessAndShininess(float baseRoughness, float shininess)
{
    float shininessFactor = clamp(shininess / 128.0, 0.0, 1.0);
    float result = baseRoughness * (1.0 - 0.8 * shininessFactor);
    return clamp(result, 0.0, 1.0);
}

/*
(6) computeF0FromIOR:
    - For dielectrics, F0 is roughly ((ior - 1)/(ior + 1))^2 at normal incidence.
*/
vec3 computeF0FromIOR(float ior)
{
    float r0 = (ior - 1.0) / (ior + 1.0);
    r0 *= r0;
    return vec3(r0);
}

/*
(7) computeF0Combined:
    - Mixes the dielectric F0 with baseColor if metallic=1, then merges with old .mtl 'specular'.
*/
vec3 computeF0Combined(vec3 baseColor, float metallic, vec3 specular, float ior)
{
    vec3 dielectricF0 = computeF0FromIOR(ior);
    // If metallic is 1.0 => baseColor for reflection; if 0 => dielectricF0
    vec3 baseF0 = mix(dielectricF0, baseColor, metallic);

    // Old .mtl 'specular' might override or raise F0
    baseF0 = max(baseF0, specular);
    return baseF0;
}

////////////////////////////////////////////////////////////////////////
// 3) "computePBRLighting" with extended MTL, environment reflection (Cook–Torrance IBL),
//    clearcoat, sheen, and a naive refraction/transmission pass
////////////////////////////////////////////////////////////////////////
/*
Steps:
(1) Combine roughness & shininess => effectiveRoughness.
(2) Local Cook–Torrance for point lights.
(3) Environment Reflection (Cook–Torrance IBL).
(4) Clearcoat
(5) Sheen
(6) Emissive
(7) Ambient
(8) (Optional) Extra reflection if you want to unify older approach
(9) Transmission => partial refraction
*/

const float PI = 3.14159265359;
const float MAX_MIPS = 5.0;// for environment map MIP

vec3 computePBRLighting(
vec3 N,
vec3 V,
vec3 fragPos,
vec3 baseColor,
vec2 texCoords// For normal-based distortion if desired
){
    //----------------------------------------------
    // (1) Combine roughness + shininess
    //----------------------------------------------
    float effectiveRoughness = combineRoughnessAndShininess(material.roughness, material.shininess);

    //----------------------------------------------
    // (2) Local Cook–Torrance from point lights
    //----------------------------------------------
    vec3 localLighting = vec3(0.0);

    // F0: base reflectance from IOR + metallic + specular
    vec3 F0 = computeF0Combined(
    baseColor,
    material.metallic,
    material.specular,
    material.ior
    );

    for (int i = 0; i < 10; i++)
    {
        float withinBounds =
        step(lightOrthoLeft[i], fragPos.x) *
        step(fragPos.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], fragPos.y) *
        step(fragPos.y, lightOrthoTop[i]);

        if (withinBounds > 0.0)
        {
            vec3 L = normalize(lightPositions[i] - fragPos);
            vec3 H = normalize(V + L);
            float NdotL = max(dot(N, L), 0.0);

            float D = DistributionGGX(N, H, effectiveRoughness);
            float G = GeometrySmith(N, V, L, effectiveRoughness);
            float NdotV = max(dot(N, V), 0.0);
            float HdotV = max(dot(H, V), 0.0);
            vec3 F  = fresnelSchlick(HdotV, F0);

            float denom = 4.0 * NdotV * NdotL + 0.0001;
            vec3 specular = (D * G * F) / denom;

            // kS = F; kD = (1 - F)*(1 - metallic)
            vec3 kS = F;
            vec3 kD = (vec3(1.0) - kS) * (1.0 - material.metallic);

            // Lambertian diffuse
            vec3 diffuse = kD * baseColor;

            localLighting += (diffuse + specular)
            * lightColors[i] * lightStrengths[i]
            * NdotL;
        }
    }

    //----------------------------------------------
    // (3) Environment Reflection (Cook–Torrance IBL)
    //----------------------------------------------
    // We'll do a simplified version: we sample environmentMap using reflectDir,
    // do a roughness-based MIP, and combine with a Fresnel factor based on NdotV.

    float NdotV = max(dot(N, V), 0.0);
    // reflectDir
    vec3 reflectDir = reflect(-V, N);
    // MIP based on effectiveRoughness
    float mipLevel = effectiveRoughness * MAX_MIPS;
    vec3 envSample = textureLod(environmentMap, reflectDir, mipLevel).rgb;

    // Fresnel for environment (with exponent tweak)
    float exponent = material.fresnelExponent;// e.g. default 1.0 if not set
    vec3 F_env = fresnelSchlickExponent(NdotV, F0, exponent);

    // Approx geometry term or just 1.0
    float G_approx = 1.0;
    vec3 environmentSpec = envSample * F_env * G_approx;

    // Scale by environmentMapStrength * (1.0 - effectiveRoughness)
    // so rough surfaces show less reflection
    float reflectionFactor = environmentMapStrength * clamp(1.0 - effectiveRoughness, 0.0, 1.0);

    // Combine environment reflection with local lighting
    vec3 environmentContribution = environmentSpec * reflectionFactor;

    //----------------------------------------------
    // (4) Clearcoat
    //----------------------------------------------
    vec3 clearcoatContrib = vec3(0.0);
    if (material.clearcoat > 0.001)
    {
        float ccRough = clamp(material.clearcoatRoughness, 0.0, 1.0);
        vec3 H_cc = normalize(V + reflect(-V, N));

        float NdotV_cc = max(dot(N, V), 0.0);
        float D_cc = DistributionGGX(N, H_cc, ccRough);
        float G_cc = GeometrySmith(N, V, -V, ccRough);
        vec3 F0_cc = vec3(0.25);
        vec3 F_cc  = fresnelSchlick(NdotV_cc, F0_cc);

        float denom_cc = 4.0 * NdotV_cc * NdotV_cc + 0.0001;
        vec3 spec_cc = (D_cc * G_cc * F_cc) / denom_cc;
        spec_cc *= material.clearcoat;

        clearcoatContrib = spec_cc * environmentMapStrength;
    }

    //----------------------------------------------
    // (5) Sheen
    //----------------------------------------------
    vec3 sheenContrib = vec3(0.0);
    if (material.sheen > 0.001)
    {
        float edgeFactor = pow(1.0 - NdotV, 5.0);
        vec3 sheenColor  = mix(baseColor, vec3(1.0), 0.5);
        sheenContrib = sheenColor * edgeFactor * material.sheen;
    }

    //----------------------------------------------
    // (6) Combine local + environment => finalColor
    //----------------------------------------------
    vec3 finalColor = localLighting + environmentContribution + clearcoatContrib + sheenContrib;

    // Emissive
    finalColor += material.emissive;

    // (7) Ambient (old-school approach)
    vec3 ambientTerm = computeAmbientColor(finalColor);
    finalColor += ambientTerm;

    //----------------------------------------------
    // (8) Transmission => 2D-based "refraction"
    //----------------------------------------------
    float averageTf = (material.transmission.r + material.transmission.g + material.transmission.b) / 3.0;
    if (averageTf > 0.001)
    {
        // We'll store final UVs in `finalScreenCoords`
        vec2 finalScreenCoords = texCoords;

        // 1) If usePlanarNormalDistortion => do a small refraction offset
        if (usePlanarNormalDistortion)
        {
            // "air -> object," ratio ~ 1.0 / ior
            float refractionRatio = 1.0 / material.ior;
            // Refract direction in [-1..1]
            vec3 refractDir = refract(-V, N, refractionRatio);

            // Convert from [-1..1] to [-0.5..+0.5]
            vec2 refOffset = refractDir.xy * 0.5;

            // Add that offset to base texCoords.
            // 'refractionStrength' determines how strongly we shift the UV.
            finalScreenCoords += (refOffset * refractionStrength);
        }

        // 2) Flip if requested
        if (flipPlanarHorizontal)
        {
            finalScreenCoords.x = 1.0 - finalScreenCoords.x;
        }
        if (flipPlanarVertical)
        {
            finalScreenCoords.y = 1.0 - finalScreenCoords.y;
        }

        // 3) Normal-based distortion
        if (usePlanarNormalDistortion)
        {
            // Sample the normal map's RG channels at 'texCoords'
            vec2 nrg = texture(normalMap, texCoords).rg * 2.0 - 1.0;
            finalScreenCoords += (nrg * distortionStrength);
        }

        // 4) "screenFacingPlanarTexture" logic
        float facing = dot(N, V);
        vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
        vec3 refr2D;

        if (screenFacingPlanarTexture)
        {
            // Only sample if fragment faces camera above threshold
            if (facing > planarFragmentViewThreshold)
            {
                // clamp coords to [0,1]
                finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
                refr2D = texture(screenTexture, finalScreenCoords).rgb;
            }
            else
            {
                // If not facing, use fallback
                refr2D = fallbackColor;
            }
        }
        else
        {
            // always sample
            finalScreenCoords = clamp(finalScreenCoords, 0.0, 1.0);
            refr2D = texture(screenTexture, finalScreenCoords).rgb;
        }

        // 5) If near black => fallback
        if (length(refr2D) < 0.05)
        {
            refr2D = fallbackColor;
        }

        // 6) Multiply by the transmission color => tint
        refr2D *= material.transmission;

        // 7) Blend with finalColor
        finalColor = mix(finalColor, refr2D, averageTf);
    }

    // Return final color (alpha is handled in main if needed)
    return finalColor;
}

// ---------------------------------------------------
// Particle-specific diffuse with distance attenuation
// ---------------------------------------------------
vec3 computeParticleDiffuseLighting(vec3 normal, vec3 fragPos, vec3 baseColor)
{
    // Ambient from user-defined "ambientColor" * ambientStrength
    vec3 ambient = computeAmbientColor(baseColor);

    vec3 diffuse= vec3(0.0);
    for (int i=0;i<10;i++)
    {
        // Determine if the fragment is within the light's ortho bounds
        float withinBounds =
        step(lightOrthoLeft[i], fragPos.x) *
        step(fragPos.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], fragPos.y) *
        step(fragPos.y, lightOrthoTop[i]);

        if (withinBounds > 0.0)
        {
            vec3 lightVec= lightPositions[i] - fragPos;
            float distance= length(lightVec);
            vec3 lightDir= normalize(lightVec);

            float attenuation= 1.0 / (1.0 + 0.09*distance + 0.032*(distance*distance));

            float diff= max(dot(normal, lightDir), 0.0);
            diffuse += attenuation* lightColors[i]* diff* baseColor* lightStrengths[i];
        }
    }

    return ambient+ diffuse;
}

// ---------------------------------------------------
// Particle-specific phong with distance attenuation
// ---------------------------------------------------
vec3 computeParticlePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor)
{
    // Ambient from user-defined "ambientColor" * ambientStrength
    vec3 ambient = computeAmbientColor(baseColor);

    vec3 diffuse = vec3(0.0);
    vec3 specular= vec3(0.0);

    for (int i = 0; i < 10; ++i)
    {
        // Determine if the fragment is within the light's ortho bounds
        float withinBounds =
        step(lightOrthoLeft[i], fragPos.x) *
        step(fragPos.x, lightOrthoRight[i]) *
        step(lightOrthoBottom[i], fragPos.y) *
        step(fragPos.y, lightOrthoTop[i]);

        if (withinBounds > 0.0)
        {
            // Distance-based attenuation
            vec3 lightVec = lightPositions[i] - fragPos;
            float distance= length(lightVec);
            vec3 lightDir = normalize(lightVec);

            float attenuation= 1.0/(1.0+ 0.09*distance + 0.032*(distance*distance));

            // Diffuse shading
            float diff = max(dot(normal, lightDir), 0.0);
            diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];

            // Blinn-Phong spec
            vec3 halfwayDir= normalize(lightDir + viewDir);
            float specAngle= max(dot(normal, halfwayDir), 0.0);
            float spec= pow(specAngle, max(legacy_roughness, 0.0));
            specular += attenuation * spec * lightColors[i] * lightStrengths[i];
        }
    }

    return ambient + diffuse + specular;
}

// ---------------------------------------------------
// Wave output helper function
// ---------------------------------------------------
struct WaveOutput {
    vec2  waveTexCoords;// The offset coords
    float waveHeightX;
    float waveHeightY;
    float waveVal;// final waveVal or any combined value
};

// ---------------------------------------------------
// Compute Wave for Procedural Displacement
// ---------------------------------------------------
WaveOutput computeWave(vec2 baseTexCoords)
{
    WaveOutput wo;

    // 1) Start with coords
    vec2 waveTexCoords = baseTexCoords;

    // 2) Noise factor
    float noiseFactor = smoothNoise(waveTexCoords * randomness);

    // 3) Offsets
    waveTexCoords.x += sin(time * waveSpeed + baseTexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + baseTexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    wo.waveTexCoords = waveTexCoords;

    // 4) waveHeightX/Y
    float waveHeightX = sin(waveTexCoords.y * waveDetail);
    float waveHeightY = cos(waveTexCoords.x * waveDetail);
    wo.waveHeightX    = waveHeightX;
    wo.waveHeightY    = waveHeightY;

    // 5) Combined waveVal
    float waveVal = 0.5 * (waveHeightX + waveHeightY);
    waveVal *= waveAmplitude;
    wo.waveVal = waveVal;

    return wo;
}

// ---------------------------------------------------
// Procedural Displacement for POM
// ---------------------------------------------------
float proceduralDisplacement(vec2 coords)
{
    WaveOutput wo = computeWave(coords);

    // waveVal in wo.waveVal is ~[-waveAmplitude..+waveAmplitude]
    // map it into [0..1]
    float finalH = 0.5 + 0.5 * wo.waveVal;
    finalH = clamp(finalH, 0.0, 1.0);

    return finalH;
}

// ---------------------------------------------------
// Parallax Occlusion Mapping
// ---------------------------------------------------
vec2 ParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset)
{
    float numLayers= mix(float(pomMaxSteps), float(pomMinSteps), abs(viewDir.z));
    float layerDepth= 1.0/ numLayers;
    float currentLayerDepth=0.0;
    vec2 P= viewDir.xy* pomHeightScale;
    vec2 deltaTexCoords= P/ numLayers;

    vec2 currentTexCoords= texCoords;
    float currentDepthMapValue= texture(displacementMap, currentTexCoords, textureLodLevel).r;
    if (invertDisplacementMap)
    {
        currentDepthMapValue= 1.0- currentDepthMapValue;
    }

    float depthFromTexture= currentDepthMapValue;

    while (currentLayerDepth< depthFromTexture)
    {
        currentTexCoords-= deltaTexCoords;
        currentDepthMapValue= texture(displacementMap, currentTexCoords, textureLodLevel).r;
        if (invertDisplacementMap)
        {
            currentDepthMapValue= 1.0- currentDepthMapValue;
        }
        depthFromTexture= currentDepthMapValue;
        currentLayerDepth+= layerDepth;
    }

    vec2 prevTexCoords= currentTexCoords+ deltaTexCoords;
    float prevLayerDepth= currentLayerDepth- layerDepth;
    float prevDepthFromTexture= texture(displacementMap, prevTexCoords, textureLodLevel).r;
    if (invertDisplacementMap)
    {
        prevDepthFromTexture= 1.0- prevDepthFromTexture;
    }

    float weight= (depthFromTexture- currentLayerDepth)/
    ((depthFromTexture- currentLayerDepth)- (prevDepthFromTexture- prevLayerDepth));
    vec2 finalTexCoords= mix(currentTexCoords, prevTexCoords, weight);

    depthOffset= pomHeightScale*(1.0- mix(currentLayerDepth, prevLayerDepth, weight))* 0.0001;
    return finalTexCoords;
}

// ---------------------------------------------------
// Procedural Parallax Occlusion Mapping
// ---------------------------------------------------
vec2 ProceduralParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset)
{
    float numLayers= mix(float(pomMaxSteps), float(pomMinSteps), abs(viewDir.z));
    float layerDepth= 1.0/ numLayers;
    float currentLayerDepth=0.0;

    vec2 P= viewDir.xy* pomHeightScale;
    vec2 deltaTexCoords= P/ numLayers;

    vec2 currentTexCoords= texCoords;
    float currentDepth= proceduralDisplacement(currentTexCoords);
    if (invertDisplacementMap) currentDepth= 1.0- currentDepth;
    float depthFromTexture= currentDepth;

    while (currentLayerDepth< depthFromTexture)
    {
        currentTexCoords-= deltaTexCoords;
        currentDepth= proceduralDisplacement(currentTexCoords);
        if (invertDisplacementMap) currentDepth=1.0- currentDepth;
        depthFromTexture= currentDepth;
        currentLayerDepth+= layerDepth;
    }

    vec2 prevTexCoords= currentTexCoords+ deltaTexCoords;
    float prevLayerDepth= currentLayerDepth- layerDepth;
    float prevDepth= proceduralDisplacement(prevTexCoords);
    if (invertDisplacementMap) prevDepth= 1.0- prevDepth;

    float weight= (depthFromTexture- currentLayerDepth)/
    ((depthFromTexture- currentLayerDepth)-(prevDepth- prevLayerDepth));
    vec2 finalTexCoords= mix(currentTexCoords, prevTexCoords, weight);

    depthOffset= pomHeightScale*(1.0- mix(currentLayerDepth, prevLayerDepth, weight))* 0.0001;
    return finalTexCoords;
}

// ---------------------------------------------------
// Adjust FragDepth with Optional Clamping
// ---------------------------------------------------
void adjustFragDepth(
vec4 viewPos,
mat4 projectionMatrix,
vec4 fragPosWorld,
vec3 TBN[3],
float depthOffset,
inout float fragDepth
) {
    // Reconstruct eye position
    vec4 eyePos = viewPos;

    // Offset in tangent space
    vec3 offsetTangent = vec3(0.0, 0.0, -depthOffset);
    vec3 offsetWorld = mat3(TBN[0], TBN[1], TBN[2]) * offsetTangent;
    vec4 offsetEye = vec4(offsetWorld, 0.0);

    // New eye position with offset
    vec4 newEyePos = eyePos + offsetEye;

    // Reproject to clip space
    vec4 clipPos = projectionMatrix * newEyePos;
    float ndcDepth = clipPos.z / clipPos.w;

    // Clamp the depth to avoid excessive forward shifts
    ndcDepth = clamp(ndcDepth, 0.0, parallaxMaxDepthClamp);

    // Optional forward clamping
    float oldZ = fragDepth;
    float allowedMinZ = oldZ - maxForwardOffset;
    if (ndcDepth < allowedMinZ) {
        ndcDepth = allowedMinZ;
    }

    fragDepth = fragDepth;
}

#endif// COMMON_FUNCS_GLSL