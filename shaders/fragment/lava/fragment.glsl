#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform samplerCube environmentMap;
uniform vec3 cameraPos;
uniform float time;
uniform float waveSpeed;
uniform float waveAmplitude;
uniform float randomness;
uniform float texCoordFrequency;
uniform float texCoordAmplitude;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];

uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;

uniform sampler2D shadowMap;
uniform float surfaceDepth;
uniform float shadowStrength;

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

// Shadow calculation function
float ShadowCalculation(vec4 fragPosLightSpace, vec3 normal, float waveHeight) {
    // Perform perspective divide
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    // Transform to [0,1] range
    projCoords = projCoords * 0.5 + 0.5;

    // Offset the depth based on the normal map and wave height
    projCoords.z -= waveHeight * 0.1;// Adjust scaling factor as needed

    // Check if fragment is outside the shadow map
    if (projCoords.z > 1.0)
    return 0.0;

    // Get closest depth value from light's perspective
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    // Get depth of current fragment from light's perspective
    float currentDepth = projCoords.z;
    // Bias to prevent shadow acne
    float bias = max(0.005 * (1.0 - dot(normal, normalize(lightPositions[0] - FragPos))), 0.0005);
    // Check whether current fragment is in shadow
    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    // PCF for soft shadows
    int samples = 3;
    for (int x = -samples; x <= samples; ++x)
    {
        for (int y = -samples; y <= samples; ++y)
        {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            shadow += currentDepth - bias > pcfDepth ? 1.0 : 0.0;
        }
    }
    shadow /= float((samples * 2 + 1) * (samples * 2 + 1));

    // Attenuate shadow based on lava depth and shadow strength
    shadow *= exp(-surfaceDepth * 0.1) * shadowStrength;// Adjust attenuation factor as needed

    // Clamp shadow value
    shadow = clamp(shadow, 0.0, 1.0);

    return shadow;
}

vec3 computePhongLighting(vec3 normalMap, vec3 viewDir) {
    vec3 ambient = vec3(0.2, 0.1, 0.0);// Warm ambient light
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normalMap, lightDir), 0.0);
        diffuse += lightColors[i] * diff * lightStrengths[i];

        // Specular component
        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normalMap, halfwayDir), 0.0), 32.0);
        specular += lightColors[i] * spec * lightStrengths[i];
    }
    return ambient + diffuse + specular;
}

void main()
{
    // Generate dynamic texture coordinates
    vec2 waveTexCoords = TexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    // Generate normal map based on wave pattern
    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);
    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    vec3 viewDir = normalize(cameraPos - FragPos);
    vec3 reflectDir = reflect(-viewDir, normalMap);

    // Environment reflection
    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);

    // Lava color based on noise
    vec3 baseColor = vec3(1.0, 0.3, 0.0);// Deep lava color
    vec3 brightColor = vec3(1.0, 0.7, 0.0);// Bright lava color

    float noiseValue = smoothNoise(TexCoords * 5.0 + time * 0.5);
    vec3 lavaColor = mix(baseColor, brightColor, noiseValue);
    vec3 color = mix(lavaColor, reflection, fresnel * 0.2);

    // Compute wave height for shadow offset
    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    // Compute shadow
    float shadow = ShadowCalculation(FragPosLightSpace, normalMap, waveHeight);

    // Apply shadow to lighting
    if (phongShading) {
        vec3 phongColor = computePhongLighting(normalMap, viewDir);
        // Shadows reduce brightness slightly, as lava is emissive
        color = mix(color, color * (1.0 - shadow * 0.5), 0.5) + phongColor * 0.5;
    } else {
        // Apply shadow to color directly
        color = mix(color, color * (1.0 - shadow * 0.5), 1.0);
    }

    // Additional lava effects
    float bubbleNoise = smoothNoise(TexCoords * 10.0 + time * 2.0);
    if (bubbleNoise > 0.8) {
        color = brightColor;
    }

    float rockNoise = smoothNoise(TexCoords * 20.0 + time * 0.1);
    if (rockNoise > 0.9) {
        color = mix(color, vec3(0.2, 0.2, 0.2), rockNoise - 0.9);
    }

    // Apply tone mapping and gamma correction
    if (applyToneMapping) {
        color = toneMapping(color);
    }

    if (applyGammaCorrection) {
        color = pow(color, vec3(1.0 / 2.2));
    }

    // Final color output
    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
