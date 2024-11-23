#version 330 core

in vec2 TexCoords;
out vec4 FragColor;

uniform sampler2D depthMap;

void main()
{
    float depthValue = texture(depthMap, TexCoords).r;
    FragColor = vec4(depthValue, depthValue, depthValue, 1.0);// Red channel represents depth
}
