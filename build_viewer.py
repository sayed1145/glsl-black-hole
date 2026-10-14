"""Bundle the actual GLSL files into one offline, dependency-free HTML viewer."""
from pathlib import Path
import json
from render import DEFAULT,ROOT

shaders={name:(ROOT/'shaders'/f'{name}.frag').read_text() for name in ['geometry','emission','blur','composite']}
html=(ROOT/'viewer_template.html').read_text().replace('/*__SHADERS__*/',json.dumps(shaders,ensure_ascii=False)).replace('/*__PARAMETERS__*/',json.dumps(DEFAULT))
(ROOT/'output').mkdir(exist_ok=True)
(ROOT/'output/black_hole_live.html').write_text(html)
print(ROOT/'output/black_hole_live.html')
