"""Build source-bound display meshes. Visual frames never approve CAD mounting."""
import argparse
from array import array
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

# Explicit display normals in the saved source's world axes; no SKU mounting claim.
NORMALS = {'H7159':(-1,0,0), 'H7165/10Z':(0,-1,0), 'H2026':(0,-1,0),
 '17251S_1':(0,-1,0),'17251S_2':(0,-1,0),'27083_1':(0,1,0),'27083_2':(0,1,0),
 '2643_1':(0,1,0),'2643_2':(0,1,0),'2605_1':(0,-1,0),'2605_2':(0,-1,0),
 '37033':(0,0,-1),'37034':(0,0,-1),'38081':(0,0,1),'W0962':(0,0,1),'W0968z':(0,0,1),
 'F1692':(0,0,-1),'3453':(0,0,1),'L905-915_1':(0,-1,0),'L905-915_2':(0,-1,0)}

def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sha(raw):return hashlib.sha256(raw).hexdigest()

def compile_mesh(model,raw,node_ids,normal=None,code=''):
    if sha(raw)!=model['geometry_sha256']:raise ValueError('Source mesh checksum mismatch')
    rows=[r for r in model['elements'] if r['node_id'] in node_ids]
    if not rows or {r['node_id'] for r in rows}!=set(node_ids):raise ValueError('Missing selected source nodes')
    world=[]
    for row in rows:
        size=row['floats'];offset=row['offset']
        if type(size) is not int or size<=0 or size%9 or offset<0 or offset+size*8>len(raw):raise ValueError('Invalid triangle buffer')
        p=array('f');p.frombytes(raw[offset:offset+size*4]);n=array('f');n.frombytes(raw[offset+size*4:offset+size*8]);m=row['matrix']
        if len(m)!=16 or not all(math.isfinite(x) for x in m):raise ValueError('Invalid source transform')
        points=[[sum(m[k+4*j]*p[i+j] for j in range(3))+m[12+k] for k in range(3)] for i in range(0,size,3)]
        normals=[[sum(m[k+4*j]*n[i+j] for j in range(3)) for k in range(3)] for i in range(0,size,3)]
        if not all(math.isfinite(x) for pt in points+normals for x in pt):raise ValueError('Nonfinite source geometry')
        world.append((row,points,normals))
    pts=[p for _,ps,_ in world for p in ps]
    if normal is None:
        extent=[max(p[k] for p in pts)-min(p[k] for p in pts) for k in range(3)]
        normal=tuple(int(k==min(range(3),key=lambda j:extent[j])) for k in range(3))
    v=[0,0,1] if not normal[2] else [0,1,0];u=cross(v,normal);axes=[u,v,normal]
    projected=[[[dot(p,a) for a in axes] for p in ps] for _,ps,_ in world]
    allpts=[p for ps in projected for p in ps];lo=[min(p[k] for p in allpts) for k in range(3)];hi=[max(p[k] for p in allpts) for k in range(3)]
    # Dominant planar face is a visual reference, never a cutout/mounting definition.
    planes=defaultdict(float)
    for ps in projected:
        for i in range(0,len(ps),3):
            a,b,c=ps[i:i+3];ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)];area=cross(ab,ac)
            if max(a[2],b[2],c[2])-min(a[2],b[2],c[2])<1e-6:planes[round((a[2]+b[2]+c[2])/3,6)]+=abs(area[2])/2
    plane=min(lo[2],hi[2]) if code in ('37033','37034','F1692') else (max(planes,key=planes.get) if planes else lo[2])
    center=[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,plane];elements=[]
    for (row,ps,ns),projected_ps in zip(world,projected):
        if sum(g['count'] for g in row['materials'])!=len(ps):raise ValueError('Material ranges do not cover triangles')
        elements.append(dict(positions=[round(p[k]-center[k],7) for p in projected_ps for k in range(3)],
            normals=[round(dot(n,a),7) for n in ns for a in axes],materials=row['materials']))
    return dict(schema='rockpro.part-mesh/1',units='m',frame='mount.local_uvn',elements=elements,
        display_only=True,frame_status='unconfirmed_visual_frame',source_binding=model['source_binding'],
        source_geometry_sha256=model['geometry_sha256'],node_ids=node_ids,
        bounds_m=[lo[k]-center[k] for k in range(3)]+[hi[k]-center[k] for k in range(3)])

def prepare(package):
    package=Path(package);catalog=json.loads((package/'catalog.json').read_text(encoding='utf-8'))
    path=package/'images/index.json';index=json.loads(path.read_text(encoding='utf-8'))
    for row in catalog['items']:
        image=index['images'][row['id']];folder=package/'models'/row['id'];model=json.loads((folder/'model.json').read_text(encoding='utf-8'))
        if model['source_binding']!=row['source_binding']:raise ValueError('Mixed source identity')
        # Match the explicitly labelled thumbnail selection. Never merge dispersed repeats.
        nodes=image['source']['node_ids'];code=row['catalog_code_raw']
        mesh=compile_mesh(model,(folder/'geometry.bin').read_bytes(),nodes,NORMALS.get(code),code)
        file=row['id']+'.mesh.json';raw=json.dumps(mesh,separators=(',',':')).encode()
        if len(raw)>16*1024*1024:raise ValueError('Display mesh exceeds route limit')
        (path.parent/file).write_bytes(raw)
        image['mesh']=dict(file=file,sha256=sha(raw),scope='source_reference_display',
            source_geometry_sha256=model['geometry_sha256'],source_binding=row['source_binding'],
            node_ids=nodes,display_body_count=len(nodes),source_body_count=len(model['elements']),bounds_m=mesh['bounds_m'],frame_status=mesh['frame_status'])
    path.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared',len(catalog['items']),'source display meshes')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package');prepare(p.parse_args().package)
