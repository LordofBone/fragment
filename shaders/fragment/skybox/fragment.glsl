#version 330 core
#include "common_funcs.glsl"

in vec3 TexCoords;
out vec4 FragColor;

uniform samplerCube environmentMap;

// Lanczos parameters
uniform float uOffset;// baseOffset
uniform float uLobes;// e.g. 2.0 or 3.0
uniform int   uSampleRadius;// e.g. 2
uniform float uStepSize;// e.g. 0.5, 0.75, ...
uniform float uSharpen;// e.g. 0.0 for no sharpen, 0.5 for mild, etc.

void main()
{
    FragColor = sampleCubemapLanczos(
    environmentMap,
    TexCoords,
    uOffset,
    uLobes,
    uSampleRadius,
    uStepSize,
    uSharpen
    );
}
