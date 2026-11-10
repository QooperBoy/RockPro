"""Convert downloaded supplier STEP into portable display assets, without IronCAD.

Run with an isolated cadquery-ocp==7.8.1.1 interpreter. No runtime dependency
is added to Studio. Inputs stay local; output contains vendor geometry only.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def sha(raw): return hashlib.sha256(raw).hexdigest()

def vendor_stl(path,step_path):
    """Use an alternate export of the same vendor model, only after scale checks."""
    from OCP.STEPControl import STEPControl_Reader
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    with zipfile.ZipFile(path) as z:
        entries=[i for i in z.infolist() if i.filename.lower().endswith('.stl')]
        if len(entries)!=1 or entries[0].file_size>40*1024*1024:raise ValueError('Ambiguous vendor STL')
        raw=z.read(entries[0])
    n=struct.unpack_from('<I',raw,80)[0]
    if len(raw)!=84+n*50 or n>250000:raise ValueError('Invalid binary STL')
    triangles=[]
    for i in range(n):
        values=struct.unpack_from('<12f',raw,84+i*50)
        triangles.append([list(values[j:j+3]) for j in (3,6,9)])
    points=[p for t in triangles for p in t]
    if not all(math.isfinite(x) for p in points for x in p):raise ValueError('Nonfinite STL')
    bounds=[min(p[k] for p in points) for k in range(3)]+[max(p[k] for p in points) for k in range(3)]
    reader=STEPControl_Reader();reader.ReadFile(str(step_path));reader.TransferRoots()
    box=Bnd_Box();BRepBndLib.AddOptimal_s(reader.OneShape(),box,False,False)
    step_bounds=box.Get()
    # Exporters may translate their origin. Compare all three physical extents,
    # without scaling, reflecting or changing the vendor part's orientation.
    if any(abs((bounds[k+3]-bounds[k])-(step_bounds[k+3]-step_bounds[k]))>.25 for k in range(3)):
        raise ValueError('Vendor STL/STEP dimensions or units differ')
    return triangles,sha(raw)

def tessellate(path):
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRep import BRep_Tool
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone: raise ValueError('STEP read failed')
    reader.TransferRoots(); shape = reader.OneShape()
    if shape.IsNull(): raise ValueError('Empty STEP')
    BRepMesh_IncrementalMesh(shape, .28, False, .26, False).Perform()
    faces = TopExp_Explorer(shape, TopAbs_FACE); triangles = []
    while faces.More():
        face = TopoDS.Face_s(faces.Current()); location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None:
            # Small vendor fillets can need a finer tolerance than the rest.
            BRepMesh_IncrementalMesh(face, .01, False, .1, False).Perform()
            mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None: raise ValueError('Face without triangles')
        transform = location.Transformation()
        points = [mesh.Node(i).Transformed(transform) for i in range(1, mesh.NbNodes()+1)]
        for i in range(1, mesh.NbTriangles()+1):
            ids = list(mesh.Triangle(i).Get())
            if face.Orientation() == TopAbs_REVERSED: ids[1], ids[2] = ids[2], ids[1]
            triangles.append([[points[j-1].X(), points[j-1].Y(), points[j-1].Z()] for j in ids])
        faces.Next()
    if not triangles or len(triangles)>250000: raise ValueError('Invalid triangle count')
    return triangles

def display_mesh(triangles, family, color):
    # Orientation is a display suggestion, never an approved mounting frame.
    points = [p for tri in triangles for p in tri]
    low = [min(p[k] for p in points) for k in range(3)]
    high = [max(p[k] for p in points) for k in range(3)]
    extent = [high[k]-low[k] for k in range(3)]
    n = min(range(3), key=lambda k: extent[k])
    v = 2 if n != 2 else 1
    u = next(k for k in range(3) if k not in (n,v))
    # u cross v = n. Preserve chirality of supplier geometry.
    sign = 1 if (u,v,n) in ((0,1,2),(1,2,0),(2,0,1)) else -1
    def project(p): return [sign*p[u],p[v],p[n]]
    projected = [[project(p) for p in tri] for tri in triangles]
    pts = [p for tri in projected for p in tri]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    planes = {}
    for a,b,c in projected:
        if max(a[2],b[2],c[2])-min(a[2],b[2],c[2]) < .001:
            z = round((a[2]+b[2]+c[2])/3, 2)
            planes[z] = planes.get(z,0)+abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
    plane = max(planes,key=planes.get) if planes else lo[2]
    center = [(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,plane]
    positions=[]; normals=[]
    for tri in projected:
        a,b,c=tri;ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)]
        normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        length=math.sqrt(sum(x*x for x in normal))
        if length<1e-10: continue
        for p in tri:
            positions.extend(round((p[k]-center[k])/1000,7) for k in range(3))
            normals.extend(round(x/length,5) for x in normal)
    return dict(schema='rockpro.part-mesh/1',units='m',frame='mount.local_uvn',display_only=True,
        frame_status='supplier_visual_frame_requires_mount_review',
        bounds_m=[(lo[k]-center[k])/1000 for k in range(3)]+[(hi[k]-center[k])/1000 for k in range(3)],
        elements=[dict(positions=positions,normals=normals,materials=[dict(color=color,count=len(positions)//3)])])

def thumbnail(mesh,path):
    from PIL import Image, ImageDraw
    image=Image.new('RGB',(360,280),'#eaf0ed'); draw=ImageDraw.Draw(image)
    data=mesh['elements'][0]; p=data['positions']; triangles=[]
    for i in range(0,len(p),9):
        pts=[p[j:j+3] for j in range(i,i+9,3)]
        triangles.append((sum(q[2]+q[1]*.4 for q in pts),[(q[0]+q[2]*.5,-q[1]-q[2]*.35) for q in pts],data['normals'][i:i+3]))
    allp=[p for _,tri,_ in triangles for p in tri];lo=[min(p[k] for p in allp) for k in range(2)];hi=[max(p[k] for p in allp) for k in range(2)]
    scale=min(300/max(hi[0]-lo[0],.001),220/max(hi[1]-lo[1],.001))
    for _,tri,normal in sorted(triangles,key=lambda x:x[0]):
        shade=int(100+100*abs(normal[2]*.7+normal[1]*.2+normal[0]*.1))
        draw.polygon([(180+(x-(lo[0]+hi[0])/2)*scale,140+(y-(lo[1]+hi[1])/2)*scale) for x,y in tri],fill=(shade,shade,min(255,shade+7)))
    image.save(path)

def family(row,sku):
    category=row.get('category',''); text=(row.get('name','')+' '+sku).lower()
    if category=='Narożniki':return 'corners'
    if category=='Profile i listwy':return 'profiles'
    if category=='Uchwyty':return 'handles'
    if category=='Zawiasy':return 'hinges'
    if category in ('ZAMKI','Klamry'):return 'latches'
    if category=='Koła Nogi':return 'wheels' if 'koł' in text else 'feet'
    return 'vents'

def prepare(manifest,output,fallback=None):
    data=json.loads(manifest.read_text(encoding='utf-8'));output.mkdir(parents=True,exist_ok=True)
    definitions=[];assets={};errors=[]
    for a in data['assets']:
        key='penn-'+a['model_id']+'-'+a['sha256'][:12]
        refs=[r for r in data['items'] if a['file'] in r['asset_files'] or a['file'] in r.get('reference_files',[])]
        if not refs: errors.append(dict(asset=key,error='Missing catalog evidence'));continue
        source=Path(a['file']);raw=source.read_bytes()
        if sha(raw)!=a['sha256']: raise ValueError('Changed STEP input')
        sku=a.get('configuration') or source.stem.removeprefix('Penn Elcom-')
        representative=refs[0];fam=family(representative,sku)
        try:
            gz=output/(key+'.mesh.json.gz');png=output/(key+'.png')
            mesh=json.loads(gzip.decompress(gz.read_bytes())) if gz.exists() else None
            if mesh is None or mesh.get('source_step_sha256')!=a['sha256']:
                alternate=fallback if fallback and fallback['model_id']==a['model_id'] else None
                triangles,stl_sha=vendor_stl(alternate['path'],source) if alternate else (tessellate(source),None)
                mesh=display_mesh(triangles,fam,0x333639 if sku.endswith('K') else 0xbac2c8)
                mesh['source_step_sha256']=a['sha256']
                if stl_sha:mesh['source_vendor_stl_sha256']=stl_sha
                payload=json.dumps(mesh,separators=(',',':'),allow_nan=False).encode()
                compressed=gzip.compress(payload,compresslevel=9,mtime=0);gz.write_bytes(compressed)
            else:compressed=gz.read_bytes()
            if not png.exists():thumbnail(mesh,png)
            assets[key]=dict(mesh=gz.name,mesh_sha256=sha(compressed),image=png.name,image_sha256=sha(png.read_bytes()),
                source_step_sha256=a['sha256'],model_id=a['model_id'],triangles=len(mesh['elements'][0]['positions'])//9,
                bounds_m=mesh['bounds_m'],source_vendor_stl_sha256=mesh.get('source_vendor_stl_sha256'))
            common=dict(asset_id=key,sku=sku,name=a.get('heading') or representative['name'],family_id=fam,
                source_url='https://www.3dcontentcentral.com/download-model.aspx?catalogid=6237&id='+a['model_id'],
                concept_envelope_mm=[round(1000*(mesh['bounds_m'][k+3]-mesh['bounds_m'][k]),3) for k in (0,1)])
            exact=[r for r in refs if r['status']=='downloaded_candidate' and a['file'] in r['asset_files']]
            # Only exact identities reuse Excel IDs. Variant conflicts remain distinct supplier definitions.
            if exact:
                for r in exact:definitions.append(dict(common,id=r['id'],sku=r['code'],name=r['name'],identity_status='exact_catalog_code',pricing_company_id=r['id']))
            else:definitions.append(dict(common,id='supplier-'+key,identity_status='supplier_variant_separate_from_excel'))
            print(key,'OK',len(compressed),flush=True)
        except Exception as exc:errors.append(dict(asset=key,error=str(exc)));print(key,'FAIL',str(exc),flush=True)
    result=dict(schema='rockpro.supplier-parts/1',assets=assets,items=definitions,errors=errors,
        scope='public_supplier_geometry_display_only')
    (output/'index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(assets=len(assets),definitions=len(definitions),errors=errors)),flush=True)
    return not errors

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('output',type=Path);p.add_argument('--fallback-stl',type=Path);a=p.parse_args()
    fallback=json.loads(a.fallback_stl.read_text(encoding='utf-8')) if a.fallback_stl else None
    sys.exit(0 if prepare(a.manifest,a.output,fallback) else 1)
