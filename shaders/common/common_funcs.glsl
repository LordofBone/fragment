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
// Particle simulation uniforms for fluid dynamics
// ---------------------------------------------------
uniform float maxFluidForce;
uniform float particlePressure;
uniform float particleViscosity;

// ---------------------------------------------------
// Global uniform arrays for lights
// ---------------------------------------------------
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

// ---------------------------------------------------
// Calculate fluid forces (pressure & viscosity)
// ---------------------------------------------------
vec3 calculateFluidForces(vec3 velocity)
{
    // pressure = -velocity * particlePressure
    vec3 pressureForce = -velocity * particlePressure;
    // viscosity = -velocity * particleViscosity
    vec3 viscosityForce = -velocity * particleViscosity;
    vec3 totalFluidForce = pressureForce + viscosityForce;

    float forceMag = length(totalFluidForce);
    if (forceMag > maxFluidForce && forceMag > 0.0)
    {
        totalFluidForce = normalize(totalFluidForce) * maxFluidForce;
    }
    return totalFluidForce;
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
