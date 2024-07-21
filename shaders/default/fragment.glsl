#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform vec3 lightPosition;  // Ensure you set this from your Python code

out vec4 FragColor;

void main()
{
    // Normalize the fragment normal
    vec3 normal = normalize(Normal);

    // Fetch the normal from the normal map and convert it from [0,1] to [-1,1]
    vec3 mapNormal = texture(normalMap, TexCoords).rgb;
    mapNormal = mapNormal * 2.0 - 1.0; // This assumes the normal map is in tangent space

    // Adjust the normal using the normal map (this is a simplified version assuming normal map is in world space)
    normal = normalize(normal + mapNormal);

    // Compute lighting
    vec3 lightDir = normalize(lightPosition - FragPos);
    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = diff * texture(diffuseMap, TexCoords).rgb;

    // Combine results
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords).rgb;  // Simple ambient lighting
    vec3 result = ambient + diffuse;
    FragColor = vec4(result, 1.0);
}