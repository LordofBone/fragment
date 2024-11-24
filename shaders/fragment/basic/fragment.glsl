#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform vec3 ambientColor;

void main()
{
    // Sample the diffuse texture to get the base color
    vec3 diffuseColor = texture(diffuseMap, TexCoords).rgb;

    // Apply the ambient color as flat lighting
    vec3 resultColor = diffuseColor * ambientColor;

    // Output the color with full opacity
    FragColor = vec4(resultColor, 1.0);
}
