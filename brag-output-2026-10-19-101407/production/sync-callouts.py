"""Match the SVG ownership markers to the Blender camera projections."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1];comp=root/'composition'
projection=root/'production/cut-video-projection.json'
if not projection.exists():projection=root/'production/cut-projection.json'
a,b=[p['points'] for p in json.loads(projection.read_text())]
def curve(v):
 x,y=v['rx'];u,w=v['apu'];return f'M {x} {y} C {x+30:.1f} {y+220:.1f}, {u+35:.1f} {w+390:.1f}, {u} {w}'
s=(comp/'film.js').read_text()
for ident,key in [('rx-point','rx'),('apu-point','apu')]:
 x,y=a[key];u,w=b[key]
 pattern=r"tl.fromTo\('#"+ident+r"',\{attr:\{cx:[\d.]+,cy:[\d.]+\}\},\{attr:\{cx:[\d.]+,cy:[\d.]+\},duration:5,ease:'none'\},10.8\);"
 replacement=f"tl.fromTo('#{ident}',{{attr:{{cx:{x},cy:{y}}}}},{{attr:{{cx:{u},cy:{w}}},duration:5,ease:'none'}},10.8);"
 s,count=re.subn(pattern,replacement,s);assert count==1,(ident,count)
s,count=re.subn(r"tl.fromTo\('#handoff-path',\{attr:\{d:'[^']+'\}\},\{attr:\{d:'[^']+'\},duration:5,ease:'none'\},10.8\);",f"tl.fromTo('#handoff-path',{{attr:{{d:'{curve(a)}'}}}},{{attr:{{d:'{curve(b)}'}},duration:5,ease:'none'}},10.8);",s);assert count==1
(comp/'film.js').write_text(s)
s=(comp/'film.template').read_text();s=re.sub(r'(id="handoff-path" d=")[^"]+',r'\g<1>'+curve(a),s)
for ident,key in [('rx-point','rx'),('apu-point','apu')]:
 x,y=a[key];s=re.sub(r'(id="'+ident+r'" cx=")[^"]+(" cy=")[^"]+',r'\g<1>'+str(x)+r'\g<2>'+str(y),s)
(comp/'film.template').write_text(s)
