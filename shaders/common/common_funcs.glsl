#ifndef COMMON_FUNCS_GLSL
#define COMMON_FUNCS_GLSL

// ---------------------------------------------------
// Global uniforms
// ---------------------------------------------------
uniform float textureLodLevel;

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
 *    fluidPressure  : how strong the "pressure" drag is
 *    fluidViscosity : how strong the "viscous" drag is
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
    vec3 right    = normalize(cross(dir, vec3(0.0, 1.0, 0.0)));
    vec3 up       = normalize(cross(right, dir));

    // Sample directions
    vec3 dir1 = normalize(dir + offset * right);
    vec3 dir2 = normalize(dir - offset * right);
    vec3 dir3 = normalize(dir + offset * up);

    // Grab the colors
    vec4 col1 = texture(cubemap, dir1);
    vec4 col2 = texture(cubemap, dir2);
    vec4 col3 = texture(cubemap, dir3);

    // Weighted average: center has a higher weight
    // so that we don't blur too heavily
    return (center * 0.4 + col1 * 0.2 + col2 * 0.2 + col3 * 0.2);
}

//////////////////////////////////////////////////////
// Bicubic helpers
//////////////////////////////////////////////////////

// One-dimensional Catmull-Rom spline basis
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
    // else 0
    return 0.0;
}

// A small helper to do 2D bicubic weight
// We'll treat (u, v) in [-2..2], then multiply catmullRom1D(u)*catmullRom1D(v).
float bicubicWeight2D(float u, float v)
{
    return catmullRom1D(u) * catmullRom1D(v);
}

// ----------------------------------------------------------------------
// sampleCubemapBicubic
//   - cubemap : the samplerCube
//   - dir : the main direction in 3D
//   - baseOffset : how big each sample step is (like 0.01..0.02 radians)
// ----------------------------------------------------------------------
vec4 sampleCubemapBicubic(samplerCube cubemap, vec3 dir, float baseOffset)
{
    // We'll do a 4x4 sampling in a local tangent frame around 'dir'
    // and accumulate with bicubic weights.

    // Build a local frame: 'dir' is forward
    vec3 fwd = normalize(dir);
    // pick an arbitrary up
    vec3 tempUp = abs(fwd.y) < 0.99 ? vec3(0, 1, 0) : vec3(1, 0, 0);
    vec3 side = normalize(cross(fwd, tempUp));
    vec3 up   = normalize(cross(side, fwd));

    // We'll sum color and total weight
    vec4 accumColor = vec4(0.0);
    float accumWeight = 0.0;

    // We'll sample offsets i in {0,1,2,3} => centered around 1.5
    // so that i-1.5 in [-1.5..+1.5], similar to a typical 4x4 bicubic approach
    for (int i = 0; i < 4; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            // offU, offV in [-1.5..1.5]
            float offU = float(i) - 1.5;
            float offV = float(j) - 1.5;

            // distance in "samples" for the Catmull-Rom function
            float w = bicubicWeight2D(offU, offV);

            // Convert (offU, offV) to angular offsets
            // scale them by baseOffset (like 0.02)
            vec3 sampleDir = fwd
            + (offU * baseOffset) * side
            + (offV * baseOffset) * up;

            sampleDir = normalize(sampleDir);

            vec4 c = texture(cubemap, sampleDir);

            accumColor  += c * w;
            accumWeight += w;
        }
    }

    // Normalize
    if (accumWeight > 0.0)
    return accumColor / accumWeight;
    else
    return texture(cubemap, dir);
}

//////////////////////////////////////////////////////
// Lanczos helpers
//////////////////////////////////////////////////////

// 1D Lanczos function
// x is distance in "samples", lobes is typically 2 or 3
float lanczos1D(float x, float lobes)
{
    x = abs(x);
    if (x < 1e-5) {
        return 1.0;// avoid 0/0
    }
    if (x > lobes) {
        return 0.0;
    }
    // sin(pi*x)/(pi*x) * sin(pi*x/lobes)/(pi*x/lobes)
    float pi_x   = 3.14159265359 * x;
    float pi_xL  = pi_x / lobes;
    return (sin(pi_x)/(pi_x)) * (sin(pi_xL)/(pi_xL));
}

// 2D version for convenience
float lanczos2D(float u, float v, float lobes)
{
    return lanczos1D(u, lobes) * lanczos1D(v, lobes);
}

