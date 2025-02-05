#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texCoords;
layout(location = 3) in vec3 tangent;
layout(location = 4) in vec3 bitangent;

// ---------------------------------------------------------
// Outputs to the fragment shader
// ---------------------------------------------------------
out vec2 TexCoords;
out vec3 FragPos;// World-space fragment position
out vec3 Normal;// World-space normal (if you need it)
out vec3 TangentFragPos;// Tangent-space fragment position
out vec3 TangentViewPos;// Tangent-space view position
out vec3 TangentLightPos;// Tangent-space light position
out vec4 FragPosLightSpace;// For shadow mapping
out float FragPosW;// Clip-space w (if needed)

// We will pass the TBN as 3 separate rows
out vec3 TBNrow0;// T in world space
out vec3 TBNrow1;// B in world space
out vec3 TBNrow2;// N in world space

// ---------------------------------------------------------
// Uniforms
// ---------------------------------------------------------
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;
uniform vec3 viewPosition;

void main()
{
    // 1) Compute world-space position & normal
    vec4 worldPos4 = model * vec4(position, 1.0);
    FragPos = vec3(worldPos4);

    // For normal, do normal matrix approach
    mat3 normalMatrix = mat3(transpose(inverse(model)));
    Normal = normalize(normalMatrix * normal);

    // 2) Pass UV directly
    TexCoords = texCoords;

    // 3) Build TBN in world space
    vec3 T = normalize(mat3(model) * tangent);
    vec3 B = normalize(mat3(model) * bitangent);
    vec3 N = normalize(mat3(model) * normal);
    // Store them so the fragment can reconstruct mat3 TBN
    TBNrow0 = T;
    TBNrow1 = B;
    TBNrow2 = N;

    // 4) For parallax:
    //    Convert fragment pos, view pos, and light pos to tangent space
    //    Pick one main light source for simplicity
    vec3 lightPosW = vec3(lightSpaceMatrix * vec4(FragPos, 1.0));

    // Now transform to tangent space
    mat3 invTBN = transpose(mat3(T, B, N));

    TangentFragPos  = invTBN * FragPos;
    TangentViewPos  = invTBN * viewPosition;
    TangentLightPos = invTBN * lightPosW;

    // 5) Light-space position for shadow mapping
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPos, 1.0);

    // 6) Final clip-space position
    vec4 clipSpacePos = projection * view * vec4(FragPos, 1.0);
    gl_Position = clipSpacePos;

    // 7) Pass w if needed
    FragPosW = clipSpacePos.w;
}
