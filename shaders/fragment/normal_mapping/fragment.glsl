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
    FragColor = vec4(result, 1.0);
}
