// Tone mapping functions
vec3 Uncharted2Tonemap(vec3 x) {
    float A=0.15;
    float B=0.50;
    float C=0.10;
    float D=0.20;
    float E=0.02;
    float F=0.30;
    return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F))-E/F;
}

vec3 toneMapping(vec3 color) {
    vec3 curr=Uncharted2Tonemap(color*2.0);
    vec3 whiteScale=1.0/Uncharted2Tonemap(vec3(11.2));
    return curr*whiteScale;
}

// Smooth noise
float noise(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7)))*43758.5453);
}

float smoothNoise(vec2 p) {
    vec2 i=floor(p);
    vec2 f=fract(p);
    f=f*f*(3.0-2.0*f);
    return mix(
    mix(noise(i+vec2(0.0, 0.0)), noise(i+vec2(1.0, 0.0)), f.x),
    mix(noise(i+vec2(0.0, 1.0)), noise(i+vec2(1.0, 1.0)), f.x),
    f.y);
}

// Shadow Calculation pattern
float ShadowCalculation(sampler2D shadowMap, vec4 fragPosLightSpace, float bias) {
    vec3 projCoords=fragPosLightSpace.xyz/fragPosLightSpace.w;
    projCoords=projCoords*0.5+0.5;

    if (projCoords.x<0.0||projCoords.x>1.0||projCoords.y<0.0||projCoords.y>1.0||projCoords.z<0.0||projCoords.z>1.0){
        return 0.0;
    }

    float closestDepth=texture(shadowMap, projCoords.xy).r;
    float currentDepth=projCoords.z;

    float shadow=0.0;
    vec2 texelSize=1.0/textureSize(shadowMap, 0);
    int samples=3;// or 1 for less complexity
    for (int x=-samples;x<=samples;x++){
        for (int y=-samples;y<=samples;y++){
            float pcfDepth=texture(shadowMap, projCoords.xy+vec2(x, y)*texelSize).r;
            shadow += (currentDepth - bias > pcfDepth) ? 1.0 : 0.0;
        }
    }
    shadow/=float((samples*2+1)*(samples*2+1));
    return shadow;
}

// Phong lighting template
vec3 computePhongLighting(vec3 normal, vec3 viewDir, vec3 fragPos, vec3 diffuseColor, vec3 ambientColor, vec3 lightPositions[10], vec3 lightColors[10], float lightStrengths[10], bool phongShading) {
    vec3 ambient=ambientColor*diffuseColor;
    vec3 diffuse=vec3(0.0);
    vec3 specular=vec3(0.0);
    vec3 specColor=vec3(1.0);

    for (int i=0;i<10;i++){
        vec3 lightDir=normalize(lightPositions[i]-fragPos);
        float diff=max(dot(normal, lightDir), 0.0);
        diffuse+=diff*diffuseColor*lightColors[i]*lightStrengths[i];

        if (phongShading){
            vec3 reflectDir=reflect(-lightDir, normal);
            float spec=pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
            specular+=specColor*lightColors[i]*spec*lightStrengths[i];
        }
    }
    return ambient+diffuse+specular;
}
