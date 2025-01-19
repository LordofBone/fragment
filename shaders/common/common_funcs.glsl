#ifndef COMMON_FUNCS_GLSL
#define COMMON_FUNCS_GLSL

// ---------------------------------------------------
// Global uniforms
// ---------------------------------------------------
uniform float textureLodLevel;

// Now we have a float controlling the ambient brightness.
uniform float ambientStrength;// 0.0 => no ambient, 1.0 => full ambient intensity

// ---------------------------------------------------
// Environment mapping uniforms
// ---------------------------------------------------
uniform samplerCube environmentMap;// A cubemap with MIP levels
uniform float environmentMapStrength;
uniform float envMapLodLevel;

// ---------------------------------------------------
// Parallax Occlusion Mapping (POM) uniforms
// ---------------------------------------------------
uniform float pomHeightScale;
uniform int pomMinSteps;
uniform int pomMaxSteps;
uniform sampler2D displacementMap;
uniform bool invertDisplacementMap;
uniform bool useCheckerPattern;

// ---------------------------------------------------
// Liquid simulation uniforms
// ---------------------------------------------------
uniform float time;
uniform float waveSpeed;
uniform float waveAmplitude;
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

///////////////////////////////////////////////////////////
// Example: Extended PBR material struct for .mtl data
///////////////////////////////////////////////////////////
struct Material {
// Basic old-school fields
    vec3 ambient;// e.g., from old Ka
    vec3 diffuse;// Kd
    vec3 specular;// Ks
    float shininess;// Ns

// "Core" PBR fields
    float roughness;// 'Pr' in Blender MTL (0.0–1.0 range typically)
    float metallic;// 'Pm' in Blender MTL (0.0–1.0 range typically)

// Additional MTL data (not fully used here but stored)
    float ior;// Ni (index of refraction), e.g. 1.45
    float transparency;// d (a typical alpha / dissolve)
    float clearcoat;// Pc
    float clearcoatRoughness;// Pcr
    float sheen;// Ps
    float anisotropy;// aniso
    float anisotropyRot;// anisor
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
float ShadowCalculationStandard(vec4 fragPosLightSpace, sampler2D shadowMap)
{
    vec3 projCoords= fragPosLightSpace.xyz/ fragPosLightSpace.w;
    projCoords= projCoords*0.5+ 0.5;

    if (projCoords.x<0.0|| projCoords.x>1.0||
    projCoords.y<0.0|| projCoords.y>1.0)
    {
        return 0.0;
    }

    float closestDepth= texture(shadowMap, projCoords.xy).r;
    float currentDepth= projCoords.z;
    float bias= 0.005;

    float shadow=0.0;
    vec2 texelSize= 1.0/ textureSize(shadowMap, 0);

    for (int x=-1;x<=1;x++)
    {
        for (int y=-1;y<=1;y++)
        {
            float pcfDepth= texture(shadowMap, projCoords.xy+ vec2(x, y)*texelSize).r;
            shadow += (currentDepth- bias> pcfDepth)? 1.0:0.0;
        }
    }
    shadow /=9.0;
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
// Compute Diffuse Lighting (standard version)
// ---------------------------------------------------
vec3 computeDiffuseLighting(vec3 N, vec3 V, vec3 fragPos, vec3 baseColor)
{
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; ++i)
    {
        vec3 lightDir = normalize(lightPositions[i] - fragPos);
        float diff = max(dot(N, lightDir), 0.0);
        diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];
    }

    // Old approach: reflect direction + separate environment pass
    vec3 reflectDir = reflect(-V, N);

    vec3 envColor = sampleEnvironmentMapLod(reflectDir).rgb;

    vec3 result = ambient + diffuse;

    result = mix(result, result + envColor, environmentMapStrength);

    return result;
}

