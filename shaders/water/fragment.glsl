#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform samplerCube environmentMap;
uniform vec3 cameraPos;
uniform float time;

const float waveSpeed = 0.03;
const float waveAmplitude = 0.1;

void main()
{
    vec2 waveTexCoords = TexCoords;
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * 10.0) * waveAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * 10.0) * waveAmplitude;

    vec3 normalMap = vec3(0.0, 0.0, 1.0);  // Using a constant normal pointing up
    normalMap.xy += waveAmplitude * vec2(sin(waveTexCoords.y * 10.0), cos(waveTexCoords.x * 10.0));
    normalMap = normalize(normalMap);

    vec3 viewDir = normalize(cameraPos - FragPos);
    vec3 reflectDir = reflect(-viewDir, normalMap);
    vec3 refractDir = refract(-viewDir, normalMap, 1.0 / 1.33);

    vec3 reflection = texture(environmentMap, reflectDir).rgb;
    vec3 refraction = texture(environmentMap, refractDir).rgb;

    float fresnel = pow(1.0 - dot(viewDir, normalMap), 3.0);

    vec3 color = mix(refraction, reflection, fresnel);

    FragColor = vec4(color, 1.0);
}
