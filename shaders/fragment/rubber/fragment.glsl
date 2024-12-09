#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentLightPos;
in vec3 TangentViewPos;
in vec3 TangentFragPos;
in vec4 FragPosLightSpace;
in float FragPosW;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform samplerCube environmentMap;
uniform sampler2D shadowMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];

uniform float textureLodLevel;
uniform float envMapLodLevel;
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform bool shadowingEnabled;
uniform float envSpecularStrength;

uniform mat4 view;
uniform mat4 projection;
uniform vec3 viewPosition;

uniform float pomHeightScale;
uniform int pomMinSteps;
uniform int pomMaxSteps;

uniform bool invertDisplacementMap;

// Tone mapping and other utility functions
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

// Enhanced POM function with depth correction
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

vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec2 texCoords) {
    vec3 ambient = 0.1 * texture(diffuseMap, texCoords, textureLodLevel).rgb;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    float roughness = 0.5;// Reduced roughness for more shine

    for (int i = 0; i < 10; i++) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * texture(diffuseMap, texCoords, textureLodLevel).rgb * lightColors[i] * lightStrengths[i];

        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normal, halfwayDir), 0.0), 32.0 * (1.0 - roughness));
        specular += spec * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeLightingWithoutPhong(vec3 normal, vec2 texCoords) {
    vec3 ambient = 0.1 * texture(diffuseMap, texCoords, textureLodLevel).rgb;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; i++) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * texture(diffuseMap, texCoords, textureLodLevel).rgb * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse;
}

float ShadowCalculation(vec4 fragPosLightSpace)
{
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    float currentDepth = projCoords.z;
    float bias = 0.005;
    float shadow = 0.0;

    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    for (int x = -1; x <= 1; ++x)
    {
        for (int y = -1; y <= 1; ++y)
        {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y)*texelSize).r;
            shadow += currentDepth - bias > pcfDepth ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;

    return shadow;
}

void main()
{
    // Transform view direction into tangent space
    vec3 viewDir = normalize(TangentViewPos - TangentFragPos);

    // Apply Enhanced POM with Depth Correction
    float depthOffset = 0.0;
    vec2 newTexCoords = ParallaxOcclusionMapping(TexCoords, viewDir, depthOffset);

    // If parallax mapping results in coords outside 0-1, discard
    if (newTexCoords.x > 1.0 || newTexCoords.y > 1.0 || newTexCoords.x < 0.0 || newTexCoords.y < 0.0)
    discard;

    // Recalculate normal from normal map using the newTexCoords
    vec3 norm = texture(normalMap, newTexCoords, textureLodLevel).rgb;
    norm = normalize(norm * 2.0 - 1.0);

    // View direction in world space:
    vec3 worldViewDir = normalize(viewPosition - FragPos);

    // Compute reflection
    vec3 reflectDir = reflect(-worldViewDir, norm);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPosLightSpace);
    }

    vec3 finalColor;
    if (phongShading) {
        finalColor = computePhongLighting(norm, worldViewDir, newTexCoords);
    } else {
        finalColor = computeLightingWithoutPhong(norm, newTexCoords);
    }

    finalColor = (1.0 - shadow) * finalColor;

    // Fresnel effect
    float fresnel = pow(1.0 - dot(worldViewDir, norm), 3.0);
    vec3 reflection = mix(envColor, vec3(1.0), fresnel);

    vec3 result = finalColor + reflection * envSpecularStrength;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0/2.2));
    }

    FragColor = vec4(clamp(result, 0.0, 1.0), 1.0);

    // Depth Correction
    float correctedDepth = clamp(gl_FragCoord.z - depthOffset, 0.0, 1.0);
    gl_FragDepth = correctedDepth;
}
