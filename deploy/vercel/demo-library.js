for(const button of document.querySelectorAll('[data-type]'))button.onclick=()=>{if(!confirm('Otworzyć nowy draft? Niezapisany szkic zostanie zastąpiony.'))return;const type=button.dataset.type,cover=(face,kind)=>({id:crypto.randomUUID(),label:face==='top'?'Wieko górne':'Klapa przednia',face,kind,depth_mm:face==='top'?45:40,hinge_edge:'high',requires:[],height_override:false});const draft={schema:'rockpro.configurator/3',name:'Nowa '+(type==='cabinet'?'szafa':'skrzynia'),type,internal_mm:[600,500,350],thickness_mm:9.8,cooperation:'independent',covers:type==='case'?[cover('top','hinged')]:type==='cabinet'?[cover('front','hinged')]:[cover('top','removable'),cover('front','removable')],hardware:[],placements:[]};localStorage.setItem('rockpro.configurator.recovery.v3',JSON.stringify({draft,storage:{id:null,revision:0},dirty:true}));location.href='wizard.html';};

const make=(tag,text)=>{const el=document.createElement(tag);if(text)el.textContent=text;return el;};
fetch('examples.json').then(r=>{if(!r.ok)throw Error('Nie można wczytać wzorców');return r.json();}).then(data=>{
 for(const example of data.items){
  const card=make('article');card.className='ready-example';card.dataset.example=example.id;
  const image=make('img');image.src=example.image;image.alt=example.name+' — podgląd 3D';image.width=800;image.height=600;card.append(image);
  const content=make('div');content.className='ready-example-content';content.append(make('h2',example.name),make('p',example.description));
  const specs=make('p','Wnętrze: '+example.internal_mm.join(' × ')+' mm · wieko '+example.lid_mm+' mm');specs.className='hint';content.append(specs);
  content.append(make('p','Części: '+example.total_count+' · uchwyty: '+example.handles+' · koła: '+example.wheels));
  const button=make('button','Otwórz kopię w 3D →');button.className='primary';button.dataset.openExample=example.id;
  button.onclick=async()=>{
   button.disabled=true;const status=document.getElementById('example-status');status.textContent='Przygotowanie kopii…';
   try{const response=await fetch('wizard/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({draft:example.draft,id:null,expected_revision:0})});const saved=await response.json();if(!response.ok)throw Error(saved.error);location.href='wizard.html?draft='+saved.id;}
   catch(error){status.textContent=error.message;button.disabled=false;}
  };
  content.append(button);card.append(content);document.getElementById('ready-examples').append(card);
 }
 document.getElementById('example-status').textContent='Otwarcie wzorca nie nadpisuje Twojego bieżącego szkicu ani zapisanych projektów.';
}).catch(error=>document.getElementById('example-status').textContent=error.message);
