#version 430
#include "glsl_utilities.glsl"

// -----------------------------------------------------------------------------
// Inputs from vertex shader
// -----------------------------------------------------------------------------
in vec3  fragColor;// Base color from vertex shader
in float lifetimePercentageToFragment;// Particle's lifetime fraction [0..1]
flat in float particleIDOut;// Unique particle ID
in vec3  fragPos;// Particle position in world space

// -----------------------------------------------------------------------------
// Outputs
// -----------------------------------------------------------------------------
out vec4 finalColor;

// -----------------------------------------------------------------------------
// Uniforms controlling fade behavior
// -----------------------------------------------------------------------------
uniform vec3 particleFadeColor;// Color to fade to if enabled
uniform bool particleFadeToColor;// If true => blend color from fragColor to particleFadeColor
uniform bool smoothEdges;// If true => fade edges of the point sprite

// -----------------------------------------------------------------------------
// Lighting/shading uniforms (for your custom lighting funcs)
// -----------------------------------------------------------------------------
uniform vec3 viewPosition;// Camera/world-space position
uniform int lightingMode;// 0 => diffuse, 1 => Phong, etc.

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------
void main()
{
    // 1) Introduce slight per‐particle color variation so particles aren't identical
    vec2 localCoords = gl_PointCoord;
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Scale the incoming fragColor by ±10%
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);

    // 2) If we want the particle to fade its color over time, do a mix:
    //    at t=0 => variedColor
    //    at t=1 => particleFadeColor
    vec3 baseColor;
    // We need to boost the fade color to make it more visible when mixing
    vec3 particleFadeColorBoosted = particleFadeColor * 5.0;// Make the fade color more intense
    if (particleFadeToColor)
    {
        // Note: you can invert the mix arguments if you want the color
        // to start at fadeColor and end at variedColor. As is, it starts varied
        // and goes to fadeColor over lifetime [0..1].
        baseColor = mix(variedColor, particleFadeColorBoosted, lifetimePercentageToFragment);
    }
    else
    {
        baseColor = variedColor;
    }

    // 3) Create a spherical billboard by discarding fragments outside the point-sprite circle.
    //    The offset "- 0.10" is something you've found helps avoid clipping on certain GPUs.
    vec2 centeredCoord = gl_PointCoord * 2.0 - 0.10;
    float distSquared = dot(centeredCoord, centeredCoord);

    // Discard fragments outside the circle
    if (distSquared > 1.0)
    {
        discard;
    }

    // 4) Create a normal that pretends the point-sprite is a hemisphere
    float z = sqrt(max(1.0 - distSquared, 0.0));
    vec3 normal = normalize(vec3(centeredCoord, z));

    // 5) Basic lighting: either "diffuse" or "Phong" for demonstration
    vec3 viewDir = normalize(viewPosition - fragPos);

    // Select between Phong lighting and diffuse-only lighting
    vec3 finalColorRGB;
    if (lightingMode == 0)
    {
        finalColorRGB = computeParticleDiffuseLighting(normal, fragPos, baseColor);
    }
    else
    {
        // lightingMode >= 1 => do Phong as an example
        finalColorRGB = computeParticlePhongLighting(normal, viewDir, fragPos, baseColor);
    }

    // 6) Fade alpha over time: alpha goes from `legacyOpacity` at t=0 to 0 at t=1.
    //    If smoothEdges = true, also fade near circle edge.
    float alphaBase;
    if (smoothEdges)
    {
        float edgeFactor = 1.0 - distSquared;// 1.0 in center, 0.0 at edge
        alphaBase = edgeFactor * (legacyOpacity - lifetimePercentageToFragment);
    }
    else
    {
        // Straight fade from alpha=legacyOpacity at t=0 to alpha=0 at t=1
        alphaBase = legacyOpacity - lifetimePercentageToFragment;
    }

    // Clamp alpha so it never becomes negative or above 1.0
    float alpha = clamp(alphaBase, 0.0, 1.0);

    // 7) Output final RGBA color
    finalColor = vec4(finalColorRGB, alpha);
}
