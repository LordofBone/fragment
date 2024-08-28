#version 330 core

in vec3 TexCoords;

out vec4 FragColor;

uniform samplerCube environmentMap;

void main()
{
    FragColor = texture(environmentMap, TexCoords);
}
