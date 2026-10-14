"""Render an exact-period shader animation and encode GIF (no reference image).
Usage: python export_animation.py --size 960 --supersample 2 --fps 25
"""
from pathlib import Path
import argparse,subprocess,time,json
import numpy as np
from PIL import Image,ImageSequence
import imageio_ffmpeg
from render import Renderer,ROOT


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--size',type=int,default=960)
    ap.add_argument('--supersample',type=int,default=2)
    ap.add_argument('--fps',type=int,default=25)
    ap.add_argument('--duration',type=float,default=8)
    args=ap.parse_args()
    out=ROOT/'output';out.mkdir(exist_ok=True)
    scratch=ROOT/'.cache/export';scratch.mkdir(parents=True,exist_ok=True)
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    size=args.size;hi=size*args.supersample;count=round(args.duration*args.fps)
    master=scratch/'master.mkv'
    errors=open(scratch/'encode.log','w')
    master_cmd=[ff,'-y','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{size}x{size}','-r',str(args.fps),'-i','pipe:0','-an','-c:v','ffv1','-level','3','-pix_fmt','bgr0','-threads','2',str(master)]
    video_cmd=[ff,'-y','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{hi}x{hi}','-r',str(args.fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(out/'black_hole.mp4')]
    encoder=subprocess.Popen(master_cmd,stdin=subprocess.PIPE,stderr=errors)
    video=subprocess.Popen(video_cmd,stdin=subprocess.PIPE,stderr=errors)
    renderer=Renderer(hi)
    t0=time.time();first=None;last=None
    try:
        for i in range(count):
            phase=i/count*8.0
            frame=renderer.frame(phase)
            video.stdin.write(frame.tobytes())
            small=frame.resize((size,size),Image.Resampling.LANCZOS)
            encoder.stdin.write(small.tobytes())
            if i==0:
                first=np.asarray(small).copy();small.save(out/'black_hole_poster.png')
            if i==count-1:last=np.asarray(small).copy()
            if i%25==0 or i==count-1:
                print(f'Rendering {i+1}/{count}  ·  {time.time()-t0:.1f}s',flush=True)
    finally:
        encoder.stdin.close();video.stdin.close()
    if encoder.wait()!=0 or video.wait()!=0:
        raise RuntimeError('Video encoding failed; see .cache/export/encode.log')
    end=np.asarray(renderer.frame(8).resize((size,size),Image.Resampling.LANCZOS))
    loop_exact=int(np.max(np.abs(end.astype(int)-first.astype(int))))
    print('Palette analysis…',flush=True)
    def run(cmd):
        subprocess.run([ff,'-y','-loglevel','warning']+cmd,check=True,stderr=errors)
    palette=scratch/'palette.png'
    run(['-i',str(master),'-vf','palettegen=max_colors=256:stats_mode=full:reserve_transparent=1','-frames:v','1','-update','1',str(palette)])
    print('GIF quantization…',flush=True)
    run(['-i',str(master),'-i',str(palette),'-lavfi','paletteuse=dither=sierra2_4a:diff_mode=rectangle','-loop','0','-gifflags','+transdiff',str(out/'black_hole.gif')])
    with Image.open(out/'black_hole.gif') as gif:
        decoded=np.asarray(gif.convert('RGB'))
        info=dict(size=list(gif.size),frames=gif.n_frames,loop=gif.info.get('loop'),duration_ms=sum(f.info.get('duration',0) for f in ImageSequence.Iterator(gif)))
    info.update(shader_period_endpoint_max_error=loop_exact,first_frame_quantization_rmse=float(np.sqrt(np.mean((decoded.astype(float)-first.astype(float))**2))),gif_bytes=(out/'black_hole.gif').stat().st_size,render_size=hi,frame_rate=args.fps,render_seconds=round(time.time()-t0,2))
    (out/'validation.json').write_text(json.dumps(info,indent=2))
    errors.close()
    print(json.dumps(info,indent=2),flush=True)
    print('Done:',out/'black_hole.gif',flush=True)

if __name__=='__main__':main()
