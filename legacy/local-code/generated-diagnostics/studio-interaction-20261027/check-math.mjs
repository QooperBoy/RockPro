import fs from 'node:fs';import assert from 'node:assert/strict';
import {resolvePreview} from '../../Integracja/rockpro_cad/reference_studio/placement_math.mjs';
const cases=JSON.parse(fs.readFileSync(new URL('./math-fixtures.json',import.meta.url)));
for(const c of cases){const items=c.draft.placements.flatMap(g=>resolvePreview(g,c.model));assert.equal(items.length,c.model.placement.items.length);for(const item of items){const expected=c.model.placement.items.find(i=>i.id===item.id);for(let k=0;k<3;k++)assert.ok(Math.abs(item.position_mm[k]-expected.position_mm[k])<1e-6);assert.equal(item.rotation_deg,expected.rotation_deg);for(const [i,h]of (item.visual_halves??[]).entries())for(let k=0;k<3;k++)assert.ok(Math.abs(h.position_mm[k]-expected.visual_halves[i].position_mm[k])<1e-6);}}
console.log('PASS 5 Python/JS preview parity fixtures: handles, top front/rear, cabinet left/right');