// ----------------------------------------------------------------------
// sampleCubemapLanczos
//   - cubemap      : the samplerCube
//   - dir          : the main direction in 3D
//   - baseOffset   : how big each sample step is (e.g. 0.005 radians)
//   - lobes        : e.g. 2.0 or 3.0
//   - sampleRadius : integer radius in "step" units, e.g. 2 => i,j in [-2..2]
//   - stepSize     : fractional increment, e.g. 0.5 => [-2, -1.5, -1, ... , +2]
// ----------------------------------------------------------------------
vec4 sampleCubemapLanczos(
samplerCube cubemap,
vec3 dir,
float baseOffset,
float lobes,
int   sampleRadius,
float stepSize)
{
    vec3 fwd = normalize(dir);

    // Build local tangent frame
    vec3 tempUp = (abs(fwd.y) < 0.99) ? vec3(0, 1, 0) : vec3(1, 0, 0);
    vec3 side   = normalize(cross(fwd, tempUp));
    vec3 up     = normalize(cross(side, fwd));

    vec4 accumColor  = vec4(0.0);
    float accumWeight = 0.0;

    // We loop over i, j from -sampleRadius..sampleRadius in increments of stepSize.
    float minRange = -float(sampleRadius);
    float maxRange =  float(sampleRadius) + 0.001;// small epsilon to include last step

    for (float i = minRange; i <= maxRange; i += stepSize)
    {
        for (float j = minRange; j <= maxRange; j += stepSize)
        {
            float w = lanczos2D(i, j, lobes);

            // Build the sample direction
            vec3 sampleDir = fwd
            + (i * baseOffset) * side
            + (j * baseOffset) * up;
            sampleDir = normalize(sampleDir);

            // Sample the cubemap
            vec4 c = texture(cubemap, sampleDir);

            // Accumulate
            accumColor  += c * w;
            accumWeight += w;
        }
    }

    // Normalize if we got any non-zero weights
    if (accumWeight > 0.0)
    return accumColor / accumWeight;
    else
    return texture(cubemap, dir);
}

// ---------------------------------------------------
// Tone Mapping (Uncharted2)
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
// Standard PCF Shadow Calculation (no displacement)
// ---------------------------------------------------
float ShadowCalculationStandard(vec4 fragPosLightSpace, sampler2D shadowMap)
{
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;

    // If outside the [0,1] range, no shadow
    if (projCoords.x < 0.0 || projCoords.x > 1.0 ||
    projCoords.y < 0.0 || projCoords.y > 1.0)
    {
        return 0.0;
    }

    float closestDepth = texture(shadowMap, projCoords.xy).r;
    float currentDepth = projCoords.z;
    float bias = 0.005;

    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);

    for (int x = -1; x <= 1; ++x)
    {
        for (int y = -1; y <= 1; ++y)
        {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            shadow += (currentDepth - bias > pcfDepth) ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;

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
vec3 lightPos, // e.g. pick main light
float biasFactor, // e.g. 0.05
float minBias, // e.g. 0.0005
float shadowStrength,
float surfaceDepth
)
{
    vec3 displacedPos = fragPosWorld;
    displacedPos.y += waveHeight;

    vec4 fragPosLightSpace = lightSpaceMatrix * model * vec4(displacedPos, 1.0);
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;

    // If outside
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
    for (int x = -samples; x <= samples; ++x)
    {
        for (int y = -samples; y <= samples; ++y)
        {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            float comparison = currentDepth - bias - pcfDepth;
            // For smoother transitions, you can do:
            shadow += smoothstep(0.0, 0.005, comparison);
        }
    }
    shadow /= float((samples * 2 + 1) * (samples * 2 + 1));

    // Attenuate by surface depth
    shadow *= exp(-surfaceDepth * 0.1) * shadowStrength;
    shadow = clamp(shadow, 0.0, 1.0);
    return shadow;
}

/*******************************************************
 *  Basic Ambient Only
 *******************************************************/
vec3 computeAmbientColor(vec3 baseColor)
{
    // Multiply the base color by the global ambientColor uniform
    // e.g. if ambientColor = (0.2, 0.2, 0.2),
    // then result = baseColor * (0.2,0.2,0.2)
    return baseColor * ambientColor;
}

// ---------------------------------------------------
// Compute Diffuse Lighting (standard version)
// ---------------------------------------------------
vec3 computeDiffuseLighting(vec3 normal, vec3 fragPos, vec3 baseColor)
{
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; ++i)
    {
        vec3 lightDir = normalize(lightPositions[i] - fragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * baseColor * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse;
}

// ---------------------------------------------------
// Compute Phong Lighting (standard version)
// ---------------------------------------------------
vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor)
{
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);
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

    return ambient + diffuse + specular;
}

// ---------------------------------------------------
// Particle-specific lighting with distance attenuation
// ---------------------------------------------------
vec3 computeParticlePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 baseColor, float shininess)
{
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    for (int i = 0; i < 10; ++i)
    {
        // Distance-based attenuation
        vec3 lightVec = lightPositions[i] - fragPos;
        float distance = length(lightVec);
        vec3 lightDir = normalize(lightVec);

        float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));

        // Diffuse shading
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];

        // Blinn-Phong specular
        vec3 halfwayDir = normalize(lightDir + viewDir);
        float specAngle = max(dot(normal, halfwayDir), 0.0);
        float spec = pow(specAngle, max(shininess, 0.0));
        specular += attenuation * spec * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeParticleDiffuseLighting(vec3 normal, vec3 fragPos, vec3 baseColor)
{
    vec3 ambient = 0.1 * baseColor;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; ++i)
    {
        vec3 lightVec = lightPositions[i] - fragPos;
        float distance = length(lightVec);
        vec3 lightDir = normalize(lightVec);

        float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * (distance * distance));

        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += attenuation * lightColors[i] * diff * baseColor * lightStrengths[i];
    }

    return ambient + diffuse;
}

