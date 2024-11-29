#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform samplerCube environmentMap;
uniform vec3 cameraPos;
uniform vec3 ambientColor;
uniform float time;
uniform float waveSpeed;
uniform float waveAmplitude;
uniform float randomness;
uniform float texCoordFrequency;
uniform float texCoordAmplitude;
uniform sampler2D shadowMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];

uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;

uniform float surfaceDepth;
uniform float shadowStrength;

uniform mat4 model;
uniform mat4 lightSpaceMatrix;

// Noise functions
float noise(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float smoothNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
    mix(noise(i + vec2(0.0, 0.0)), noise(i + vec2(1.0, 0.0)), f.x),
    mix(noise(i + vec2(0.0, 1.0)), noise(i + vec2(1.0, 1.0)), f.x),
    f.y
    );
}

// Tone mapping functions
vec3 Uncharted2Tonemap(vec3 x) {
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;

    return ((x * (A * x + C * B) + D * E) /
    (x * (A * x + B) + D * F)) - E / F;
}

vec3 toneMapping(vec3 color) {
    vec3 curr = Uncharted2Tonemap(color * 2.0);
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

// Phong lighting function
vec3 computePhongLighting(vec3 normalMap, vec3 viewDir) {
    vec3 ambient = ambientColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normalMap, lightDir), 0.0);
        diffuse += lightColors[i] * diff * lightStrengths[i];

        vec3 reflectDir = reflect(-lightDir, normalMap);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);// Specular exponent for sharp highlights
        specular += lightColors[i] * spec * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

// Updated shadow calculation function
float ShadowCalculation(vec3 fragPosWorld, vec3 normal, float waveHeight) {
    // Compute the displaced world position
    vec3 displacedPos = fragPosWorld;
    displacedPos.y += waveHeight;

    // Transform the displaced position to light space
    vec4 fragPosLightSpace = lightSpaceMatrix * model * vec4(displacedPos, 1.0);

    // Perform perspective divide
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    // Transform to [0,1] range
    projCoords = projCoords * 0.5 + 0.5;

    // Check if projCoords are outside the shadow map boundaries
    if (projCoords.x < 0.0 || projCoords.x > 1.0 ||
    projCoords.y < 0.0 || projCoords.y > 1.0 ||
    projCoords.z < 0.0 || projCoords.z > 1.0)
    {
        return 0.0;
    }

    // Get closest depth value from light's perspective
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    // Get depth of current fragment from light's perspective
    float currentDepth = projCoords.z;

    // Bias to prevent shadow acne
    float bias = max(0.05 * (1.0 - dot(normal, normalize(lightPositions[0] - displacedPos))), 0.005);

    // Percentage-Closer Filtering (PCF) for softer shadows
    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    int samples = 3;
    for (int x = -samples; x <= samples; ++x) {
        for (int y = -samples; y <= samples; ++y) {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            float comparison = currentDepth - bias - pcfDepth;
            shadow += smoothstep(0.0, 0.005, comparison);
        }
    }
    shadow /= float((samples * 2 + 1) * (samples * 2 + 1));

    // Attenuate shadow based on water depth
    shadow *= exp(-surfaceDepth * 0.1) * shadowStrength;

    return shadow;
}

void main()
{
    // Generate the water normal map
    vec2 waveTexCoords = TexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);
    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    // Compute wave height
    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    vec3 viewDir = normalize(cameraPos - FragPos);
    vec3 lightDir = normalize(lightPositions[0] - FragPos);// Assuming one light source

    // Compute reflection and refraction using the environment map
    vec3 reflectDir = reflect(-viewDir, normalMap);
    vec3 refractDir = refract(-viewDir, normalMap, 1.0 / 1.33);

    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);

    vec3 envColor = mix(refraction, reflection, fresnel);

    // Calculate shadow
    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPos, normalMap, waveHeight);
    }

    // Phong lighting components
    vec3 color = vec3(0.0);
    if (phongShading) {
        vec3 phongColor = computePhongLighting(normalMap, viewDir);
        // Apply shadow to Phong lighting
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color += phongColor;
    }

    // Combine environment color and apply shadow
    envColor = mix(envColor, envColor * (1.0 - shadow), shadowStrength);

    color += envColor;

    // Apply tone mapping and gamma correction if enabled
    if (applyToneMapping) {
        color = toneMapping(color);
    }

    if (applyGammaCorrection) {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
