#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texCoords;
layout(location = 3) in vec3 tangent;
layout(location = 4) in vec3 bitangent;

out vec2 TexCoords;
out vec3 FragPos;
out vec3 Normal;
out mat3 TBN;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;
uniform vec3 viewPosition;

out vec4 FragPosLightSpace;

void main()
{
    vec3 FragPosWorld = vec3(model * vec4(position, 1.0));
    FragPos = FragPosWorld;
    Normal = normalize(mat3(transpose(inverse(model))) * normal);

    // Create TBN matrix (assumes tangent and bitangent are from CPU-side and orthogonal)
    vec3 T = normalize(mat3(model) * tangent);
    vec3 B = normalize(mat3(model) * bitangent);
    vec3 N = normalize(mat3(model) * normal);
    TBN = mat3(T, B, N);

    TexCoords = texCoords;
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPosWorld, 1.0);

    gl_Position = projection * view * vec4(FragPosWorld, 1.0);
}
