#version 330 core

in vec2 TexCoords;

out vec4 FragColor;

uniform sampler2D diffuseMap;

void main()
{
    // 1) Sample the diffuse texture to get the base color
    vec3 baseColor = texture(diffuseMap, TexCoords).rgb;

    // 2) Output with full opacity
    FragColor = vec4(baseColor, 1.0);
}
