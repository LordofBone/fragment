#version 330 core

layout(location = 0) in vec2 textureCoords;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec3 position;

out vec2 TexCoords;
out vec3 FragPos;
out vec3 Normal;
out vec4 FragPosLightSpace;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;

void main()
{
    FragPos = vec3(model * vec4(position, 1.0));
    Normal = normalize(mat3(transpose(inverse(model))) * normal);
    TexCoords = textureCoords;

    // Calculate position in light space
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPos, 1.0);

    gl_Position = projection * view * vec4(FragPos, 1.0);
}
