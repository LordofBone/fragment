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
    vec3 normal = normalize(Normal + texture(normalMap, TexCoords).rgb * 2.0 - 1.0);
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords).rgb;
    vec3 lighting = vec3(0.0);

    for (int i = 0; i < 10; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        lighting += lightColors[i] * diff * lightStrengths[i];
    }

    vec3 diffuse = lighting * texture(diffuseMap, TexCoords).rgb;
    vec3 result = ambient + diffuse;

    if (applyToneMapping) {
        result = toneMapping(result);
    }

    if (applyGammaCorrection) {
        result = pow(result, vec3(1.0 / 2.2));
    }

    result = clamp(result, 0.0, 1.0);
    FragColor = vec4(result, 1.0);
}
