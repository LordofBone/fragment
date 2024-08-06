#version 410 core

layout(quads, fractional_odd_spacing, ccw) in;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoords;

void main()
{
    vec3 p0 = gl_in[0].gl_Position.xyz;
    vec3 p1 = gl_in[1].gl_Position.xyz;
    vec3 p2 = gl_in[2].gl_Position.xyz;
    vec3 p3 = gl_in[3].gl_Position.xyz;

    vec3 pos = mix(mix(p0, p1, gl_TessCoord.x), mix(p3, p2, gl_TessCoord.x), gl_TessCoord.y);
    gl_Position = projection * view * model * vec4(pos, 1.0);

    FragPos = pos;
    Normal = vec3(0.0, 1.0, 0.0);// Upward normal for the plane
    TexCoords = gl_TessCoord.xy;
}
