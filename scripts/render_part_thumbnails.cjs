// Render explicitly mapped, previously exported CAD parts. Never opens IronCAD.
// Usage: node render_part_thumbnails.cjs private-mapping.json output-folder
// Playwright is a development dependency; ROCKPRO_PLAYWRIGHT may point to it.
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const {chromium}=require(process.env.ROCKPRO_PLAYWRIGHT||'playwright');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
async function main(){
 const mapping=JSON.parse(fs.readFileSync(process.argv[2])),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
 const vendor=path.resolve(__dirname,'../Integracja/rockpro_cad/viewer3d/vendor');
 const models=new Map(),binaries=new Map();
 for(const spec of mapping.items){
  if(!/^[A-Za-z0-9_-]+$/.test(spec.filename))throw Error('Invalid output filename');
  if(!models.has(spec.model)){
   const model=JSON.parse(fs.readFileSync(spec.model)),binary=fs.readFileSync(path.join(path.dirname(spec.model),'geometry.bin'));
   if(hash(binary)!==model.geometry_sha256)throw Error('Source geometry checksum mismatch');
   models.set(spec.model,model);binaries.set(spec.model,binary);
  }
 }
 let current;
 const server=http.createServer((req,res)=>{
  const name=req.url.split('?')[0];let body,type;
  if(name==='/'){body='<html><body style="margin:0"></body></html>';type='text/html';}
  else if(['/three.module.min.js','/three.core.min.js'].includes(name)){body=fs.readFileSync(path.join(vendor,name.slice(1)));type='text/javascript';}
  else if(name==='/geometry.bin'){body=binaries.get(current.model);type='application/octet-stream';}
  else{res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':type});res.end(body);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
 try{
  browser=await chromium.launch({executablePath:process.env.ROCKPRO_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:720,height:480},deviceScaleFactor:1});
  await page.goto('http://127.0.0.1:'+server.address().port);
  const previous=fs.existsSync(path.join(out,'index.json'))?JSON.parse(fs.readFileSync(path.join(out,'index.json'))).images:{};
  const images=Object.fromEntries(Object.entries(previous).filter(([,v])=>v.kind==='manufacturer_photo'));
  for(const spec of mapping.items){
   current=spec;const model=models.get(spec.model),rows=model.elements.filter(e=>spec.roots.includes(e.root_id)&&(!spec.node_ids||spec.node_ids.includes(e.node_id)));
   if(!rows.length||spec.roots.some(id=>!rows.some(e=>e.root_id===id)))throw Error('Missing mapped part '+spec.id);
   await page.evaluate(async({rows,direction,crop})=>{
    const T=await import('/three.module.min.js'),binary=await fetch('/geometry.bin').then(r=>r.arrayBuffer());
    document.body.replaceChildren();const scene=new T.Scene();scene.background=new T.Color(0xf3f6f1);
    const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(720,480);renderer.outputColorSpace=T.SRGBColorSpace;document.body.append(renderer.domElement);
    const box=new T.Box3(),meshes=[];
    for(const row of rows){
     const g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(new Float32Array(binary,row.offset,row.floats),3));g.setAttribute('normal',new T.BufferAttribute(new Float32Array(binary,row.offset+row.floats*4,row.floats),3));
     let offset=0;const mats=row.materials.map((group,i)=>{g.addGroup(offset,group.count,i);offset+=group.count;return new T.MeshStandardMaterial({color:group.color===16777215?0xbec9cf:group.color,roughness:.46,metalness:.48,side:T.DoubleSide});});
     const mesh=new T.Mesh(g,mats);mesh.matrixAutoUpdate=false;mesh.matrix.fromArray(row.matrix);scene.add(mesh);g.computeBoundingBox();box.union(g.boundingBox.clone().applyMatrix4(mesh.matrix));meshes.push(mesh);
    }
    if(crop){const axis=['x','y','z'][crop.axis],mid=(box.min[axis]+box.max[axis])/2;box.min[axis]=mid-crop.length_m/2;box.max[axis]=mid+crop.length_m/2;const unit=new T.Vector3();unit[axis]=1;renderer.clippingPlanes=[new T.Plane(unit.clone(),-box.min[axis]),new T.Plane(unit.clone().negate(),box.max[axis])];}
    const center=box.getCenter(new T.Vector3()),size=box.getSize(new T.Vector3()),radius=size.length()/2;
    const camera=new T.PerspectiveCamera(32,1.5,radius/1000,radius*100);camera.up.set(0,0,1);camera.position.copy(center).add(new T.Vector3(...direction).normalize().multiplyScalar(radius/Math.sin(T.MathUtils.degToRad(16))*1.12));camera.lookAt(center);
    scene.add(new T.HemisphereLight(0xffffff,0x68776e,2.8));for(const [v,intensity]of [[[1,-2,3],3],[[-2,1,1],1.5]]){const light=new T.DirectionalLight(0xffffff,intensity);light.position.copy(center).add(new T.Vector3(...v).multiplyScalar(radius*3));scene.add(light);}
    // Thin silhouettes expose the actual bends and openings without changing geometry.
    for(const mesh of meshes){const edge=new T.LineSegments(new T.EdgesGeometry(mesh.geometry,35),new T.LineBasicMaterial({color:0x52636b,transparent:true,opacity:.35}));edge.matrixAutoUpdate=false;edge.matrix.copy(mesh.matrix);scene.add(edge);}
    renderer.render(scene,camera);window.finishThumbnail=()=>{renderer.dispose();renderer.forceContextLoss();};
   },{rows,direction:spec.direction,crop:spec.crop});
   const file=spec.filename+'.png';await page.screenshot({path:path.join(out,file)});await page.evaluate(()=>window.finishThumbnail());
   images[spec.id]={file,sha256:hash(fs.readFileSync(path.join(out,file))),kind:'cad_render',label:spec.label||'Render z modelu CAD',source:{geometry_sha256:model.geometry_sha256,roots:spec.roots,node_ids:rows.map(r=>r.node_id),crop:spec.crop||null,description:spec.source}};
   console.log(spec.id+' rendered');
  }
  fs.writeFileSync(path.join(out,'index.json'),JSON.stringify({schema:'rockpro.part-images/1',images},null,2));
 }finally{await browser?.close();await new Promise(r=>server.close(r));}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
