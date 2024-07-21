#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D heightMap;
uniform samplerCube environmentMap;

uniform vec3 lightPosition;
uniform vec3 viewPosition;

void main()
{
    // Retrieve normal from normal map
    vec3 normal = texture(normalMap, TexCoords).rgb;
    normal = normalize(normal * 2.0 - 1.0);// Transform normal vector to range [-1, 1]

    // Retrieve height from height map
    float height = texture(heightMap, TexCoords).r;

    // Calculate view and light directions
    vec3 viewDir = normalize(viewPosition - FragPos);
    vec3 lightDir = normalize(lightPosition - FragPos);

    // Calculate the reflection vector
    vec3 reflectDir = reflect(viewDir, normal);

    // Retrieve the environment color
    vec3 envColor = texture(environmentMap, reflectDir).rgb;

    // Calculate ambient lighting
    vec3 ambient = 0.1 * texture(diffuseMap, TexCoords).rgb;

    // Calculate diffuse lighting
    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = diff * texture(diffuseMap, TexCoords).rgb;

    // Calculate specular lighting
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(normal, halfwayDir), 0.0), 64.0);
    vec3 specular = spec * vec3(1.0);// White specular highlight

    // Combine results with height-based scaling
    vec3 result = ambient + diffuse + specular + envColor * height;

    FragColor = vec4(result, 1.0);
}
