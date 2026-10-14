#version 330
uniform sampler2D uSource;
uniform vec2 uResolution;
uniform vec2 uDirection;
out vec4 fragColor;
void main() {
    vec2 uv=gl_FragCoord.xy/uResolution;
    vec3 c=texture(uSource,uv).rgb*0.14446445;
    c+=(texture(uSource,uv+uDirection*1.411765).rgb+texture(uSource,uv-uDirection*1.411765).rgb)*0.235176;
    c+=(texture(uSource,uv+uDirection*3.294118).rgb+texture(uSource,uv-uDirection*3.294118).rgb)*0.141176;
    c+=(texture(uSource,uv+uDirection*5.176471).rgb+texture(uSource,uv-uDirection*5.176471).rgb)*0.057647;
    c+=(texture(uSource,uv+uDirection*7.058824).rgb+texture(uSource,uv-uDirection*7.058824).rgb)*0.014117;
    fragColor=vec4(c,1.0);
}
