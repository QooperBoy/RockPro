"""Prepare explicitly mapped reference meshes for Studio, without opening CAD.

Mapping rows require id, roots, u_axis, v_axis, normal, mounting_plane_m.
The existing raster index supplies IDs; this does not approve mounting geometry.
"""
import argparse
from array import array
import hashlib
import json
from pathlib import Path


def prepare(model_path, mapping_path, output):
    model_path, output = Path(model_path), Path(output)
    model=json.loads(model_path.read_text(encoding='utf-8'))
    raw=(model_path.parent/'geometry.bin').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=model['geometry_sha256']:
        raise ValueError('Mesh source checksum mismatch')
    index_path=output/'index.json';index=json.loads(index_path.read_text(encoding='utf-8'))
    for spec in json.loads(Path(mapping_path).read_text(encoding='utf-8'))['items']:
        rows=[r for r in model['elements'] if r['root_id'] in spec['roots']]
        if not rows or spec['id'] not in index['images']:
            raise ValueError('Missing explicit mesh binding')
        axes=[spec['u_axis'],spec['v_axis'],spec['normal']]
        if any(sum(v*v for v in a)!=1 for a in axes) or any(sum(a[k]*b[k] for k in range(3)) for i,a in enumerate(axes) for b in axes[i+1:]):
            raise ValueError('Orthonormal mounting frame required')
        cross=[axes[0][1]*axes[1][2]-axes[0][2]*axes[1][1],axes[0][2]*axes[1][0]-axes[0][0]*axes[1][2],axes[0][0]*axes[1][1]-axes[0][1]*axes[1][0]]
        if sum(cross[k]*axes[2][k] for k in range(3))!=1:
            raise ValueError('Mounting frame must not reflect catalog geometry')
        elements=[];all_points=[]
        for row in rows:
            positions=array('f');positions.frombytes(raw[row['offset']:row['offset']+row['floats']*4])
            normals=array('f');normals.frombytes(raw[row['offset']+row['floats']*4:row['offset']+row['floats']*8])
            matrix=row['matrix'];pts=[];ns=[]
            for i in range(0,len(positions),3):
                world=[sum(matrix[k+4*j]*positions[i+j] for j in range(3))+matrix[12+k] for k in range(3)]
                normal=[sum(matrix[k+4*j]*normals[i+j] for j in range(3)) for k in range(3)]
                pts.append([sum(world[k]*a[k] for k in range(3)) for a in axes])
                ns.extend(round(sum(normal[k]*a[k] for k in range(3)),7) for a in axes)
            all_points.extend(pts);elements.append(dict(points=pts,normals=ns,materials=row['materials']))
        center=[(min(p[k] for p in all_points)+max(p[k] for p in all_points))/2 for k in (0,1)]+[spec['mounting_plane_m']]
        for e in elements:
            e['positions']=[round(p[k]-center[k],7) for p in e.pop('points') for k in range(3)]
        filename=spec['id'].replace('/','-')+'.mesh.json'
        if '/' in filename or '\\' in filename or '..' in filename:raise ValueError('Invalid mesh filename')
        data=json.dumps(dict(schema='rockpro.part-mesh/1',units='m',frame='mount.local_uvn',elements=elements),separators=(',',':')).encode()
        (output/filename).write_bytes(data)
        index['images'][spec['id']]['mesh']=dict(file=filename,sha256=hashlib.sha256(data).hexdigest(),
            source_geometry_sha256=model['geometry_sha256'],roots=spec['roots'],scope='reference_geometry_not_approved_mount')
    index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model');p.add_argument('mapping');p.add_argument('output')
    a=p.parse_args();prepare(a.model,a.mapping,a.output)
