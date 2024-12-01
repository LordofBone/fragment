#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentViewDir;
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
uniform float parallaxScale;

uniform mat4 view;

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

vec2 ParallaxMapping(vec2 texCoords, vec3 viewDir)
{
    float height = texture(displacementMap, texCoords).r;
    float heightScale = parallaxScale;// Adjust parallax scale (0.0 to disable)
    float heightBias = heightScale * 0.5;
    vec2 p = viewDir.xy / viewDir.z * (height * heightScale - heightBias);
    vec2 texCoordsOffset = texCoords + p;

    // Clamp the texture coordinates to prevent invalid accesses
    texCoordsOffset = clamp(texCoordsOffset, 0.0, 1.0);

    return texCoordsOffset;
}

vec3 computePhongLighting(vec3 normal, vec3 viewDir) {
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    float roughness = 0.5;// Reduced roughness for more shine

    for (int i = 0; i < 10; i++) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * texture(diffuseMap, TexCoords, textureLodLevel).rgb * lightColors[i] * lightStrengths[i];

        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normal, halfwayDir), 0.0), 32.0 * (1.0 - roughness));// Adjusted shininess
        specular += spec * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeLightingWithoutPhong(vec3 normal) {
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords, textureLodLevel).rgb;
    vec3 diffuse = vec3(0.0);

    for (int i = 0; i < 10; i++) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * texture(diffuseMap, TexCoords, textureLodLevel).rgb * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse;
}

float ShadowCalculation(vec4 fragPosLightSpace)
{
    // Perform perspective divide
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
    // Parallax mapping
    vec3 viewDir = normalize(TangentViewDir);
    vec2 texCoords = TexCoords;
    if (parallaxScale > 0.0)
    {
        texCoords = ParallaxMapping(TexCoords, viewDir);
        // Discard fragments with invalid texture coordinates
        if (texCoords.x < 0.0 || texCoords.x > 1.0 || texCoords.y < 0.0 || texCoords.y > 1.0)
        discard;
    }

    // Fetch the normal from the normal map and transform it to the range [-1, 1]
    vec3 normal = texture(normalMap, texCoords, textureLodLevel).rgb;
    normal = normalize(normal * 2.0 - 1.0);

    // Reconstruct TBN matrix in fragment shader (optional but necessary if not passed from vertex shader)
    vec3 tangent = normalize(vec3(1.0, 0.0, 0.0));
    vec3 bitangent = normalize(vec3(0.0, 1.0, 0.0));
    mat3 TBN = mat3(tangent, bitangent, vec3(0.0, 0.0, 1.0));

    // Transform normal to world space (if necessary)
    normal = normalize(TBN * normal);

    // Recalculate view direction in world space
    vec3 viewFragPos = FragPos;
    viewDir = normalize(-vec3(view * vec4(viewFragPos, 1.0)));

    vec3 reflectDir = reflect(viewDir, normal);
    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    // Calculate shadow
    float shadow = 0.0;
    if (shadowingEnabled) {
        shadow = ShadowCalculation(FragPosLightSpace);
    }

    vec3 finalColor;
    if (phongShading) {
        finalColor = computePhongLighting(normal, viewDir);
    } else {
        finalColor = computeLightingWithoutPhong(normal);
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
