#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;

uniform vec3 lightPositions[10];
uniform vec3 lightColors[10];
uniform float lightStrengths[10];
uniform float textureLodLevel;

uniform bool applyToneMapping;
uniform bool applyGammaCorrection;
uniform bool phongShading;
uniform vec3 ambientColor;// New uniform for ambient light color

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

vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 FragPos) {
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords).rgb;
    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);
    vec3 specularColor = vec3(1.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        diffuse += lightColors[i] * diff * texture(diffuseMap, TexCoords).rgb * lightStrengths[i];

        vec3 reflectDir = reflect(-lightDir, normal);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
        specular += spec * specularColor * lightColors[i] * lightStrengths[i];
    }

    return ambient + diffuse + specular;
}

vec3 computeDiffuseWithNormalMap(vec3 normal) {
    vec3 lighting = vec3(0.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        lighting += lightColors[i] * diff * lightStrengths[i];
    }

    return lighting * texture(diffuseMap, TexCoords).rgb;
}

void main()
{
    // Fetch the normal from the normal map and transform it to the range [-1, 1]
    vec3 normal = normalize(Normal + texture(normalMap, TexCoords).rgb * 2.0 - 1.0);

    // Calculate view direction (from fragment position to camera position)
    vec3 viewDir = normalize(-FragPos);// Assuming camera is at the origin (0, 0, 0)

    vec3 color;
    if (phongShading) {
        color = computePhongLighting(normal, viewDir, FragPos);
    } else {
        // Even without Phong shading, we still want the lighting to respect the normal map
        color = computeDiffuseWithNormalMap(normal);
    }

    // Add ambient light to the result
    color += ambientColor * texture(diffuseMap, TexCoords).rgb;

    if (applyToneMapping) {
        color = toneMapping(color);
    }

    if (applyGammaCorrection) {
        color = pow(color, vec3(1.0 / 2.2));
    }

    color = clamp(color, 0.0, 1.0);
    FragColor = vec4(color, 1.0);
}
