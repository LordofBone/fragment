#version 330 core
#include "glsl_utilities.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;

void main()
{
    vec3 diffuseColor = texture(diffuseMap, TexCoords).rgb;

    vec3 resultColor = computeAmbientColor(diffuseColor);

    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(vec3(4.0, 1.0, 1.0));
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 result = resultColor * diff;

    // Incorporate `legacyOpacity` parameter
    float alpha = clamp(legacyOpacity, 0.0, 1.0);

    FragColor = vec4(result, alpha);
}
