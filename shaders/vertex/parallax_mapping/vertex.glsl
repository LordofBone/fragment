#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texCoords;
layout(location = 3) in vec3 tangent;
layout(location = 4) in float tangentHandedness;

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
    // Compute the normal matrix to handle non-uniform scaling correctly
    // normalMatrix = transpose(inverse(mat3(model)))
    mat3 normalMatrix = transpose(inverse(mat3(model)));

    // Transform normal and tangent using the normalMatrix
    vec3 N = normalize(normalMatrix * normal);
    vec3 T = normalize(normalMatrix * tangent);

    // Compute the bitangent using the handedness and ensure orthonormality
    vec3 B = cross(N, T) * tangentHandedness;
    B = normalize(B);
    T = normalize(cross(B, N));

    // Assign the orthonormal TBN to output variables
    Normal = N;
    Tangent = T;
    Bitangent = B;

    // Transform vertex position to world space
    FragPos = vec3(model * vec4(position, 1.0));
    TexCoords = texCoords;

    // Calculate position in light space (for shadow mapping)
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPos, 1.0);

    // Final position in clip space
    gl_Position = projection * view * vec4(FragPos, 1.0);
}
