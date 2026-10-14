#version 330
// GPU-only optical map. Unit Schwarzschild radius; no imported image or LUT.
uniform vec2 uResolution;
uniform vec2 uCenter;
uniform float uTilt;
uniform float uScale;
uniform float uInclination;
uniform float uInner;
layout(location=0) out vec4 map0;
layout(location=1) out vec4 map1;
layout(location=2) out vec4 map2;

vec3 acceleration(vec3 p, float h2) {
    float r2 = dot(p,p);
    return -1.5 * h2 * p / (r2*r2*sqrt(r2));
}
void main() {
    vec2 p=(gl_FragCoord.xy-uCenter*uResolution)/uResolution.y;
    float c=cos(uTilt), s=sin(uTilt);
    p=mat2(c,-s,s,c)*p*uScale;
    // Image-directed compression of the lower lensed image around the
    // critical curve. This is an artistic fit, not an exact Kerr metric.
    float b=length(p);
    float w=smoothstep(0.3,1.5,-p.y)*(1.0-smoothstep(5.0,7.0,b));
    float critical=2.598;
    if(b>critical) p*= (critical+(b-critical)*(1.0+0.30*w))/b;
    const float observer=80.0;
    vec3 origin=observer*vec3(0.0,sin(uInclination),cos(uInclination));
    vec3 forward=-normalize(origin);
    vec3 right=vec3(1.0,0.0,0.0);
    vec3 up=normalize(cross(right,forward));
    origin+=p.x*right+p.y*up;
    vec3 v=forward;
    float h2=dot(cross(origin,v),cross(origin,v));
    vec3 pos=origin;
    map0=vec4(0.0); map1=vec4(0.0); map2=vec4(0.0);
    int hits=0;
    for(int i=0;i<540;i++) {
        float r=length(pos);
        if(r<1.015) break;
        if(r>85.0 && dot(pos,v)>0.0) break;
        float dt=clamp(r*0.052,0.012,3.0);
        // Kick-drift-kick integrator for the central null-geodesic force.
        vec3 a=acceleration(pos,h2);
        vec3 halfv=v+a*dt*0.5;
        vec3 next=pos+halfv*dt;
        vec3 nextv=halfv+acceleration(next,h2)*dt*0.5;
        if(pos.y*next.y<0.0) {
            float f=pos.y/(pos.y-next.y);
            vec3 hit=mix(pos,next,f);
            float rr=length(hit.xz);
            if(rr>uInner && rr<34.0) {
                vec4 data=vec4(rr,atan(hit.z,hit.x),abs(nextv.y),1.0);
                if(hits==0) map0=data;
                if(hits==1) map1=data;
                if(hits==2) map2=data;
                hits++;
                if(hits>=3) break;
            }
        }
        pos=next; v=nextv;
    }
}
