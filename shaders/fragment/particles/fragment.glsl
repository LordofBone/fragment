#version 430
#include "common_funcs.glsl"

// Inputs from vertex shader
in vec3 fragColor;// Base color from vertex shader
in float lifetimePercentageToFragment;// Particle's lifetime fraction
flat in float particleIDOut;// Particle ID
in vec3 fragPos;// Particle position in world space

out vec4 finalColor;

// Uniforms controlling fade behavior
uniform vec3 particleFadeColor;
uniform bool particleFadeToColor;
uniform bool smoothEdges;

// Lighting and shading uniforms
uniform vec3 viewPosition;
uniform float opacity;
// Lighting mode selector: 0 => diffuse, 1 => Phong, 2 => PBR
uniform int lightingMode;

void main()
{
    // 1) Vary color within the particle using randomization
    vec2 localCoords = gl_PointCoord;// local coords within [0..1]
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);// ±10%

    // 2) Fade color over time if desired
    vec3 baseColor;
    if (particleFadeToColor)
    {
        baseColor = mix(variedColor, particleFadeColor, lifetimePercentageToFragment);
    }
    else
    {
        baseColor = variedColor;
    }

    // 3) Create a spherical normal for the particle
    //    (simulate a sphere in point-sprite)
    vec2 centeredCoord = gl_PointCoord * 2.0 - 0.10;
    float distSquared = dot(centeredCoord, centeredCoord);

    // Discard fragments outside the circle
    if (distSquared > 1.0)
    {
        discard;
    }

    float z = sqrt(max(1.0 - distSquared, 0.0));
    vec3 normal = normalize(vec3(centeredCoord, z));

    // 4) Lighting: Phong or diffuse with distance attenuation
    vec3 viewDir = normalize(viewPosition - fragPos);

    // Select between Phong lighting and diffuse-only lighting
    vec3 finalColorRGB;

    if (lightingMode == 0)
    {
        finalColorRGB = computeParticleDiffuseLighting(normal, fragPos, baseColor);
    }
    else if (lightingMode >= 1)
    {
        finalColorRGB = computeParticlePhongLighting(normal, viewDir, fragPos, baseColor);
    }

    // 5) Compute alpha (fade over time + optional smooth edges)
    float alphaBase;
    if (smoothEdges)
    {
        float edgeFactor = 1.0 - distSquared;// fade near edge
        alphaBase = edgeFactor * (1.0 - lifetimePercentageToFragment);
    }
    else
    {
        alphaBase = 1.0 - lifetimePercentageToFragment;
    }

    // Incorporate `opacity` parameter
    float alpha = clamp(alphaBase * opacity, 0.0, 1.0);

    // 6) Output final
    finalColor = vec4(finalColorRGB, alpha);
}
