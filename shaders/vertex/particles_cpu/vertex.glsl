#version 430

// -----------------------------------------------------------------------------
// Attribute inputs (match your Python _setup_vertex_attributes_cpu layout)
// -----------------------------------------------------------------------------
// CPU passes (pos.x, pos.y, pos.z, pos.w) in location=0,
// lifetimePercentage in location=1,
// particleID in location=2.
layout (location = 0) in vec4 position;// (x, y, z, w)
layout (location = 1) in float lifetimePercentage;// e.g., 0..1
layout (location = 2) in float particleID;// Unique ID

// -----------------------------------------------------------------------------
// Uniforms
// -----------------------------------------------------------------------------
uniform mat4 model;// Model transform (translation/scale/rotation)
uniform mat4 view;// View matrix (camera)
uniform mat4 projection;// Projection matrix (perspective/ortho)
uniform vec3 cameraPosition;// Camera world-space pos

uniform float particleSize;// Base size of the particle
uniform vec3  particleColor;// Base color of the particle

// -----------------------------------------------------------------------------
// Outputs to the fragment shader
// -----------------------------------------------------------------------------
out vec3  fragColor;
out float lifetimePercentageToFragment;
flat out float particleIDOut;
out vec3  fragPos;

void main()
{
    // 1) Convert position from local to world space
    vec4 worldPos = model * position;

    // 2) Standard MVP transform to get final clip-space
    gl_Position = projection * view * worldPos;

    // 3) Distance-based point size (matching transform feedback approach)
    vec3 toCam = cameraPosition - worldPos.xyz;
    float dist = length(toCam);
    float size = particleSize / dist;
    gl_PointSize = size;

    // 4) Pass outputs to the fragment shader
    fragColor = particleColor;
    lifetimePercentageToFragment = lifetimePercentage;
    particleIDOut = particleID;
    fragPos = worldPos.xyz;
}
