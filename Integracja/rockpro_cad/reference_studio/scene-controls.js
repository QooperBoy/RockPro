import * as THREE from './vendor/three.module.min.js';

// Same navigation in the wizard and all source viewers. Placement captures left only.
export function configureOrbit(controls){
 controls.enableDamping=true;
 controls.mouseButtons={LEFT:THREE.MOUSE.ROTATE,MIDDLE:THREE.MOUSE.ROTATE,RIGHT:THREE.MOUSE.PAN};
 controls.domElement.addEventListener('auxclick',e=>{if(e.button===1)e.preventDefault();});
 controls.domElement.title='Środkowy przycisk: obrót · Prawy: przesuwanie · Rolka: zbliżanie · Lewy: okucia / obrót pustego tła';
}

export function stopOrbitMotion(controls){
 const position=controls.object.position.clone(),target=controls.target.clone(),damping=controls.enableDamping;
 controls.enableDamping=false;controls.update(); // Flush public damping state without a camera jump.
 controls.object.position.copy(position);controls.target.copy(target);controls.enableDamping=damping;controls.update();
}
