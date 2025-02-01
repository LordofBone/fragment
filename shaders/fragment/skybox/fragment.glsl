#version 330 core
#include "glsl_utilities.glsl"

in vec3 TexCoords;
out vec4 FragColor;

//uniform samplerCube environmentMap;

void main()
{
    //    FragColor = texture(environmentMap, TexCoords);
    FragColor = sampleEnvironmentMap(TexCoords);
}
