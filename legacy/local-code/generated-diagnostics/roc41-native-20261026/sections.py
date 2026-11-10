import json,sys,math
from pathlib import Path
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'geometry_dependencies'))
from shapely.geometry import Polygon
from shapely.affinity import translate
rows=json.loads((B/'inspect-prototype/inventory.json').read_text())['rows']
def section(id):
 f=next(r for r in rows if r['id']==id)['features'][0]
 segs=[]
 for c in f['curves']:
  if c['type']=='Z_CURVE2D_LINE':pts=[c['start'],c['end']]
  elif c['type']=='Z_CURVE2D_ARC':
   s,e=c['start_angle'],c['end_angle'];e=s+(e-s)%(2*math.pi)
   pts=[[c['center'][0]+c['radius']*math.cos(a),c['center'][1]+c['radius']*math.sin(a)] for a in np.linspace(s,e,100)]
  else:raise ValueError(c)
  segs.append(np.array(pts)*1000)
 points=list(segs.pop(0))
 while segs:
  options=[(np.linalg.norm(points[-1]-seg[k]),i,k) for i,seg in enumerate(segs) for k in (0,-1)]
  dist,i,k=min(options)
  if dist>0.001:raise ValueError(('unclosed',id,dist))
  seg=segs.pop(i);points.extend(seg if k==0 else seg[::-1])
 m=np.array(f['profile_parent_mm'])@np.array(f['world_mm'])
 out=np.array([[*pt,0,1] for pt in points])@m
 shape=Polygon(out[:,1:3]);print(id,'valid',shape.is_valid,'area',shape.area,'bounds',shape.bounds)
 return shape
male=section(1146);female=section(1170)
print('overlap',male.intersection(female).area,'intersection',male.intersection(female).bounds)
for dy in [-2,-1,0,1,2]:
 for dz in [0,0.2,0.5,1,2,3,4,5]:
  moved=translate(female,dy,dz);area=male.intersection(moved).area
  if area<1e-6:print('clear',dy,dz,'distance',male.distance(moved))
