#version 330 core
#include "common_funcs.glsl"

in vec2 TexCoords;
in vec3 FragPos;
in vec3 Normal;
in vec4 FragPosLightSpace;

out vec4 FragColor;

uniform sampler2D diffuseMap;
uniform vec3 ambientColor;

void main()
{
    // 1) Sample the diffuse texture to get the base color
    vec3 baseColor = texture(diffuseMap, TexCoords).rgb;

    // 2) Multiply by ambientColor using our new function
    vec3 resultColor = computeAmbientColor(baseColor);

    // 3) Output with full opacity
    FragColor = vec4(resultColor, 1.0);
}