// ---------------------------------------------------
// Compute Phong Lighting (standard version)
// ---------------------------------------------------
vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor)
{
    // Ambient from user-defined "ambientColor" * ambientStrength
    vec3 ambient  = computeAmbientColor(baseColor);
    vec3 diffuse  = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specularColor = vec3(1.0);

    for (int i = 0; i < 10; ++i)
    {
        vec3 lightDir = normalize(lightPositions[i] - fragPos);

        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];

        // Blinn-Phong
        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normal, halfwayDir), 0.0), 32.0);
        specular += spec * specularColor * lightColors[i] * lightStrengths[i];
    }

    // Old approach: reflect direction + separate environment pass
    vec3 reflectDir = reflect(-viewDir, normal);
    // We might use envMapLodLevel as a uniform for the old approach:
    //        vec3 envColor   = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
    vec3 envColor = sampleEnvironmentMapLod(reflectDir).rgb;

    vec3 result = ambient + diffuse + specular;

    // Then blend in that environment color additively
    // "mix(lighting, lighting + envColor, environmentMapStrength)"
    result = mix(result, result + envColor, environmentMapStrength);

    return result;
}

////////////////////////////////////////////////////////////////////////
// 1) PBR Helpers (GGX, Smith, Schlick)
////////////////////////////////////////////////////////////////////////
float DistributionGGX(vec3 N, vec3 H, float roughness)
{
    float a      = roughness * roughness;
    float a2     = a * a;
    float NdotH  = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float denom  = (NdotH2 * (a2 - 1.0) + 1.0);
    denom        = 3.14159265359 * denom * denom;
    return a2 / denom;
}

float GeometrySchlickGGX(float NdotV, float k)
{
    // k = (roughness + 1)^2 / 8 in many references
    return NdotV / (NdotV * (1.0 - k) + k);
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness)
{
    float r   = (roughness + 1.0);
    float k   = (r*r) / 8.0;// e.g. UE4 approach
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);

    float ggx1  = GeometrySchlickGGX(NdotV, k);
    float ggx2  = GeometrySchlickGGX(NdotL, k);
    return ggx1 * ggx2;
}

// Fresnel by Schlick's approximation
vec3 fresnelSchlick(float cosTheta, vec3 F0)
{
    return F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
}

// If you have a "metalness" approach, typically F0 is 0.04 for dielectrics,
// but for metals it's baseColor. This mixes the two:
vec3 computeF0(vec3 baseColor, float metallic)
{
    vec3 dielectricF0 = vec3(0.04);
    return mix(dielectricF0, baseColor, metallic);
}

////////////////////////////////////////////////////////////////////////
// 2) "computePBRLighting"
//
// This function merges local light contributions (point lights) with
// a simple specular environment reflection (cubemap).
// If you want diffuse IBL, you'd also sample an "irradiance map."
////////////////////////////////////////////////////////////////////////
const float PI = 3.14159265359;
const float MAX_MIPS = 5.0;// e.g. if your cubemap has 5 MIP levels

