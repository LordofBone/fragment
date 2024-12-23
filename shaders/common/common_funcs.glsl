#ifndef COMMON_FUNCS_GLSL
#define COMMON_FUNCS_GLSL

// ---------------------------------------------------
// Global uniform arrays for lights
// ---------------------------------------------------
uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];

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

#endif// COMMON_FUNCS_GLSL
