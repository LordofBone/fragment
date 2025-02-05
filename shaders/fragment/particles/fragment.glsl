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
uniform vec3 particleFadeColor;// The color we fade to if enabled
uniform bool particleFadeToColor;// True => fade color over lifetime
uniform bool smoothEdges;// True => soften particle edges

// -----------------------------------------------------------------------------
// Lighting/shading uniforms (for your custom lighting funcs)
// -----------------------------------------------------------------------------
uniform vec3 viewPosition;// Camera/world-space view position
uniform int lightingMode;// 0 => diffuse, 1 => Phong, 2 => PBR, etc.

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------
void main()
{
    // 1) Introduce a small per‐particle color variation to avoid uniform look
    vec2 localCoords = gl_PointCoord;
    float colorVariation = generateRandomValue(localCoords, particleIDOut);

    // Scale the incoming fragColor by ±10%
    vec3 variedColor = fragColor * (0.9 + 0.2 * colorVariation);

    // 2) Fade color over time if desired:
    //    at lifetimePercentage=0 => use variedColor
    //    at lifetimePercentage=1 => use particleFadeColor
    vec3 baseColor;
    if (particleFadeToColor)
    {
        baseColor = mix(particleFadeColor, variedColor, lifetimePercentageToFragment);
    }
    else
    {
        baseColor = variedColor;
    }

    // 3) Create a spherical "billboard" by discarding texels outside a circle
    //    (Pretend the point sprite is a sphere in its local coords)
    //    Usually, you do (2*gl_PointCoord - 1.0) to map [0..1]->[-1..1].
    //    Found this needs to be set to 0.10 to avoid clipping on some GPUs.
    vec2 centeredCoord = gl_PointCoord * 2.0 - 0.10;
    float distSquared = dot(centeredCoord, centeredCoord);

    // Discard fragments outside the circle
    if (distSquared > 1.0)
    {
        discard;// Outside the circle => kill the fragment
    }

    float z = sqrt(max(1.0 - distSquared, 0.0));
    vec3 normal = normalize(vec3(centeredCoord, z));

    // 4) Simple lighting: pick between "diffuse" or "Phong" for demonstration.
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

    // 5) Fade out alpha over time as well, respecting "legacyOpacity" as the
    //    starting alpha.  If smoothEdges=true, fade near the particle's edge.
    float alphaBase;
    if (smoothEdges)
    {
        // Edge factor => 1.0 in the center, 0.0 at edge of the circle
        float edgeFactor = 1.0 - distSquared;
        alphaBase = edgeFactor * (legacyOpacity - lifetimePercentageToFragment);
    }
    else
    {
        // Straight fade from alpha=legacyOpacity at t=0 to alpha=0 at t=1
        alphaBase = legacyOpacity - lifetimePercentageToFragment;
    }

    // 6) Clamp alpha to [0..1]
    float alpha = clamp(alphaBase, 0.0, 1.0);

    // 7) Final output
    finalColor = vec4(finalColorRGB, alpha);
}
