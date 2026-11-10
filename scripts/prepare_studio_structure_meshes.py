"""Extract whole reference units from the pinned T1 graphics export, without CAD."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
from prepare_studio_part_meshes import prepare

SOURCE_GEOMETRY_SHA256='ce7224fea5bd1a911868df777fe48cd853c60de2603b81d175c0c5cc9f03cc34'


def build(model_path, output):
    model_path,output=Path(model_path),Path(output)
    model=json.loads(model_path.read_text(encoding='utf-8'))
    binary=(model_path.parent/'geometry.bin').read_bytes()
    if (model['geometry_sha256']!=SOURCE_GEOMETRY_SHA256
            or hashlib.sha256(binary).hexdigest()!=SOURCE_GEOMETRY_SHA256):
        raise ValueError('Source checksum mismatch')
    index_path=output/'index.json';index=json.loads(index_path.read_text(encoding='utf-8'))
    # Native part coordinates retained for profiles and the measured corner datum.
    for code,node in {'EG-0113':1050,'EG-0500/1':1146,'EG-0500/2':1170,
                      '410429':43,'B1930':1194,'B1121':1202,'W0968Z':1586}.items():
        r=next(e for e in model['elements'] if e['node_id']==node)
        positions=array('f');positions.frombytes(binary[r['offset']:r['offset']+r['floats']*4])
        normals=array('f');normals.frombytes(binary[r['offset']+r['floats']*4:r['offset']+r['floats']*8])
        bounds=[min(positions[k::3]) for k in range(3)]+[max(positions[k::3]) for k in range(3)]
        mesh=dict(schema='rockpro.part-mesh/1',units='m',frame='source.local',display_only=True,
            frame_status='reference_native_coordinates',source_geometry_sha256=model['geometry_sha256'],
            node_ids=[node],bounds_m=bounds,elements=[dict(positions=list(positions),normals=list(normals),materials=r['materials'])])
        data=json.dumps(mesh,separators=(',',':')).encode();file=code.replace('/','-')+'.mesh.json'
        (output/file).write_bytes(data)
        index['images'][code]['mesh']=dict(file=file,sha256=hashlib.sha256(data).hexdigest(),
            scope='structural_reference_native_coordinates',source_geometry_sha256=model['geometry_sha256'],node_ids=[node])
    index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    # Complete hinge (both mounting halves) and complete caster (all eight bodies).
    mapping={'items':[
        dict(id='270836',roots=[1226,1336],u_axis=[-1,0,0],v_axis=[0,0,1],normal=[0,1,0],mounting_plane_m=.5),
        dict(id='17251S',roots=[192,78],u_axis=[1,0,0],v_axis=[0,0,1],normal=[0,-1,0],mounting_plane_m=0),
        dict(id='source-caster-epson',roots=[1552],u_axis=[1,0,0],v_axis=[0,-1,0],normal=[0,0,-1],mounting_plane_m=.018)]}
    temp=output/'structure-mapping.json';temp.write_text(json.dumps(mapping),encoding='utf-8')
    prepare(model_path,temp,output)
    # Closure anchors use the source body rim (300 mm), not the centre of the
    # full bounding box. These are asymmetric halves; centring them on the seam
    # incorrectly raises the upper part into the top edge profile.
    index=json.loads(index_path.read_text(encoding='utf-8'))
    for spec in mapping['items']:
        if spec['id'] not in ('270836','17251S'):continue
        zs=[]
        for row in model['elements']:
            if row['root_id'] not in spec['roots']:continue
            p=array('f');p.frombytes(binary[row['offset']:row['offset']+row['floats']*4]);m=row['matrix']
            zs.extend(sum(m[2+4*j]*p[i+j] for j in range(3))+m[14] for i in range(0,len(p),3))
        shift=(min(zs)+max(zs))/2-.3
        meta=index['images'][spec['id']]['mesh'];file=output/meta['file'];mesh=json.loads(file.read_text())
        for element in mesh['elements']:
            for k in range(1,len(element['positions']),3):element['positions'][k]=round(element['positions'][k]+shift,7)
        mesh['mounting_reference']=dict(source_rim_m=.3,vertical_reference='body_rim_not_bbox_center')
        data=json.dumps(mesh,separators=(',',':')).encode();file.write_bytes(data);meta['sha256']=hashlib.sha256(data).hexdigest()
    index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model');p.add_argument('output');a=p.parse_args();build(a.model,a.output)
