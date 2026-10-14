# glsl-black-hole — a pure-GLSL, *Interstellar*-style black hole

**[中文说明 / Chinese README](README_zh.md)** · **[▶ Live demo (WebGL 2)](https://sayed1145.github.io/glsl-black-hole/)** · [Implementation & validation report (zh)](report/报告.md)

<p align="center">
  <img src="output/black_hole_poster.png" width="640" alt="Procedural black hole rendered entirely in GLSL: warm accretion disk bent above and below the shadow, thin photon ring, cold lens scatter, sparse star field">
</p>

Gravitational lensing, a warm accretion disk folded over and under the shadow, a thin photon ring, cinematic lens scatter and a star field — all computed in **four fragment shaders (290 lines of GLSL)** plus one small fitted radiance table. No textures, no HDRI, no image is ever read at render time. The whole thing also runs in the browser as a **single self-contained HTML file**.

> 📺 A 6-minute Chinese video walks through the physics and the code (Bilibili link will be added here after release).

## Highlights

- **Light bending** – rays are traced from the camera through a Schwarzschild-type central force (`a = -1.5 h² r⃗ / r⁵`, units `r_s = 1`) with a kick–drift–kick integrator; up to three disk crossings per pixel are recorded, which is what produces the primary image, the upper "lifted" far side and the thin secondary ring. Rays with impact parameter below the critical value `b_c = 3√3/2 · r_s ≈ 2.598 r_s` fall in — that circle is the black hole's shadow (the image of the photon sphere at `1.5 r_s`).
- **Procedural disk** – domain-warped fBm noise, radially stretched into filaments; three fitted 18-node RGB radial radiance curves; warm-colour constraint and outer fall-off; grazing-angle foreground boost; secondary-image absorption; anti-aliased thin ring.
- **Cinematic composite** – four-level floating-point bloom (separable blur), warm highlight mapping, cold blue lens scatter, sparse procedural stars, light vignette.
- **8-second seamless loop** – every time term is periodic; frame `t = 0` and `t = 8` are bit-identical (max channel error 0).
- **Two front-ends** – an offline Python/[moderngl](https://github.com/moderngl/moderngl) exporter (EGL, works headless with Mesa llvmpipe) and a dependency-free **WebGL 2** viewer with pause/scrub/speed/quality controls.

## What it is *not*

This is a **visual fit, not a physics simulation**. It is a non-rotating (Schwarzschild-like) lensing model; there is **no spin, no Doppler beaming, no gravitational redshift**. The compression of the lower image is a screen-space artistic adjustment, and the blue scatter is a lens look — the shadow does not glow by itself. See the [report](report/报告.md) for the full list of limitations and the validation data.

## Quick start

### 1. No install: open the viewer

Open [`output/black_hole_live.html`](output/black_hole_live.html) in any browser with WebGL 2 and `EXT_color_buffer_float` (Chrome/Edge/Firefox desktop; most recent mobile browsers). Or use the hosted copy: **https://sayed1145.github.io/glsl-black-hole/**

Space = pause/play · drag the timeline · change speed · pick 720 / 1080 / 1920 quality (1920 shows the finest ring and filament detail).

### 2. Render / export from Python

Python 3.10+, an EGL / OpenGL 3.3 capable environment (on Linux without a GPU install `libegl1` and `libgl1-mesa-dri`; the scripts default to `LIBGL_ALWAYS_SOFTWARE=1`).

```bash
python -m pip install -r requirements.txt
python render.py --size 1920 --output output/still.png --time 0          # one frame
python export_animation.py --size 960 --supersample 2 --fps 25 --duration 8   # GIF/MP4 loop
python build_viewer.py                                                  # rebuild output/black_hole_live.html after editing shaders
python fit_profiles.py --reference /path/to/reference.png               # optional: re-fit the radial curves (needs SciPy)
python make_report.py --kind black_hole                                 # optional: regenerate the .docx report
```

## Repository layout

```
shaders/
  geometry.frag    ray bending + disk intersections (rebuilt only when the camera/resolution changes)
  emission.frag    procedural disk radiance, filaments, ring, secondary-image absorption
  blur.frag        separable blur for the 4-level bloom
  composite.frag   tone mapping, lens scatter, stars, vignette
  radiance.glsl    fitted radial radiance curves (3 × 18 RGB nodes)
render.py              Renderer class: offscreen EGL context, multi-pass pipeline → PNG
export_animation.py    8-second loop → GIF / MP4 (Lanczos downscale, palette + Sierra dithering)
build_viewer.py        inlines the shaders into viewer_template.html → output/black_hole_live.html
fit_profiles.py        optional offline calibration of the radial curves (the only script that reads a reference image)
make_report.py         optional .docx report generator
radial_profiles.json   calibration output
output/                black_hole_live.html, black_hole_poster.png, validation.json
report/                报告.md, 黑洞_实现与验证报告.docx, rendered.jpg
```

The 20 MiB GIF and the 1920×1920 MP4 described in the report are **not** committed here — regenerate them with `export_animation.py` or watch the video. The square reference picture used for calibration is also not redistributed (its copyright status is unclear); `fit_profiles.py` accepts any reference image you supply.

## Rendering pipeline

1. **geometry.frag** – For every pixel a ray leaves the camera and is integrated through the central force field. Each crossing of the disk plane (up to three) stores radius, azimuth and incidence data in floating-point render targets.
2. **emission.frag** – At each crossing, periodic procedural noise and layered fBm (`fbm(p + fbm(p))` domain warping) are stretched radially into filaments; the fitted radiance curves give colour and brightness; grazing-angle boost, secondary-image absorption and an anti-aliased ring are added. The camera is fixed — the motion comes from the flow pattern and local brightness evolving with different phases, all with an exact 8 s period.
3. **blur.frag** – Four bloom levels (÷2, ÷4, ÷12, ÷24) with separable convolution.
4. **composite.frag** – Warm highlight mapping, cold lens scatter, sparse stars, edge darkening.
5. **Export** – render at 1920×1920, Lanczos down to 960×960, 256-colour palette with Sierra dithering for GIF; MP4 keeps the full gradient range.

## Validation (from `output/validation.json`)

| check | result |
|---|---|
| loop | 200 frames · 40 ms · 8000 ms · `loop = 0` |
| shader output at t = 0 vs t = 8 | max channel error **0** |
| mean change between neighbouring frames / across the loop seam | 2.35 / 2.37 (of 255) — no seam jump |
| first-frame GIF quantisation RMSE | 1.18 / 255 (encoding error, not similarity to the reference) |
| WebGL 2 test (Chromium) | shader compile passed · `gl_error = 0` · pause/play/reset/quality OK |

## References

- O. James, E. von Tunzelmann, P. Franklin, K. S. Thorne, *Gravitational lensing by spinning black holes in astrophysics, and in the movie Interstellar*, Class. Quantum Grav. 32 (2015) 065001 — [arXiv:1502.03808](https://arxiv.org/abs/1502.03808)
- J.-P. Luminet, *Image of a spherical black hole with thin accretion disk*, A&A 75 (1979) 228
- E. Bruneton, *A Real-time High-quality Black Hole Shader* (2020) — https://ebruneton.github.io/black_hole_shader/
- R. Antonelli, *starless* — Schwarzschild ray tracer and the `-1.5 h² r⃗ / r⁵` geodesic form — https://rantonels.github.io/starless/
- I. Quilez, *Domain Warping* — https://iquilezles.org/articles/warp/ ; *The Book of Shaders*, ch. 13 (fBm)
- Event Horizon Telescope Collaboration, *First M87 EHT Results I*, ApJL 875 L1 (2019)

These were used as study material only; the shaders, the fitting and the export pipeline in this repository are original implementations and contain no assets or code from the sites above.

## License

[MIT](LICENSE) © 2026 sayed1145
