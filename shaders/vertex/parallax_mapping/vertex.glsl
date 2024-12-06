#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texCoords;
layout(location = 3) in vec3 tangent;
layout(location = 4) in vec3 bitangent;

out vec2 TexCoords;
out vec3 FragPos;
out vec3 Normal;
out vec3 Tangent;
out vec3 Bitangent;
out vec4 FragPosLightSpace;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;

void main()
{
    // Transform vertex position to world space
    FragPos = vec3(model * vec4(position, 1.0));

    // Transform normal vector to world space
    Normal = normalize(mat3(transpose(inverse(model))) * normal);

    // Transform tangent and bitangent vectors to world space
    Tangent = normalize(mat3(model) * tangent);
    Bitangent = normalize(mat3(model) * bitangent);

    TexCoords = texCoords;

    // Calculate position in light space
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPos, 1.0);

    // Calculate final vertex position
    gl_Position = projection * view * vec4(FragPos, 1.0);
}
