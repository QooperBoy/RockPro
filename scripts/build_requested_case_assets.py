"""Build local concept-only display assets; never modify source CAD or the workbook."""
import hashlib,json,math,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad import studio_requested_parts as parts

class Mesh:
    def __init__(self):self.elements=[]
    def triangles(self,triangles,color):
        p=[];n=[]
        for a,b,c in triangles:
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            length=math.sqrt(sum(x*x for x in normal)) or 1
            for vertex in (a,b,c):p.extend(round(x/1000,8) for x in vertex);n.extend(round(x/length,6) for x in normal)
        self.elements.append(dict(positions=p,normals=n,materials=[dict(count=len(p)//3,color=color)]))
    def box(self,center,size,color):
        x,y,z=center;a,b,c=[s/2 for s in size]
        v=[(x+sx*a,y+sy*b,z+sz*c) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        self.triangles([(v[a],v[b],v[c]) for a,b,c in [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]],color)
    def cylinder(self,center,radius,height,color,hole=0):
        x,y,z=center;t=[];steps=32
        for j in range(steps):
            a=2*math.pi*j/steps;b=2*math.pi*(j+1)/steps
            def p(r,ang,zz):return(x+r*math.cos(ang),y+r*math.sin(ang),z+zz)
            p0,p1,p2,p3=p(radius,a,0),p(radius,b,0),p(radius,b,height),p(radius,a,height)
            t.extend([(p0,p1,p2),(p0,p2,p3)])
            for zz,flip in [(0,True),(height,False)]:
                q=[p(radius,a,zz),p(radius,b,zz),p(hole,b,zz),p(hole,a,zz)]
                t.extend([(q[0],q[2],q[1]),(q[0],q[3],q[2])] if flip else [(q[0],q[1],q[2]),(q[0],q[2],q[3])])
            if hole:t.extend([(p(hole,a,0),p(hole,a,height),p(hole,b,height)),(p(hole,a,0),p(hole,b,height),p(hole,b,0))])
        self.triangles(t,color)
    def ball_octant(self,radius,color):
        t=[]
        # A display dome, with 6 mm nominal outward projection. Not a measured
        # mounting datum; the real corner/foot clearance remains unapproved.
        def p(a,b):return [22-radius*math.sin(a)*math.cos(b),22-radius*math.sin(a)*math.sin(b),22-radius*math.cos(a)]
        for i in range(10):
            for j in range(10):
                a,b=i*math.pi/20,j*math.pi/20;c,d=(i+1)*math.pi/20,(j+1)*math.pi/20
                q=[p(a,b),p(c,b),p(c,d),p(a,d)]
                t.extend([(q[0],q[1],q[2]),(q[0],q[2],q[3])])
        self.triangles(t,color)
    def model(self):
        points=[e['positions'] for e in self.elements]
        bounds=[min(v for p in points for v in p[k::3]) for k in range(3)]+[max(v for p in points for v in p[k::3]) for k in range(3)]
        return dict(schema='rockpro.part-mesh/1',units='m',frame='mount.local_uvn',display_only=True,
          frame_status='dimensioned_concept_unconfirmed_mount',geometry_status='simplified_not_vendor_cad',elements=self.elements,bounds_m=bounds)

def build():
    folder=ROOT/'artifacts/studio-requested-parts/images';folder.mkdir(parents=True,exist_ok=True)
    company=json.loads((ROOT/'artifacts/erp-company-parts/catalog.json').read_text(encoding='utf-8'))
    companies={r['id']:r for r in company['items']};index=dict(schema='rockpro.part-images/1',images={})
    silver=0xbec9cf;black=0x252a2d
    for definition in parts.definitions():
        key=definition['id'];mesh=Mesh()
        if key==parts.CORNER:
            # Three stepped flanges and an octant dome; approximate outline only.
            mesh.ball_octant(28,silver)
            for axis in range(3):
                size=[39,30,1.8];center=[47.5,15,-.9]
                for arm in (False,True):
                    c=center[:];s=size[:]
                    if arm:c[0],c[1]=c[1],c[0];s[0],s[1]=s[1],s[0]
                    for _ in range(axis):c=[c[2],c[0],c[1]];s=[s[2],s[0],s[1]]
                    mesh.box(c,s,silver)
        elif key==parts.LATCH:
            # Split at the seam, with both dishes visible when the lid is removed.
            for sign in (-1,1):
                mesh.box([0,sign*43.5,-4],[127,85,10],black)
                mesh.box([0,sign*43.5,1.5],[108,66,3],0x383d40)
            mesh.cylinder([0,-30,3],21,3,black)
            mesh.box([0,-30,8],[46,10,7],black)
            mesh.box([0,8,4],[17,54,5],black)
            for x in (-55,55):
                for y in (-76,-45,-12,12,45,76):mesh.cylinder([x,y,1],2.4,1,0x738087)
        elif key==parts.VENT:
            mesh.box([0,0,-4],[178,127,1.2],black)
            for c,s in [([0,-57,1],[178,13,1.2]),([0,57,1],[178,13,1.2]),([-82,0,1],[14,101,1.2]),([82,0,1],[14,101,1.2])]:mesh.box(c,s,black)
            for x in [-50,-25,0,25,50]:
                mesh.box([x,0,1],[12,78,5],0x171b1e)
                mesh.box([x+5,0,4],[3,78,3],0x52595d)
            for x in [-79,0,79]:
                for y in [-56,56]:mesh.cylinder([x,y,2],2.5,1,0x738087)
        elif key==parts.FEET:mesh.cylinder([0,0,0],10,9,black,hole=2.2)
        else:
            mesh.box([15,-.7,.5],[30,1.4,1],silver);mesh.box([-.7,15,.5],[1.4,30,1],silver)
        model=mesh.model();model['source']=dict(url=definition['source_url'],note=definition['note'])
        file=folder/(key+'.mesh.json');file.write_text(json.dumps(model,separators=(',',':')),encoding='utf-8')
        if key in companies:
            image=ROOT/'artifacts/erp-company-parts'/companies[key]['image']['file']
        else:
            from PIL import Image,ImageDraw
            image=folder/'angle-concept.png';im=Image.new('RGB',(256,192),'#edf2ef');draw=ImageDraw.Draw(im)
            draw.line([(75,40),(75,145),(185,145)],fill='#7c9098',width=14);draw.text((30,165),'30 x 30 mm - KONCEPCJA',fill='#223c40');im.save(image)
        dest=folder/(key+image.suffix);shutil.copyfile(image,dest)
        index['images'][key]=dict(file=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),kind='manufacturer_photo' if key in companies else 'cad_render',
          label='Zdjęcie katalogowe; bryła 3D uproszczona' if key in companies else 'Pogląd profilu — przekrój 30 mm jest koncepcją',
          source=dict(description=definition['note'],url=definition['source_url']),mesh=dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    # Retain the complete source handle unchanged, associated with generic H2026.
    original=ROOT/'artifacts/studio-project-parts/images'
    for suffix in ('.png','.mesh.json'):shutil.copyfile(original/('source-012a6a363ff93545f036605a'+suffix),folder/('H2026'+suffix))
    index['images']['H2026']=dict(file='H2026.png',sha256=hashlib.sha256((folder/'H2026.png').read_bytes()).hexdigest(),kind='cad_render',
      label='Pełny uchwyt H2026 ze źródła; wykończenie Z do potwierdzenia',source=dict(description='Zachowana siatka H2026, bez skalowania i zmiany źródła.'),
      mesh=dict(file='H2026.mesh.json',sha256=hashlib.sha256((folder/'H2026.mesh.json').read_bytes()).hexdigest()))
    (folder/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    print(folder)

if __name__=='__main__':build()
