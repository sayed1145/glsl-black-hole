#version 330
// Procedural plasma. All noise is evaluated algebraically; no image textures.
uniform vec2 uResolution;
uniform float uTime;
uniform vec2 uCenter;
uniform float uTilt;
uniform sampler2D uMap0;
uniform sampler2D uMap1;
uniform sampler2D uMap2;
out vec4 fragColor;
const float TAU=6.28318530718;

float hash21(vec2 p) {
    vec3 q=fract(vec3(p.xyx)*vec3(0.1031,0.1030,0.0973));
    q+=dot(q,q.yzx+33.33);
    return fract((q.x+q.y)*q.z);
}
float noiseP(vec2 p,float period) {
    vec2 i=floor(p),f=fract(p);
    f=f*f*(3.0-2.0*f);
    vec2 i0=vec2(i.x,mod(i.y,period));
    vec2 i1=vec2(i.x,mod(i.y+1.0,period));
    return mix(mix(hash21(i0),hash21(i0+vec2(1,0)),f.x),
               mix(hash21(i1),hash21(i1+vec2(1,0)),f.x),f.y);
}
float fbmP(vec2 p,float period,float footprint) {
    float n=0.0, amp=0.52;
    for(int i=0;i<5;i++) {
        float aa=1.0-smoothstep(0.65,2.1,footprint);
        n+=amp*mix(0.5,noiseP(p,period),aa);
        p*=2.0;period*=2.0;footprint*=2.0;amp*=0.49;
    }
    return n;
}
// Calibrated radial radiance only; no reference-image pixels or texture.
const int PROFILE_N=18;
const float RADII[PROFILE_N]=float[PROFILE_N](
    1.600000,1.850000,2.100000,2.400000,2.700000,3.000000,3.400000,3.800000,4.300000,4.900000,5.600000,6.500000,7.600000,9.000000,10.700000,12.800000,15.500000,19.000000
);
const vec3 UPPER[PROFILE_N]=vec3[PROFILE_N](
    vec3(0.255777,0.166983,0.130913),
    vec3(0.137799,0.112648,0.095081),
    vec3(0.264506,0.176011,0.157152),
    vec3(0.454691,0.277004,0.215472),
    vec3(0.804536,0.516623,0.372846),
    vec3(1.150769,0.757494,0.551068),
    vec3(1.673280,1.122596,0.815232),
    vec3(1.971796,1.355241,0.988191),
    vec3(1.381316,0.953994,0.710846),
    vec3(1.212427,0.769973,0.538510),
    vec3(0.632655,0.452315,0.354578),
    vec3(0.504023,0.315987,0.231414),
    vec3(0.303187,0.201846,0.163637),
    vec3(0.012821,0.011026,0.008847),
    vec3(0.001271,0.001093,0.000877),
    vec3(0.000438,0.000377,0.000303),
    vec3(0.000001,0.000000,0.000000),
    vec3(0.000000,0.000000,0.000000)
);
const vec3 LOWER[PROFILE_N]=vec3[PROFILE_N](
    vec3(0.000000,0.000000,0.000000),
    vec3(0.233461,0.154232,0.134631),
    vec3(0.392270,0.241803,0.181831),
    vec3(0.553336,0.335322,0.237910),
    vec3(0.720745,0.450136,0.316339),
    vec3(0.930359,0.597947,0.426111),
    vec3(1.302152,0.882694,0.646073),
    vec3(1.496130,1.043103,0.770311),
    vec3(1.466698,1.060739,0.801137),
    vec3(1.110652,0.758425,0.554937),
    vec3(0.974833,0.643935,0.452933),
    vec3(0.489304,0.319002,0.232886),
    vec3(0.459541,0.279972,0.193965),
    vec3(0.207503,0.128341,0.098463),
    vec3(0.019420,0.016701,0.013400),
    vec3(0.006035,0.005190,0.004164),
    vec3(0.002372,0.002040,0.001636),
    vec3(0.000000,0.000000,0.000000)
);
const vec3 GRAZING[PROFILE_N]=vec3[PROFILE_N](
    vec3(0.501431,0.383656,0.323421),
    vec3(0.594023,0.435577,0.352526),
    vec3(0.444722,0.360840,0.306858),
    vec3(0.530725,0.417036,0.366201),
    vec3(0.889255,0.628932,0.505206),
    vec3(1.389388,0.980254,0.755381),
    vec3(1.798031,1.323533,1.027938),
    vec3(2.046291,1.551282,1.215553),
    vec3(2.129368,1.670683,1.322172),
    vec3(1.976563,1.561564,1.261436),
    vec3(1.794290,1.370349,1.106133),
    vec3(1.308990,0.979743,0.789233),
    vec3(0.924975,0.641772,0.498919),
    vec3(0.479225,0.351105,0.285022),
    vec3(0.200028,0.149638,0.130981),
    vec3(0.054028,0.046464,0.037279),
    vec3(0.011962,0.010287,0.008254),
    vec3(0.000000,0.000000,0.000000)
);
vec3 fittedRadiance(float radius,float incidence,bool upper) {
    if(radius<RADII[0] || radius>RADII[PROFILE_N-1]) return vec3(0.0);
    int k=0;
    for(int i=0;i<PROFILE_N-2;i++) if(radius>RADII[i+1]) k=i+1;
    float f=clamp((radius-RADII[k])/(RADII[k+1]-RADII[k]),0.0,1.0);
    vec3 a=upper?mix(UPPER[k],UPPER[k+1],f):mix(LOWER[k],LOWER[k+1],f);
    vec3 b=mix(GRAZING[k],GRAZING[k+1],f);
    float grazing=1.0-smoothstep(0.12,0.32,incidence);
    return mix(a,b,grazing);
}


