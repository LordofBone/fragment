#version 330 core

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform samplerCube environmentMap;
uniform vec3 cameraPos;
uniform float time;
uniform float waveSpeed;
uniform float waveAmplitude;
uniform float randomness;
uniform float texCoordFrequency;
uniform float texCoordAmplitude;

float noise(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float smoothNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(noise(i + vec2(0.0, 0.0)), noise(i + vec2(1.0, 0.0)), f.x),
    mix(noise(i + vec2(0.0, 1.0)), noise(i + vec2(1.0, 1.0)), f.x),
    f.y);
}

void main()
{
    vec2 waveTexCoords = TexCoords;
    float noiseFactor = smoothNoise(waveTexCoords * randomness);
    waveTexCoords.x += sin(time * waveSpeed + TexCoords.y * texCoordFrequency + noiseFactor) * texCoordAmplitude;
    waveTexCoords.y += cos(time * waveSpeed + TexCoords.x * texCoordFrequency + noiseFactor) * texCoordAmplitude;

    vec3 normalMap = vec3(0.0, 0.0, 1.0);// Using a constant normal pointing up
    normalMap.xy += waveAmplitude * vec2(sin(waveTexCoords.y * 10.0),
    cos(waveTexCoords.x * 10.0));
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
