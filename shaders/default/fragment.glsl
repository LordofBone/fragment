#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;

uniform vec3 lightPositions[4];
uniform vec3 lightColors[4];
uniform float lightStrengths[4];
uniform float lodLevel;

out vec4 FragColor;

void main()
{
    // Normalize the fragment normal
    vec3 normal = normalize(Normal);

    // Fetch the normal from the normal map and convert it from [0,1] to [-1,1]
    vec3 mapNormal = texture(normalMap, TexCoords, lodLevel).rgb;
    mapNormal = mapNormal * 2.0 - 1.0;// This assumes the normal map is in tangent space

    // Adjust the normal using the normal map (this is a simplified version assuming normal map is in world space)
    normal = normalize(normal + mapNormal);

    // Compute lighting
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords, lodLevel).rgb;// Simple ambient lighting
    vec3 lighting = vec3(0.0);

    for (int i = 0; i < 4; ++i) {
        vec3 lightDir = normalize(lightPositions[i] - FragPos);
        float diff = max(dot(normal, lightDir), 0.0);
        lighting += lightColors[i] * diff * lightStrengths[i];
    }

    vec3 diffuse = lighting * texture(diffuseMap, TexCoords, lodLevel).rgb;

    // Combine results
    vec3 result = ambient + diffuse;
    FragColor = vec4(result, 1.0);
}
