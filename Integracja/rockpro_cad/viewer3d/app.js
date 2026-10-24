import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';

const host=document.querySelector('#viewport'),status=document.querySelector('#status');
const layers=[['plywood','Sklejka'],['profiles','Profile aluminiowe'],['corners','Narożniki i wzmocnienia'],['closures','Zamki i zawiasy'],['handles','Uchwyty'],['wheels','Koła']];
const palette=['#408080','#458bc1','#a47c36','#9465b6','#cf6578','#637595'];
const groups=new Map(layers.map(([key])=>[key,new THREE.Group()]));
const modelGroup=new THREE.Group(),edges=[],materials=new Map();
let renderer,controls,camera,scene,center,radius,playing=false,timer=null;

function material(color){
 if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.53,metalness:color===0x408080 ? .05 : .35,side:THREE.DoubleSide}));
 return materials.get(color);
}
function showCamera(back=false){
 camera.position.copy(center).add(new THREE.Vector3(back?-1.45:1.45,back?1.8:-1.8,1.3).normalize().multiplyScalar(radius*1.15/Math.sin(Math.min(camera.fov*Math.PI/360,Math.atan(Math.tan(camera.fov*Math.PI/360)*camera.aspect)))));
 controls.target.copy(center);controls.update();
}
function visible(){
 const step=Number(document.querySelector('#progress').value);
 layers.forEach(([key],i)=>{groups.get(key).visible=i<step&&document.querySelector('#layer-'+key).checked;const row=document.querySelector('#layer-'+key).closest('label');row.classList.toggle('current',i===step-1);row.classList.toggle('pending',i>=step);row.querySelector('.count').textContent=i<step?'✓':'—';});
 document.querySelector('#step').textContent=step===6?'Cała skrzynia':step===0?'Początek':layers[step-1][1];
 document.querySelector('#play').textContent=playing?'❚❚ Pauza':'▶ Odtwórz';
}
function stop(){playing=false;clearInterval(timer);visible();}

async function init(){
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0xeff4f4);
 renderer.outputColorSpace=THREE.SRGBColorSpace;host.prepend(renderer.domElement);
 scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(38,1,.001,100);camera.up.set(0,0,1);
 controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;
 scene.add(new THREE.HemisphereLight(0xffffff,0x91a0a4,2.4));
 const key=new THREE.DirectionalLight(0xffffff,3);key.position.set(2,-3,5);scene.add(key);
 const fill=new THREE.DirectionalLight(0xc1d8df,1.5);fill.position.set(-3,2,2);scene.add(fill);
 scene.add(modelGroup);for(const group of groups.values())modelGroup.add(group);
 const data=await fetch('./model.json').then(r=>{if(!r.ok)throw Error('Brak modelu');return r.json();});
 if(data.kind!=='ironcad_native_mesh')throw Error('Nieznany format geometrii');
 const binary=await fetch('./geometry.bin').then(r=>{if(!r.ok)throw Error('Brak bufora geometrii');return r.arrayBuffer();});
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',binary)),v=>v.toString(16).padStart(2,'0')).join('');
 if(hash!==data.geometry_sha256)throw Error('Niezgodna suma kontrolna geometrii');
 let triangles=0;
 for(let i=0;i<data.elements.length;i++){
  const row=data.elements[i],geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(binary,row.offset,row.floats),3));
  geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(binary,row.offset+row.floats*4,row.floats),3));
  let start=0;const mats=[];
  for(const group of row.materials){geometry.addGroup(start,group.count,mats.length);mats.push(material(group.color));start+=group.count;}
  const mesh=new THREE.Mesh(geometry,mats);mesh.matrix.fromArray(row.matrix);mesh.matrixAutoUpdate=false;
  mesh.userData={id:row.node_id,root:row.root_id,originalMaterials:mats};
  const target=groups.get(row.layer);if(!target)throw Error('Nieprzypisana warstwa: '+row.layer);target.add(mesh);
  // Feature edges only; no triangulation wireframe across curved faces.
  const line=new THREE.LineSegments(new THREE.EdgesGeometry(geometry,35),new THREE.LineBasicMaterial({color:0x294348,transparent:true,opacity:.24}));
  mesh.add(line);edges.push(line);triangles+=row.floats/9;
  if(i%20===0){status.textContent=`Wczytywanie ${i+1}/${data.elements.length} części…`;await new Promise(requestAnimationFrame);}
 }
 modelGroup.updateMatrixWorld(true);
 const bounds=new THREE.Box3().setFromObject(modelGroup);center=bounds.getCenter(new THREE.Vector3());radius=bounds.getSize(new THREE.Vector3()).length()/2;
 if(!Number.isFinite(radius)||radius<=0)throw Error('Niepoprawny gabaryt');
 controls.minDistance=radius*.4;controls.maxDistance=radius*12;showCamera();controls.saveState();
 const floor=new THREE.Mesh(new THREE.PlaneGeometry(radius*8,radius*8),new THREE.MeshStandardMaterial({color:0xe7eeee,roughness:1}));floor.position.set(center.x,center.y,bounds.min.z-.006);scene.add(floor);
 for(const [key,label] of layers){
  const row=document.createElement('label');row.className='layer';row.style.borderLeft='5px solid '+palette[layers.findIndex(v=>v[0]===key)];const input=document.createElement('input');input.type='checkbox';input.id='layer-'+key;input.checked=true;input.onchange=visible;
  const count=document.createElement('span');count.className='count';count.textContent=groups.get(key).children.length;row.append(input,document.createTextNode(String(layers.findIndex(v=>v[0]===key)+1).padStart(2,'0')+' · '+label),count);document.querySelector('#layers').append(row);
 }
 status.textContent=`${data.elements.length} siatek · ${Math.round(triangles/1000)} tys. trójkątów\nEksport oryginalnej geometrii. Bez zmiany modelu ICS. ${data.missing_export_meshes?.length||0} węzły bez siatki w eksporcie.`;
 document.querySelector('#progress').oninput=()=>{stop();visible();};
 document.querySelector('#play').onclick=()=>{
  if(playing){stop();return;}playing=true;document.querySelector('#progress').value=0;visible();
  timer=setInterval(()=>{const p=document.querySelector('#progress');p.value=Number(p.value)+1;visible();if(Number(p.value)===6)stop();},950);
 };
 document.querySelector('#all').onclick=()=>{stop();for(const [key] of layers)document.querySelector('#layer-'+key).checked=true;document.querySelector('#progress').value=6;visible();};
 document.querySelector('#fit').onclick=()=>showCamera();document.querySelector('#front').onclick=()=>showCamera();document.querySelector('#back').onclick=()=>showCamera(true);
 document.querySelector('#colors').onchange=e=>{layers.forEach(([key],i)=>groups.get(key).children.forEach(mesh=>{mesh.material=e.target.checked?material(new THREE.Color(palette[i]).getHex()):mesh.userData.originalMaterials;}));};
 document.querySelector('#edges').onchange=e=>edges.forEach(line=>line.visible=e.target.checked);
 new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();showCamera();}).observe(host);
 visible();renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
 window.rockproView={loaded:true,meshCount:data.elements.length,layers:Object.fromEntries([...groups].map(([k,g])=>[k,g.children.length]))};
}
init().catch(error=>{const box=document.querySelector('#error');box.style.display='block';box.textContent='Nie można otworzyć widoku 3D: '+error.message;status.textContent='Błąd wczytywania — brak kompletnego podglądu';console.error(error);});
