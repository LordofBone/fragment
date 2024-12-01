#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texCoords;
layout(location = 3) in vec3 tangent;// Tangent vector
layout(location = 4) in vec3 bitangent;// Bitangent vector

out vec2 TexCoords;
out vec3 FragPos;
out vec3 Normal;
out vec3 TangentViewDir;// View direction in tangent space
out vec3 TangentFragPos;// Fragment position in tangent space
out vec4 FragPosLightSpace;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;

void main()
{
    FragPos = vec3(model * vec4(position, 1.0));
    Normal = normalize(mat3(transpose(inverse(model))) * normal);
    TexCoords = texCoords;

    // Calculate tangent space matrices
    mat3 TBN = transpose(mat3(
    normalize(mat3(model) * tangent),
    normalize(mat3(model) * bitangent),
    Normal
    ));

    vec3 viewPos = vec3(inverse(view) * vec4(0.0, 0.0, 0.0, 1.0));// Camera position in world space
    vec3 viewDir = normalize(viewPos - FragPos);
    TangentViewDir = TBN * viewDir;

    TangentFragPos = TBN * FragPos;

    // Calculate position in light space
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPos, 1.0);

    gl_Position = projection * view * vec4(FragPos, 1.0);
}
