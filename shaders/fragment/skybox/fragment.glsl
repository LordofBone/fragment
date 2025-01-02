#version 330 core
#include "common_funcs.glsl"

in vec3 TexCoords;

out vec4 FragColor;

uniform samplerCube environmentMap;

void main()
{
    // A small offset ~ 0.01 or 0.02
    float offsetAngle = 0.015;

    // Now do your custom 4-tap sampling
    FragColor = sampleCubemapTent(environmentMap, TexCoords, offsetAngle);
}