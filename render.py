"""Pure shader renderer: procedural GLSL -> GPU framebuffers -> PNG/GIF.
The supplied reference image is NOT read, uploaded, traced, or composited here.
"""
from pathlib import Path
import argparse,json,time,os
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE','1')
import moderngl
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent
VERT='''#version 330
in vec2 in_pos;
void main(){gl_Position=vec4(in_pos,0.0,1.0);}
'''
DEFAULT=dict(center=[0.5152,0.4529],tilt=0.2157,scale=27.50,inclination=0.072,inner=1.51)
class Renderer:
    def __init__(self,size=960,params=None):
        self.size=size;self.params=DEFAULT| (params or {})
        self.ctx=moderngl.create_standalone_context(backend='egl')
        self.buf=self.ctx.buffer(np.array([-1,-1, 3,-1, -1,3],dtype='f4').tobytes())
        self.maps=[self.ctx.texture((size,size),4,dtype='f4') for _ in range(3)]
        for tex in self.maps:
            tex.filter=(moderngl.NEAREST,moderngl.NEAREST)
            tex.repeat_x=False;tex.repeat_y=False
        self.geo_fbo=self.ctx.framebuffer(self.maps)
        self.hdr_tex,self.hdr_fbo=self.target(size,'f2')
        self.final_tex,self.final_fbo=self.target(size,'f1')
        self.blooms=[(self.target(max(8,size//div),'f2'),self.target(max(8,size//div),'f2')) for div in [2,4,12,24]]
        self.geometry=self.make_program('geometry.frag')
        self.emission=self.make_program('emission.frag')
        self.blur=self.make_program('blur.frag')
        self.composite=self.make_program('composite.frag')
        self.make_geometry()
    def target(self,size,dtype):
        tex=self.ctx.texture((size,size),4,dtype=dtype)
        tex.filter=(moderngl.LINEAR,moderngl.LINEAR);tex.repeat_x=False;tex.repeat_y=False
        return tex,self.ctx.framebuffer([tex])
    def make_program(self,name):
        p=self.ctx.program(vertex_shader=VERT,fragment_shader=(ROOT/'shaders'/name).read_text())
        v=self.ctx.simple_vertex_array(p,self.buf,'in_pos')
        return p,v
    def uniform(self,p,name,value):
        if name in p:p[name].value=value
    def common(self,p,t=0):
        self.uniform(p,'uResolution',(self.size,self.size));self.uniform(p,'uTime',t%8.0)
        self.uniform(p,'uCenter',self.params['center']);self.uniform(p,'uTilt',self.params['tilt'])
    def make_geometry(self):
        t=time.time();p,v=self.geometry
        self.geo_fbo.use();self.common(p)
        for key in ('scale','inclination','inner'):
            self.uniform(p,'u'+key.title(),self.params[key])
        v.render(moderngl.TRIANGLES);self.ctx.finish()
        print(f'Geometry: {time.time()-t:.2f}s',flush=True)
    def frame(self,t=0.0):
        p,v=self.emission;self.hdr_fbo.use();self.common(p,t)
        for i,tex in enumerate(self.maps):
            tex.use(i);self.uniform(p,f'uMap{i}',i)
        v.render(moderngl.TRIANGLES)
        p,v=self.blur;self.uniform(p,'uSource',0)
        source=self.hdr_tex
        for (tex0,fbo0),(tex1,fbo1) in self.blooms:
            w=tex0.size[0]
            self.uniform(p,'uResolution',(w,w))
            fbo0.use();source.use(0);self.uniform(p,'uDirection',(1.0/w,0.0));v.render(moderngl.TRIANGLES)
            fbo1.use();tex0.use(0);self.uniform(p,'uDirection',(0.0,1.0/w));v.render(moderngl.TRIANGLES)
            source=tex1
        p,v=self.composite;self.final_fbo.use();self.common(p,t)
        self.hdr_tex.use(0);self.uniform(p,'uEmission',0)
        for i,(_, (tex,fbo)) in enumerate(self.blooms):
            tex.use(i+1);self.uniform(p,f'uBloom{i}',i+1)
        v.render(moderngl.TRIANGLES)
        a=self.final_fbo.read(components=3,alignment=1)
        return Image.frombytes('RGB',(self.size,self.size),a).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--size',type=int,default=960);ap.add_argument('--output',default='renders/test.png');ap.add_argument('--params',default=None);ap.add_argument('--time',type=float,default=0)
    args=ap.parse_args();params=json.loads(args.params) if args.params else None
    r=Renderer(args.size,params)
    t=time.time();im=r.frame(args.time);p=ROOT/args.output;p.parent.mkdir(parents=True,exist_ok=True);im.save(p)
    print('Frame:',time.time()-t,'Saved',p,flush=True)
if __name__=='__main__':main()