//---------------- Procedural Displacement for POM -----------------
float proceduralDisplacement(vec2 coords) {
    if (useCheckerPattern) {
        float cellCount=5.0;
        vec2 cellCoords=fract(coords*cellCount);
        float cellVal=(step(0.5, cellCoords.x)==step(0.5, cellCoords.y))?1.0:-1.0;
        return 0.5+0.5*cellVal*waveAmplitude;
    } else {
        float nf=smoothNoise(coords*randomness);
        float waveX=sin(coords.y*10.0+time*waveSpeed+nf*texCoordFrequency);
        float waveY=cos(coords.x*10.0+time*waveSpeed+nf*texCoordFrequency);
        float h=(waveX+waveY)*0.5;
        // Increase contrast
        h=sign(h)*pow(abs(h), 2.0);
        return 0.5+0.5*h*waveAmplitude;
    }
}

// ---------------------------------------------------
// Parallax Occlusion Mapping
// ---------------------------------------------------
vec2 ParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset)
{
    // Number of layers based on view angle
    float numLayers = mix(float(pomMaxSteps), float(pomMinSteps), abs(viewDir.z));
    float layerDepth = 1.0 / numLayers;
    float currentLayerDepth = 0.0;
    vec2 P = viewDir.xy * pomHeightScale;
    vec2 deltaTexCoords = P / numLayers;

    // Initial values
    vec2 currentTexCoords = texCoords;
    float currentDepthMapValue = texture(displacementMap, currentTexCoords, textureLodLevel).r;
    if (invertDisplacementMap)
    {
        currentDepthMapValue = 1.0 - currentDepthMapValue;
    }

    // Depth from displacement map
    float depthFromTexture = currentDepthMapValue;

    // Linear search to find the layer where the view ray intersects the depth
    while (currentLayerDepth < depthFromTexture)
    {
        currentTexCoords -= deltaTexCoords;
        currentDepthMapValue = texture(displacementMap, currentTexCoords, textureLodLevel).r;
        if (invertDisplacementMap)
        {
            currentDepthMapValue = 1.0 - currentDepthMapValue;
        }
        depthFromTexture = currentDepthMapValue;
        currentLayerDepth += layerDepth;
    }

    // Backtrack to previous layer
    vec2 prevTexCoords = currentTexCoords + deltaTexCoords;
    float prevLayerDepth = currentLayerDepth - layerDepth;
    float prevDepthFromTexture = texture(displacementMap, prevTexCoords, textureLodLevel).r;
    if (invertDisplacementMap)
    {
        prevDepthFromTexture = 1.0 - prevDepthFromTexture;
    }

    // Refine intersection point with linear interpolation
    float weight = (depthFromTexture - currentLayerDepth) / ((depthFromTexture - currentLayerDepth) - (prevDepthFromTexture - prevLayerDepth));
    vec2 finalTexCoords = mix(currentTexCoords, prevTexCoords, weight);

    // Compute depth offset (scaled appropriately)
    depthOffset = pomHeightScale * (1.0 - mix(currentLayerDepth, prevLayerDepth, weight)) * 0.0001;// Adjust scaling factor as needed

    return finalTexCoords;
}

// ---------------------------------------------------
// Procedural Parallax Occlusion Mapping
// ---------------------------------------------------
vec2 ProceduralParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset) {
    float numLayers=mix(float(pomMaxSteps), float(pomMinSteps), abs(viewDir.z));
    float layerDepth=1.0/numLayers;
    float currentLayerDepth=0.0;

    vec2 P=viewDir.xy*pomHeightScale;
    vec2 deltaTexCoords=P/numLayers;

    vec2 currentTexCoords=texCoords;
    float currentDepth=proceduralDisplacement(currentTexCoords);
    if (invertDisplacementMap) currentDepth=1.0-currentDepth;
    float depthFromTexture=currentDepth;

    while (currentLayerDepth<depthFromTexture){
        currentTexCoords-=deltaTexCoords;
        currentDepth=proceduralDisplacement(currentTexCoords);
        if (invertDisplacementMap) currentDepth=1.0-currentDepth;
        depthFromTexture=currentDepth;
        currentLayerDepth+=layerDepth;
    }

    vec2 prevTexCoords=currentTexCoords+deltaTexCoords;
    float prevLayerDepth=currentLayerDepth - layerDepth;
    float prevDepth=proceduralDisplacement(prevTexCoords);
    if (invertDisplacementMap) prevDepth=1.0-prevDepth;

    float weight=(depthFromTexture - currentLayerDepth)/
    ((depthFromTexture - currentLayerDepth)-(prevDepth - prevLayerDepth));
    vec2 finalTexCoords=mix(currentTexCoords, prevTexCoords, weight);

    depthOffset = pomHeightScale*(1.0 - mix(currentLayerDepth, prevLayerDepth, weight))*0.0001;
    return finalTexCoords;
}

#endif// COMMON_FUNCS_GLSL
