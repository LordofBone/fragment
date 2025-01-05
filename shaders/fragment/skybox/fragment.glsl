#version 330 core
#include "common_funcs.glsl"

in vec3 TexCoords;
out vec4 FragColor;

uniform samplerCube environmentMap;

void main()
{
    // Lanczos upsampling
    float offset     = 0.005;
    float lobes      = 3.0;
    int sampleRadius = 2;// -2..2 => 25 taps

    FragColor = sampleCubemapLanczos(environmentMap, TexCoords, offset, lobes, sampleRadius);
}