vec3 computePBRLighting(vec3 N, vec3 V, vec3 fragPos, vec3 baseColor)
{
    //--------------------------------------------------------
    // 1) Local Lighting (point lights)
    //--------------------------------------------------------
    // We'll accumulate combined color from all local lights
    vec3 localLighting = vec3(0.0);

    // Derive base F0 from metallic workflow
    vec3 F0 = computeF0(baseColor, material.metallic);

    for (int i = 0; i < 10; i++)
    {
        // 1.1) Light direction
        vec3 L     = normalize(lightPositions[i] - fragPos);
        vec3 H     = normalize(V + L);
        float NdotL= max(dot(N, L), 0.0);

        // 1.2) Cook–Torrance microfacet spec
        float D = DistributionGGX(N, H, material.roughness);
        float G = GeometrySmith(N, V, L, material.roughness);
        float NdotV = max(dot(N, V), 0.0);
        float HdotV = max(dot(H, V), 0.0);
        vec3  F     = fresnelSchlick(HdotV, F0);

        // 1.3) Combine spec
        float denom = 4.0 * NdotV * NdotL + 0.0001;
        vec3 specular  = (D * G * F) / denom;

        // 1.4) kS/kD split
        // kS is the fraction of specular reflection (F)
        vec3 kS = F;
        // kD is diffuse portion, scaled by (1 - metallic) so metals lose diffuse
        vec3 kD = (vec3(1.0) - kS) * (1.0 - material.metallic);

        // Lambertian diffuse (assuming baseColor is "albedo")
        vec3 diffuse = kD * baseColor / PI;

        // Final shading from this light
        // Multiply by the light color/strength
        vec3 lightContribution = (diffuse + specular) * lightColors[i]
        * lightStrengths[i] * NdotL;
        localLighting += lightContribution;
    }

    //--------------------------------------------------------
    // 2) Environment Reflection (specular IBL)
    //--------------------------------------------------------
    // We'll do a very simplified approach: reflect(N, V) with roughness-based MIP
    vec3 R = reflect(-V, N);
    // approximate MIP level for roughness
    float mipLevel = material.roughness * MAX_MIPS;
    // sample the environment map
    vec3 envSample = textureLod(environmentMap, R, mipLevel).rgb;

    // Fresnel for environment
    float NdotV = max(dot(N, V), 0.0);
    vec3 F_env  = fresnelSchlick(NdotV, F0);

    // If fully metallic => reflection is mostly baseColor
    vec3 kS_env = F_env;
    vec3 kD_env = (vec3(1.0) - kS_env) * (1.0 - material.metallic);

    // This example doesn't include a "diffuse irradiance map," so
    // we won't add a separate diffuse environment term.
    // If you had an "irradianceMap," you'd do something like:
    //   vec3 diffuseIbl = baseColor * irradianceColor;
    //   diffuseIbl *= (1.0 - metallic)...

    // We'll just do spec IBL for the example:
    vec3 envSpec  = envSample * kS_env;// approximate

    // Combine environment reflection with local lighting
    vec3 environmentContribution = envSpec * environmentMapStrength;

    // If you want some minimal ambient from your old pipeline,
    // you might do:
    //   vec3 combinedAmbient = computeAmbientColor(baseColor * material.ambient);

    //--------------------------------------------------------
    // 3) Return final color
    //--------------------------------------------------------
    return localLighting + environmentContribution;
}

// ---------------------------------------------------
// Particle-specific lighting with distance attenuation
// ---------------------------------------------------
vec3 computeParticlePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor, float shininess)
{
    // Ambient from user-defined "ambientColor" * ambientStrength
    vec3 ambient = computeAmbientColor(baseColor);

    vec3 diffuse = vec3(0.0);
    vec3 specular= vec3(0.0);

    for (int i = 0; i < 10; ++i)
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
        float spec= pow(specAngle, max(shininess, 0.0));
        specular += attenuation * spec * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeParticleDiffuseLighting(vec3 normal, vec3 fragPos, vec3 baseColor)
{
    // Ambient from user-defined "ambientColor" * ambientStrength
    vec3 ambient = computeAmbientColor(baseColor);

    vec3 diffuse= vec3(0.0);
    for (int i=0;i<10;i++)
    {
        vec3 lightVec= lightPositions[i] - fragPos;
        float distance= length(lightVec);
        vec3 lightDir= normalize(lightVec);

        float attenuation= 1.0 / (1.0 + 0.09*distance + 0.032*(distance*distance));

        float diff= max(dot(normal, lightDir), 0.0);
        diffuse += attenuation* lightColors[i]* diff* baseColor* lightStrengths[i];
    }

    return ambient+ diffuse;
}

//---------------- Procedural Displacement for POM -----------------
float proceduralDisplacement(vec2 coords)
{
    if (useCheckerPattern)
    {
        float cellCount=5.0;
        vec2 cellCoords= fract(coords* cellCount);
        float cellVal= (step(0.5, cellCoords.x)== step(0.5, cellCoords.y))?1.0:-1.0;
        return 0.5+ 0.5* cellVal* waveAmplitude;
    }
    else
    {
        float nf= smoothNoise(coords* randomness);
        float waveX= sin(coords.y*10.0+ time*waveSpeed+ nf* texCoordFrequency);
        float waveY= cos(coords.x*10.0+ time*waveSpeed+ nf* texCoordFrequency);
        float h= (waveX+ waveY)*0.5;
        // Increase contrast
        h= sign(h)* pow(abs(h), 2.0);
        return 0.5+ 0.5*h* waveAmplitude;
    }
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

#endif// COMMON_FUNCS_GLSL
