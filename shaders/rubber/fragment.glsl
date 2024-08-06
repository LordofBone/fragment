#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec3 TangentFragPos;
in vec3 TangentViewPos;
in vec3 TangentLightPos[10];

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D displacementMap;
uniform samplerCube environmentMap;

uniform vec3 lightColors[10];
uniform float lightStrengths[10];
uniform float textureLodLevel;// Separate LOD level for textures
uniform float envMapLodLevel;// Separate LOD level for environment map
uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform float envSpecularStrength;// Configurable environment specular strength

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

void main()
{
    vec3 normal = texture(normalMap, TexCoords, textureLodLevel).rgb;
    normal = normalize(normal * 2.0 - 1.0);

    float height = texture(displacementMap, TexCoords, textureLodLevel).r;

    vec3 viewDir = normalize(TangentViewPos - TangentFragPos);
    vec3 reflectDir = reflect(viewDir, normal);

    vec3 envColor = textureLod(environmentMap, reflectDir, envMapLodLevel).rgb;

    vec3 ambient = 0.05 * texture(diffuseMap, TexCoords, textureLodLevel).rgb;// Darker ambient

    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    float roughness = 0.8;// Higher value for rubbery material

    for (int i = 0; i < 10; i++) {
        vec3 lightDir = normalize(TangentLightPos[i] - TangentFragPos);

        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += diff * texture(diffuseMap, TexCoords, textureLodLevel).rgb * lightColors[i] * lightStrengths[i] * 0.5;// Darker diffuse

        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normal, halfwayDir), 0.0), 16.0 * (1.0 - roughness));
        specular += spec * lightColors[i] * lightStrengths[i];
    }

    vec3 result = ambient + diffuse + specular * 0.1 + envColor * height * envSpecularStrength;// Adjust env specular with configurable strength

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);

    FragColor = vec4(result, 1.0);
}