vec3 plasma(vec4 data) {
    float r=data.x;
    if(r<0.1) return vec3(0.0);
    float phi=data.y;
    float phase=TAU*uTime/8.0;
    float a=phi/TAU;
    float t=phase/TAU;
    float inner=1.0-smoothstep(3.5,9.0,r);
    float n0=noiseP(vec2(r*1.7,a*48.0-t*12.0),12.0);
    float n1=noiseP(vec2(r*1.7+19.6,a*48.0-t*24.0),12.0);
    float swirl=mix(n0,n1,inner*0.65);
    float finewarp=noiseP(vec2(r*5.3,a*64.0-t*32.0+r*0.3),16.0);
    float rw=r+(swirl-0.5)*0.25+(finewarp-0.5)*0.055;
    float footprint=abs(dFdx(r))+abs(dFdy(r));
    float filament=fbmP(vec2(rw*8.0,a*60.0-t*15.0+rw*0.18),15.0,footprint*8.0);
    float filament2=fbmP(vec2(rw*2.0+72.0,a*128.0-t*64.0),32.0,footprint*2.0);
    float density=pow(0.10+1.64*filament,2.25);
    density*=0.65+0.74*filament2;
    vec2 pp=(gl_FragCoord.xy-uCenter*uResolution)/uResolution.y;
    bool upper=(-sin(uTilt)*pp.x+cos(uTilt)*pp.y)>=0.0;
    float front=pow(max(0.0,sin(phi)),8.0)*(1.0-smoothstep(0.12,0.32,data.z));
    float frontBoost=1.0+1.9*front*smoothstep(6.0,9.5,r);
    float outerFade=1.0-smoothstep(11.8,15.0,r);
    return fittedRadiance(r,data.z,upper)*(density/0.84)*frontBoost*outerFade;

}
void main() {
    vec2 uv=gl_FragCoord.xy/uResolution;
    vec4 a=texture(uMap0,uv),b=texture(uMap1,uv),c=texture(uMap2,uv);
    // Grazing, cooler foreground plasma also absorbs the secondary image.
    float opacity=0.72*exp(-pow((a.x-13.0)/5.0,2.0))*(1.0-smoothstep(0.12,0.32,a.z));
    float transmission=exp(-opacity);
    vec3 col=plasma(a)+transmission*(plasma(b)*0.86+plasma(c)*0.55);
    vec2 p=(gl_FragCoord.xy-uCenter*uResolution)/uResolution.y;
    float radius=length(p)*27.5;
    vec2 q=mat2(cos(uTilt),-sin(uTilt),sin(uTilt),cos(uTilt))*p;
    col*=max(smoothstep(2.61,2.68,radius),1.0-smoothstep(0.040,0.058,abs(q.y)));
    float az=atan(q.y,q.x)/TAU;
    float stream=noiseP(vec2(radius*2.2,az*20.0-uTime/8.0*5.0),5.0);
    float silk=fbmP(vec2(radius*12.0+(stream-0.5)*0.6,az*32.0-uTime/8.0*8.0),8.0,27.5/uResolution.y*12.0);
    float arcMask=smoothstep(0.018,0.055,abs(q.y));
    col*=mix(1.0,0.58+0.84*silk,arcMask);
    float px=27.5/uResolution.y;
    float d=abs(radius-2.598);
    float ring=(1.0-smoothstep(px*0.08,px*0.76,d))*0.54;
    ring+=0.055*exp(-pow(d/(px*2.5),2.0));
    float upper=smoothstep(-0.01,0.03,p.y);
    ring*=mix(0.42,1.0,upper);
    col+=ring*vec3(1.0,0.64,0.46);
    fragColor=vec4(col,1.0);
}
