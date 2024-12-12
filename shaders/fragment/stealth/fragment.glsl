#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in mat3 TBN;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform sampler2D screenTexture;
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform vec3 viewPosition;
uniform float lightStrengths[10];
uniform float textureLodLevel;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float opacity;
uniform bool phongShading;
uniform float distortionStrength;
uniform float reflectionStrength;
uniform float environmentMapStrength;
uniform vec3 ambientColor;
uniform bool screenFacingPlanarTexture;
uniform bool warped;
uniform bool shadowingEnabled;

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

vec3 computeLighting(vec3 normal, vec3 viewDir, vec3 FragPos, vec3 diffuseColor, bool phong) {
    vec3 ambient = ambientColor * diffuseColor;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specColor = vec3(1.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diffuseColor * lightColors[i] * diff * lightStrengths[i];

        if (phong) {
            vec3 reflectDir = reflect(-lightDir, normal);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
            specular += specColor * lightColors[i] * spec * lightStrengths[i];
        }
    }

    return ambient + diffuse + specular;
}

float ShadowCalculation(vec4 fragPosLightSpace) {
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    // Transform to [0,1] range
    projCoords = projCoords * 0.5 + 0.5;
    // Get closest depth value from light's perspective (using [0,1] range fragPosLightSpace as coords)
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    // Get depth of current fragment from light's perspective
    float currentDepth = projCoords.z;
    // Check whether current fragment is in shadow
    float bias = 0.005;
    float shadow = currentDepth - bias > closestDepth ? 1.0 : 0.0;

    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    for (int x = -1; x <= 1; ++x) {
        for (int y = -1; y <= 1; ++y) {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y)*texelSize).r;
            shadow += (currentDepth - bias > pcfDepth) ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;

    return shadow;
}

void main() {
    vec2 flippedTexCoords = vec2(TexCoords.x, 1.0 - TexCoords.y);

    // Compute normal from normal map with TBN
    vec3 normalFromMap = texture(normalMap, flippedTexCoords, textureLodLevel).rgb * 2.0 - 1.0;
    vec3 normal = normalize(TBN * normalFromMap);

    float height = texture(displacementMap, flippedTexCoords, textureLodLevel).r;
    vec3 viewDir = normalize(viewPosition - FragPos);

    vec3 reflectDir;
    if (distortionStrength == 0.0) {
        reflectDir = reflect(viewDir, vec3(0.0, 0.0, 0.0));
    } else if (warped) {
        reflectDir = reflect(viewDir, FragPos);
    } else {
        reflectDir = reflect(viewDir, normal);
    }
    reflectDir = normalize(reflectDir);

    vec3 fallbackColor = vec3(0.2, 0.2, 0.2);
    vec3 envColor = vec3(0.0);
    if (dot(viewDir, normal) > 0.0) {
        envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;
        envColor = mix(fallbackColor, envColor, step(0.05, length(envColor)));
    } else {
        envColor = fallbackColor;
    }

    // Apply environmentMapStrength here
    envColor *= environmentMapStrength * reflectionStrength;

    vec3 diffuseColor = texture(diffuseMap, flippedTexCoords, textureLodLevel).rgb;

    vec2 reflectionTexCoords = (reflectDir.xy + vec2(1.0)) * 0.5;
    vec2 normalDistortion = (texture(normalMap, flippedTexCoords).rg * 2.0 - 1.0) * distortionStrength;
    vec2 distortedCoords = screenFacingPlanarTexture ? reflectionTexCoords + normalDistortion : flippedTexCoords + normalDistortion;

    vec3 backgroundColor = texture(screenTexture, clamp(distortedCoords, 0.0, 1.0)).rgb;
    if (length(backgroundColor) < 0.05) {
        backgroundColor = fallbackColor;
    }

    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPosLightSpace);
    }

    vec3 lighting = computeLighting(normal, viewDir, FragPos, diffuseColor, phongShading);
    lighting = (1.0 - shadow) * lighting;

    vec3 result = mix(backgroundColor, lighting, opacity) + envColor;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, opacity);
}
