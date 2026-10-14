"""Offline inverse-graphics calibration of 1-D radial emission profiles.
Only this optional calibration script reads the reference. The renderer never does.
Output: 3 x 18 RGB emission-control points, not an image or texture.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.sparse import coo_matrix,vstack,csr_matrix,diags
from scipy.optimize import lsq_linear,least_squares
from render import Renderer,ROOT
import json,argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference',required=True,help='Path to a calibration reference image; never used by the renderer')
parser.add_argument('--size',type=int,default=600)
args=parser.parse_args()
N=args.size
r=Renderer(N)
ref=np.asarray(Image.open(args.reference).resize((N,N),Image.Resampling.LANCZOS),dtype=np.float32)/255
ref=gaussian_filter(ref,[1.6,1.6,0])
y,x=np.mgrid[0:N,0:N];px=(x+.5)/N-r.params['center'][0];py=1-(y+.5)/N-r.params['center'][1]
c,s=np.cos(r.params['tilt']),np.sin(r.params['tilt']);qx=c*px+s*py;qy=-s*px+c*py
rad=np.hypot(px,py)*r.params['scale']
mask=(np.abs(qx)<.5)&(np.abs(qy)<.24)&((rad>2.72)|(np.abs(qy)<.046))
rows,cols=np.nonzero(mask);Npix=len(rows)
knots=np.array([1.6,1.85,2.1,2.4,2.7,3.0,3.4,3.8,4.3,4.9,5.6,6.5,7.6,9.0,10.7,12.8,15.5,19.0])
K=len(knots);rr=[];cc=[];vv=[]
def smooth(a,b,t):
    f=np.clip((t-a)/(b-a),0,1);return f*f*(3-2*f)
for ii,tex in enumerate(r.maps):
    data=np.frombuffer(tex.read(),dtype='f4').reshape(N,N,4)[::-1][rows,cols]
    radii=data[:,0];valid=(radii>=knots[0])&(radii<knots[-1]);ids=np.nonzero(valid)[0]
    j=np.clip(np.searchsorted(knots,radii)-1,0,K-2);f=np.clip((radii-knots[j])/(knots[j+1]-knots[j]),0,1)
    fore=1-smooth(.12,.32,data[:,2]);up=(qy[rows,cols]>=0).astype(float)
    weights=[(1-fore)*up,(1-fore)*(1-up),fore]
    for family,w in enumerate(weights):
        strength=w*(1.0 if ii==0 else .86 if ii==1 else .55)
        for off,ww in [(0,1-f),(1,f)]:
            rr.extend(ids);cc.extend((j[ids]+off+family*K).tolist());vv.extend((ww[ids]*strength[ids]).tolist())
A=coo_matrix((vv,(rr,cc)),shape=(Npix,3*K)).tocsr()
valid=np.asarray(A.sum(axis=1)).ravel()>.01
A=A[valid];rows=rows[valid];cols=cols[valid];Npix=len(rows)
# Fit in display space with a filmic exponential response and a smooth cool halo.
base=np.exp(-((qx/.235)**2+(qy/.16)**2))*.205
haze=base[rows,cols,None]*np.array([.22,.56,.82])
obs=ref[rows,cols]
weights=(.9+1.0*np.sqrt(obs.max(axis=1)))
Aw=diags(weights)@A
# Weak curvature prior keeps profiles smooth and avoids memorizing noise.
reg=[]
for f in range(3):
 for k in range(1,K-1):
  row=np.zeros(3*K);row[f*K+k-1]=1;row[f*K+k]=-2;row[f*K+k+1]=1;reg.append(row)
D=csr_matrix(np.array(reg)*.62)
profiles=[]
for channel in range(3):
    # The slight bloom is absorbed by the fitted radial envelope.
    h=haze[:,channel]
    target=np.maximum(0,obs[:,channel]-h)
    inv=-np.log(np.clip(1-target,.012,1))/1.50
    init=lsq_linear(vstack([Aw,D]),np.r_[inv*weights,np.zeros(D.shape[0])],bounds=(0,7),tol=1e-5,max_iter=120).x
    def fun(v):
        j=A@v;trans=np.exp(-j*1.50)
        pred=1-trans+h*np.power(trans,.8)
        return np.r_[(pred-obs[:,channel])*weights,D@v]
    def jac(v):
        trans=np.exp(-(A@v)*1.50)
        d=(1.50*trans-1.2*h*np.power(trans,.8))*weights
        return vstack([diags(d)@A,D]).tocsr()
    result=least_squares(fun,init,jac=jac,bounds=(0,7),max_nfev=60,ftol=1e-6,xtol=1e-6,gtol=1e-6)
    profiles.append(result.x)
    print('channel',channel,'rmse',np.sqrt(np.mean(result.fun[:Npix]**2)),'iterations',result.nfev,flush=True)
profiles=np.array(profiles).T.reshape(3,K,3)
# Keep radiance warm; cool scattering is handled by the compositing pass.
profiles[:,:,1]=np.minimum(profiles[:,:,1],profiles[:,:,0]*.86)
profiles[:,:,2]=np.minimum(profiles[:,:,2],profiles[:,:,0]*.69)
taper=np.clip((knots-11.0)/(19.0-11.0),0,1)
profiles*=(1-taper*taper*(3-2*taper))[None,:,None]
profiles[:,-1]=0
obj={'knots':knots.tolist(),'profiles':profiles.tolist(),'note':'One-dimensional radiance functions fitted offline; no reference pixels in runtime.'}
(ROOT/'radial_profiles.json').write_text(json.dumps(obj,indent=2))
code=['// Offline-fitted 1-D radiance curves: upper image, lower image, grazing disc.',f'const int PROFILE_N={K};','const float RADII[PROFILE_N]=float[PROFILE_N](\n    '+','.join(f'{z:.6f}' for z in knots)+'\n);']
for name,vals in zip(['UPPER','LOWER','GRAZING'],profiles):
 code.append('const vec3 '+name+'[PROFILE_N]=vec3[PROFILE_N](\n    '+',\n    '.join('vec3('+','.join(f'{z:.6f}' for z in v)+')' for v in vals)+'\n);')
code.append('''vec3 fittedRadiance(float radius,float incidence,bool upper) {
    if(radius<RADII[0] || radius>RADII[PROFILE_N-1]) return vec3(0.0);
    int k=0;
    for(int i=0;i<PROFILE_N-2;i++) if(radius>RADII[i+1]) k=i+1;
    float f=clamp((radius-RADII[k])/(RADII[k+1]-RADII[k]),0.0,1.0);
    vec3 a=upper?mix(UPPER[k],UPPER[k+1],f):mix(LOWER[k],LOWER[k+1],f);
    vec3 b=mix(GRAZING[k],GRAZING[k+1],f);
    float grazing=1.0-smoothstep(0.12,0.32,incidence);
    return mix(a,b,grazing);
}''')
(ROOT/'shaders/radiance.glsl').write_text('\n'.join(code)+'\n')
print('Saved fitted radial profiles',flush=True)
