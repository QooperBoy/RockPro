"""Convert an IronCAD Web Viewer ZIP into local Three.js mesh buffers.

Reads the native export, never opens CAD or modifies ICS. Export IDs and global
poses are preserved; layers classify whole top-level assemblies together.
"""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import zipfile


def layer(name):
    name=name.lower()
    if 'wheel' in name: return 'wheels'
    if 'eg0113' in name or 'eg0500' in name: return 'profiles'
    if 'h7159' in name or 'handle' in name: return 'handles'
    if 'hinge' in name or '17251' in name: return 'closures'
    if '410429' in name or 'brace' in name or 'socket' in name: return 'corners'
    if any(s in name for s in ('base ', 'lid ', 'dno', 'wieko', 'pad')): return 'plywood'
    return 'other'


def convert(source,output,ics=None):
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    if output.exists(): raise ValueError('Use a new output directory')
    rows=[];mapping={}
    with zipfile.ZipFile(source) as archive:
        if sum(i.file_size for i in archive.infolist())>512*1024*1024: raise ValueError('Export too large')
        tree=json.loads(archive.read('tree.json'))
        def walk(node,top):
            if node.get('t')=='p':
                ident=int(node['i'])
                if ident in mapping: raise ValueError('Duplicate mesh reference')
                mapping[ident]=(node,top)
            for child in node.get('c') or []:walk(child,top)
        for top in tree['t']:walk(top,top)
        output.mkdir(parents=True)
        with (output/'geometry.bin').open('xb') as stream:
            for name in archive.namelist():
                if not name.endswith('.json') or name=='tree.json':continue
                raw=json.loads(archive.read(name));ident=int(raw['id'])
                if ident not in mapping:raise ValueError('Unmapped exported mesh')
                node,top=mapping[ident]
                vertices=raw['v'];normals=raw['n'];matrix=raw['p']
                if not vertices or len(vertices)%9 or len(normals)!=len(vertices) or len(matrix)!=16:
                    raise ValueError('Unsupported mesh structure')
                if any(not math.isfinite(x) for x in vertices+normals+matrix):raise ValueError('Nonfinite mesh')
                if sum(g['t'] for g in raw['c'])!=len(vertices)//3:raise ValueError('Material ranges mismatch')
                offset=stream.tell();buffer=array('f',vertices+normals);buffer.tofile(stream)
                materials=[]
                for group in raw['c']:
                    bgr=int(group['c'],16);rgb=((bgr&255)<<16)|(bgr&0xff00)|((bgr>>16)&255)
                    materials.append(dict(count=group['t'],color=rgb))
                rows.append(dict(id=ident,node_id=node['id'],root_id=top['id'],name=top['n'],
                                 layer=layer(top['n']),offset=offset,floats=len(vertices),matrix=matrix,materials=materials))
    missing=[dict(mesh_id=i,node_id=mapping[i][0]['id'],root=mapping[i][1]['n']) for i in sorted(set(mapping)-{r['id'] for r in rows})]
    model=dict(schema_version=1,kind='ironcad_native_mesh',units='m',title='RockPro · Epson EB-L630U',
               source_export_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
               source_ics_sha256=hashlib.sha256(Path(ics).read_bytes()).hexdigest() if ics else None,
               geometry_sha256=hashlib.sha256((output/'geometry.bin').read_bytes()).hexdigest(),
               playback_scope='illustrative layer assembly, not historical operation timing',
               missing_export_meshes=missing,elements=rows)
    (output/'model.json').write_text(json.dumps(model,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(meshes=len(rows),vertices=sum(r['floats']//3 for r in rows),output=str(output))))
    return model


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--export',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--source-ics',type=Path)
    a=p.parse_args();convert(a.export,a.output,a.source_ics)
