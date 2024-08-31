#version 430

layout(location = 0) in vec3 position;// Input particle position
layout(location = 1) in vec3 velocity;// Input particle velocity

uniform float deltaTime;// Time step between frames
uniform vec3 gravity;// Gravity vector
uniform float bounceFactor;// Factor to reduce velocity on bounce
uniform vec3 groundPlaneNormal;// Normal of the ground plane
uniform float groundPlaneHeight;// Height of the ground plane

out vec3 tf_position;// Output new position for transform feedback
out vec3 tf_velocity;// Output new velocity for transform feedback

out vec3 frag_position;// Output position to the fragment shader
out vec3 frag_velocity;// Output velocity to the fragment shader

void main() {
    // Update velocity with gravity
    vec3 newVelocity = velocity + gravity * deltaTime;

    // Update position
    vec3 newPosition = position + newVelocity * deltaTime;

    // Check for collision with the ground plane
    float distanceToGround = dot(newPosition, groundPlaneNormal) - groundPlaneHeight;
    if (distanceToGround < 0.0) {
        // Reflect the velocity vector and reduce its magnitude
        newVelocity = reflect(newVelocity, groundPlaneNormal) * bounceFactor;

        // Position the particle back to the plane level
        newPosition = newPosition - groundPlaneNormal * distanceToGround;
    }

    // Pass updated values to transform feedback outputs
    tf_position = newPosition;
    tf_velocity = newVelocity;

    // Pass values to the fragment shader
    frag_position = newPosition;
    frag_velocity = newVelocity;

    // Set the position to be passed to the next pipeline stage
    gl_Position = vec4(newPosition, 1.0);

    // Set the size of the particle
    gl_PointSize = 5.0;// Adjust this value to make particles larger
}
