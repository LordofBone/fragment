#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform samplerCube environmentMap;
uniform vec3 cameraPos;
uniform vec3 ambientColor;// Uniform for ambient light color
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

float noise(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float smoothNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(noise(i + vec2(0.0, 0.0)), noise(i + vec2(1.0, 0.0)), f.x),
    mix(noise(i + vec2(0.0, 1.0)), noise(i + vec2(1.0, 1.0)), f.x),
    f.y);
}

vec3 Uncharted2Tonemap(vec3 x) {
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;

    return ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F;
}

vec3 toneMapping(vec3 color) {
    vec3 curr = Uncharted2Tonemap(color * 2.0);
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

vec3 computePhongLighting(vec3 normalMap, vec3 viewDir) {
    vec3 ambient = ambientColor;// Use the ambientColor uniform for ambient lighting
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

void main()
{
    // Generate the water normal map
    vec2 waveTexCoords = TexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    normalMap.xy += waveAmplitude * vec2(sin(waveTexCoords.y * 10.0), cos(waveTexCoords.x * 10.0));
    normalMap = normalize(normalMap);

    vec3 viewDir = normalize(cameraPos - FragPos);

    // Phong lighting components
    vec3 phongColor = vec3(0.0);
    if (phongShading) {
        phongColor = computePhongLighting(normalMap, viewDir);
    }

    vec3 envColor = vec3(0.0);// Default environment color is black (no reflection)

    // Check if the environment map is active (assumes environmentMap is texture unit 0)
    if (textureSize(environmentMap, 0).x > 1) {
        // Compute reflection and refraction using the environment map
        vec3 reflectDir = reflect(-viewDir, normalMap);
        vec3 refractDir = refract(-viewDir, normalMap, 1.0 / 1.33);

        vec3 reflection = texture(environmentMap, reflectDir).rgb;
        vec3 refraction = texture(environmentMap, refractDir).rgb;

        float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);

        // Mix the environment map reflection/refraction with the phong lighting
        envColor = mix(refraction, reflection, fresnel) + phongColor;
    } else {
        // Fallback: if no environment map, use ambient lighting and Phong lighting
        envColor = phongColor + ambientColor * normalMap;
    }

    // Apply tone mapping and gamma correction if enabled
    vec3 color = envColor;

    if (applyToneMapping) {
        color = toneMapping(color);
    }

    if (applyGammaCorrection) {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
