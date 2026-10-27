// Offline geometry rules: no browser, IronCAD or customer model required.
import assert from 'node:assert/strict';
import {placement} from '../Integracja/rockpro_cad/reference_studio/preview_math.mjs';
const baseline=[0,0,0,1,1,1];
const near=(a,b)=>a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<1e-10));
const rigid=placement([.7,.7,.7,.8,.8,.8],baseline,[1.2,1.3,1.4]);
near(rigid.scale,[1,1,1]);
const wall=placement([0,0,0,.01,1,1],baseline,[1.2,1.3,1.4],[1,2]);
near(wall.scale,[1,1.3,1.4]);assert.equal(wall.destination[0],.005);
const opposite=placement([.99,0,0,1,1,1],baseline,[1.2,1.3,1.4],[1,2]);
assert.ok(Math.abs(opposite.destination[0]-1.195)<1e-10);
const profile=placement([0,0,0,1,.03,.03],baseline,[1.2,1.3,1.4],[0]);
near(profile.scale,[1.2,1,1]);
for(const axes of [[],[0],[1,2]]){const p=placement([.1,.2,.3,.5,.6,.7],baseline,[1,1,1],axes);near(p.center,p.destination);near(p.scale,[1,1,1]);}
const wheel=placement([.2,.2,-.2,.3,.3,-.1],baseline,[1.2,1.3,1.4]);
assert.equal(wheel.destination[2],wheel.center[2]);
console.log('PASS: rigid hardware, fixed wall thickness, profile section, opposite anchors, baseline restore, wheel floor offset');
