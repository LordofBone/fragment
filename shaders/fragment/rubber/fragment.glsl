#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 Tangent;
in vec3 Bitangent;
in vec4 FragPosLightSpace;

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
uniform vec3 cameraPos;

uniform float parallaxScale;

// Function to compute the TBN matrix
mat3 computeTBN(vec3 normal, vec3 tangent, vec3 bitangent)
{
    // Normalize the input vectors
    vec3 T = normalize(tangent);
    vec3 B = normalize(bitangent);
    vec3 N = normalize(normal);

    return mat3(T, B, N);
}

// Parallax mapping function
vec2 parallaxMapping(vec2 texCoords, vec3 viewDirTangent)
{
    float height = texture(displacementMap, texCoords).r;
    // Adjust the height value (invert if necessary)
    height = height * parallaxScale - (parallaxScale / 2.0);

    // Offset texture coordinates
    vec2 p = viewDirTangent.xy * height;
    return texCoords + p;
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

// Lighting functions
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
        float spec = pow(max(dot(normal, halfwayDir), 0.0), 32.0 * (1.0 - roughness));// Adjusted shininess
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

// Shadow calculation function
float ShadowCalculation(vec4 fragPosLightSpace)
{
    // Perform perspective divide
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    // Transform to [0,1] range
    projCoords = projCoords * 0.5 + 0.5;

    // Check if fragment is outside the shadow map
    if (projCoords.z > 1.0)
    return 0.0;

    // Get closest depth value from light's perspective
    float closestDepth = texture(shadowMap, projCoords.xy).r;
    // Get depth of current fragment from light's perspective
    float currentDepth = projCoords.z;

    // Bias to prevent shadow acne
    float bias = 0.005;
    float shadow = 0.0;

    // Percentage-Closer Filtering (PCF) for softer shadows
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    for (int x = -1; x <= 1; ++x)
    {
        for (int y = -1; y <= 1; ++y)
        {
            float pcfDepth = texture(shadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            shadow += currentDepth - bias > pcfDepth ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;

    return shadow;
}

void main()
{
    // Compute the TBN matrix
    mat3 TBN = computeTBN(Normal, Tangent, Bitangent);

    // Calculate view direction in tangent space
    vec3 viewDir = normalize(view * vec4(-FragPos, 0.0)).xyz;
    vec3 viewDirTangent = normalize(TBN * viewDir);

    // Apply parallax mapping to adjust texture coordinates
    vec2 texCoords = parallaxMapping(TexCoords, viewDirTangent);

    // Sample the normal map using adjusted texture coordinates
    vec3 sampledNormal = texture(normalMap, texCoords, textureLodLevel).rgb;
    sampledNormal = normalize(sampledNormal * 2.0 - 1.0);

    // Transform normal to world space
    vec3 normal = normalize(TBN * sampledNormal);

    // Recalculate view direction in world space
    viewDir = normalize(cameraPos - FragPos);// Assuming you have cameraPos uniform

    // Reflect direction for environment mapping
    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    // Calculate shadow
    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPosLightSpace);
    }

    vec3 finalColor;
    if (phongShading) {
        finalColor = computePhongLighting(normal, viewDir, texCoords);
    } else {
        finalColor = computeLightingWithoutPhong(normal, texCoords);
    }

    // Apply shadow to lighting
    finalColor = (1.0 - shadow) * finalColor;

    // Fresnel effect for edges
    float fresnel = pow(1.0 - dot(viewDir, normal), 3.0);
    vec3 reflection = mix(envColor, vec3(1.0), fresnel);

    vec3 result = finalColor + reflection * envSpecularStrength;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
