#version 330 core

layout(location = 0) in vec2 textureCoords;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec3 position;

out vec2 TexCoords;
out vec3 FragPos;
out vec3 Normal;
out vec3 TangentFragPos;
out vec3 TangentViewPos;
out vec3 TangentLightPos[10];

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform vec3 viewPosition;
uniform vec3 lightPositions[10];

void main()
{
    FragPos = vec3(model * vec4(position, 1.0));
    Normal = normalize(mat3(transpose(inverse(model))) * normal);
    TexCoords = textureCoords;

    vec3 T = normalize(mat3(model) * vec3(1.0, 0.0, 0.0));
    vec3 B = normalize(mat3(model) * vec3(0.0, 1.0, 0.0));
    vec3 N = normalize(Normal);

    mat3 TBN = mat3(T, B, N);

    TangentFragPos = TBN * FragPos;
    TangentViewPos = TBN * viewPosition;

    for (int i = 0; i < 10; i++) {
        TangentLightPos[i] = TBN * lightPositions[i];
    }

    gl_Position = projection * view * model * vec4(position, 1.0);
}
