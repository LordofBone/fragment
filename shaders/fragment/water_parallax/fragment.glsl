#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos;
in vec4 FragPosLightSpace;

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

// POM uniforms
uniform float pomHeightScale;// If 0.0, no POM
uniform int pomMinSteps;
uniform int pomMaxSteps;
uniform bool invertDisplacementMap;

// Add a new uniform if you want to toggle checker pattern
uniform bool useCheckerPattern;// Set to true to use checker pattern

// Noise functions
float noise(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float smoothNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f*f*(3.0 - 2.0*f);
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
    return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F))-E/F;
}

vec3 toneMapping(vec3 color) {
    vec3 curr = Uncharted2Tonemap(color * 2.0);
    vec3 whiteScale = 1.0 / Uncharted2Tonemap(vec3(11.2));
    return curr * whiteScale;
}

// Modified Procedural displacement for POM
float proceduralDisplacement(vec2 coords) {
    if (useCheckerPattern) {
        // **Checker pattern**:
        // Scale coords to define how many cells per unit:
        float cellCount = 5.0;// Try adjusting this for more or fewer cells
        vec2 cellCoords = fract(coords * cellCount);

        // Determine cell color based on whether we're in an even or odd cell
        // We'll produce a binary pattern: 1.0 for one cell, -1.0 for the alternate cell.
        float cellVal = (step(0.5, cellCoords.x) == step(0.5, cellCoords.y)) ? 1.0 : -1.0;

        // Map cellVal from [-1,1] to [0,1] and apply waveAmplitude for height:
        // We still use waveAmplitude, but to get more "3D" effect, consider increasing pomHeightScale too.
        return 0.5 + 0.5 * cellVal * waveAmplitude;
    } else {
        // **Enhanced contrast wave pattern**
        float nf = smoothNoise(coords * randomness);
        float waveX = sin(coords.y * 10.0 + time * waveSpeed + nf * texCoordFrequency);
        float waveY = cos(coords.x * 10.0 + time * waveSpeed + nf * texCoordFrequency);
        float h = (waveX + waveY)*0.5;

        // Increase contrast using pow():
        // Take abs(h), raise it to a power >1 for stronger peaks, then reapply sign:
        h = sign(h)*pow(abs(h), 2.0);// Adjust power for desired contrast; try 2.0 or higher

        return 0.5 + 0.5 * h * waveAmplitude;
    }
}

// Parallax Occlusion Mapping function using procedural displacement
vec2 ParallaxOcclusionMapping(vec2 texCoords, vec3 viewDir, out float depthOffset)
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
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
        specular += lightColors[i] * spec * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

// Shadow calculation
float ShadowCalculation(vec3 fragPosWorld, vec3 normal, float waveHeight) {
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

    float bias = max(0.05 * (1.0 - dot(normal, normalize(lightPositions[0] - displacedPos))), 0.005);
    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    int samples = 3;
    for (int x = -samples; x <= samples; ++x) {
        for (int y = -samples; y <= samples; ++y) {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y)*texelSize).r;
            float comparison = currentDepth - bias - pcfDepth;
            shadow += smoothstep(0.0, 0.005, comparison);
        }
    }
    shadow /= float((samples*2+1)*(samples*2+1));

    shadow *= exp(-surfaceDepth * 0.1) * shadowStrength;
    return shadow;
}

void main()
{
    vec3 viewDir = normalize(cameraPos - FragPos);

    // If pomHeightScale > 0, do POM, otherwise skip
    float depthOffset = 0.0;
    vec2 workingTexCoords = TexCoords;
    if (pomHeightScale > 0.0) {
        vec3 tangentViewDir = normalize(TangentViewPos - TangentFragPos);
        workingTexCoords = ParallaxOcclusionMapping(TexCoords, tangentViewDir, depthOffset);
        workingTexCoords = clamp(workingTexCoords, 0.0, 1.0);
    }

    // Perform wave calculations using workingTexCoords
    vec2 waveTexCoords = workingTexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);

    // Use original TexCoords.x and TexCoords.y as suggested:
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    vec3 normalMap = vec3(0.0, 0.0, 1.0);
    float waveHeightX = sin(waveTexCoords.y * 10.0);
    float waveHeightY = cos(waveTexCoords.x * 10.0);
    normalMap.xy += waveAmplitude * vec2(waveHeightX, waveHeightY);
    normalMap = normalize(normalMap);

    float waveHeight = waveAmplitude * (waveHeightX + waveHeightY) * 0.5;

    vec3 reflectDir = reflect(-viewDir, normalMap);
    vec3 refractDir = refract(-viewDir, normalMap, 1.0 / 1.33);

    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);
    vec3 envColor = mix(refraction, reflection, fresnel);

    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPos, normalMap, waveHeight);
    }

    vec3 color = vec3(0.0);
    if (phongShading) {
        vec3 phongColor = computePhongLighting(normalMap, viewDir);
        phongColor = mix(phongColor, phongColor * (1.0 - shadow), shadowStrength);
        color += phongColor;
    }

    envColor = mix(envColor, envColor * (1.0 - shadow), shadowStrength);
    color += envColor;

    if (applyToneMapping) {
        color = toneMapping(color);
    }

    if (applyGammaCorrection) {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
