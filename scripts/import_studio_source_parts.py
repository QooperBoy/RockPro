"""Extract source-bound hardware candidates from existing verified preview datasets.

One explicitly selected representative per raw CAD code; other occurrences are
reported, never declared geometrically equivalent or added to purchasing BOMs.
No CAD calls, original file writes or automatic mounting approvals.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'))
from rockpro_cad.part_registry import metadata
from rockpro_cad.source_parts import digest

FAMILIES={
 'EG-0100':'profiles','EG-0300':'profiles','EG-0425':'profiles','EG-0500_1':'profiles','EG-0500_2':'profiles','EG-0581':'profiles',
 'C1341-30-33':'corners','C1346':'corners','C1351':'corners','40404':'corners','41076':'corners','41202':'corners','B1121':'braces','38081':'stacking_sockets',
 'H7159':'handles','H2026':'handles','H7165/10Z':'handles',
 '17251S_1':'latches','17251S_2':'latches','27083_1':'hinges','27083_2':'hinges','2643_1':'hinges','2643_2':'hinges','2605_1':'hinges','2605_2':'hinges',
 'L905-915':'hinges','L905-915_1':'hinges','L905-915_2':'hinges','37033':'wheels','37034':'wheels','W0962':'stacking_sockets','W0968z':'stacking_sockets','F1692':'wheel_pads',
 '205':'unclassified','220':'unclassified','3453':'unclassified','87952':'unclassified','88001D':'unclassified','E2215':'unclassified'}
LABELS={'profiles':'Profil','corners':'Narożnik','braces':'Wzmocnienie','handles':'Uchwyt','latches':'Komponent zamka',
 'hinges':'Zespół / komponent zawiasu','wheels':'Koło','stacking_sockets':'Gniazdo do piętrowania','wheel_pads':'Stopa',
 'unclassified':'Element — funkcja do potwierdzenia'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def thumbnail(spec,code,family,selected,blob):
    shown=selected
    hashes={hashlib.sha256(blob[e['offset']:e['offset']+e['floats']*8]).hexdigest() for e in selected}
    if family=='profiles' or (family in ('corners','braces') and len(hashes)==1) or code in ('E2215','L905-915'):
        chosen=max(selected,key=lambda e:max(e['bounds'][k+3]-e['bounds'][k] for k in range(3))) if family=='profiles' else selected[0]
        spec['node_ids']=[chosen['node_id']];shown=[chosen]
        if len(selected)>1:
            spec['label']='Render elementu zespołu · '+spec['label'].split(' · ')[-1]
            spec['source']+=' Obraz pokazuje jedną fizyczną podczęść, nie cały zespół ani kompletny SKU.'
    if family=='profiles':
        bounds=[[min(e['bounds'][k] for e in shown),max(e['bounds'][k+3] for e in shown)] for k in range(3)]
        axis=max(range(3),key=lambda k:bounds[k][1]-bounds[k][0])
        if bounds[axis][1]-bounds[axis][0]>.2:
            spec['crop']=dict(axis=axis,length_m=.12);spec['label']='Render fragmentu profilu · '+spec['label'].split(' · ')[-1]
    if code=='H7159':spec['direction']=[-3,-2,1.5]
    return spec


def extract(bundle,index_path,survey_path,output):
    bundle,index_path,output=Path(bundle),Path(index_path),Path(output)
    if output.exists():raise ValueError('Use a new output directory; preserve old catalogue packages')
    survey=json.loads(Path(survey_path).read_text(encoding='utf-8-sig'))
    if not survey.get('passed') or not survey.get('context_preserved') or any(not d['disk_unchanged'] for d in survey['documents']):
        raise ValueError('Read-only survey evidence is incomplete')
    observed={r['name'] for d in survey['documents'] for r in d['rows']}
    expected={k for k in FAMILIES if k in observed}
    manifest=json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    expected_sources={r['key']:r['sha256'] for r in manifest['models']}
    index=json.loads(index_path.read_text(encoding='utf-8'));candidates={};all_occurrences={};models={};inventories={}
    for key,relative in sorted(index['models'].items()):
        folder=(index_path.parent/relative).resolve();model=json.loads((folder/'model.json').read_text(encoding='utf-8'))
        inv_path=bundle/'native-02'/(key+'-inventory.json');inv=json.loads(inv_path.read_text(encoding='utf-8-sig'))
        if model.get('model_key',key)!=key or model['source_sha256']!=expected_sources.get(key) or model['inventory_sha256']!=sha(inv_path) or model['source_sha256']!=inv['source_sha256'] or model['geometry_sha256']!=sha(folder/'geometry.bin'):
            raise ValueError('Mixed or changed source dataset: '+key)
        models[key]=(folder,model);inventories[key]=inv
        roots=[r for r in inv['rows'] if r.get('name') in expected]
        for root in roots:
            # A repeated code on every leaf of the same named assembly is not a product per leaf.
            if any(parent['name']==root['name'] and root['path'].startswith(parent['path']+'/') for parent in roots):continue
            parts=[r for r in inv['rows'] if r['type']=='Z_ELEMENT_PART' and (r['path']==root['path'] or r['path'].startswith(root['path']+'/'))]
            rows=[e for e in model['elements'] if e['path'] in {r['path'] for r in parts}]
            entry=dict(project=key,root=root,part_paths=[r['path'] for r in parts],mesh_paths=[e['path'] for e in rows],
                contained_codes=sorted({r['name'] for r in roots if r['name']!=root['name'] and r['path'].startswith(root['path']+'/')}))
            all_occurrences.setdefault(root['name'],[]).append(dict(project=key,root_path=root['path'],source_sha256=inv['source_sha256'],part_count=len(parts),mesh_count=len(rows)))
            complete=bool(parts) and len(rows)==len(parts)
            previous=candidates.get(root['name'])
            if previous is None or (complete and not previous['complete']):candidates[root['name']]=dict(entry,complete=complete)
    output.mkdir(parents=True);items=[];renders=[];coverage=[]
    for code,choice in sorted(candidates.items()):
        key=choice['project'];folder,model=models[key];inv=inventories[key];root=choice['root']
        identity=dict(source_sha256=model['source_sha256'],inventory_sha256=model['inventory_sha256'],root_path=root['path'])
        part_id='source-'+digest(identity)[:24];target=output/'models'/part_id;target.mkdir(parents=True)
        raw=(folder/'geometry.bin').read_bytes();selected=[];blob=bytearray()
        for element in model['elements']:
            if element['path'] not in choice['mesh_paths']:continue
            e=copy.deepcopy(element);start=e['offset'];size=e['floats']*8;e['offset']=len(blob);e['root_id']=0
            blob.extend(raw[start:start+size]);selected.append(e)
        geometry_sha=hashlib.sha256(blob).hexdigest();(target/'geometry.bin').write_bytes(blob)
        subset=dict(schema_version=1,kind='ironcad_native_mesh',units='m',source_binding=identity,geometry_sha256=geometry_sha,elements=selected)
        (target/'model.json').write_text(json.dumps(subset,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        family=FAMILIES[code];meta=metadata(family) if family!='unclassified' else dict(family_id=family,stage_id=None,registry_version=1)
        row=dict(id=part_id,revision=1,sku=None,catalog_code_raw=code,name=code+' · '+LABELS[family]+' · '+key,
            manufacturer=None,aliases=[code],description='Wyodrębniony wariant z istniejącego projektu '+key+'.',
            note='Kod z nazwy CAD. Reprezentant jednego poddrzewa źródła; innych wystąpień nie uznano za identyczną geometrię. Brak odbioru montażu i jednostki zakupowej.',
            source_url=None,source_document='Lokalna ekstrakcja projektu '+key,source_checked_on='2026-10-27',source_project=key,source_binding=identity,
            selectable=choice['complete'],selection_blocker=None if choice['complete'] else 'Źródło nie ma pełnej geometrii tego poddrzewa.',
            cutout_status='unknown',mounting_status='unknown',geometry_status='source_geometry_reference' if choice['complete'] else 'source_incomplete',
            purchase_unit=None,automatic_placement_approved=False,production_approved=False,
            component_only=family in ('hinges','latches'),contained_codes=choice['contained_codes'],placement_geometry_mode='reference_marker',**meta)
        row['definition_sha256']=digest(row);items.append(row)
        if selected:
            spec=dict(id=part_id,filename=part_id,model=str((target/'model.json').resolve()),roots=[0],direction=[1,-2,1.6],
                label='Render źródłowy · '+key,source='Wyodrębnione poddrzewo '+code+' z projektu '+key+'. Rama montażu niepotwierdzona.')
            renders.append(thumbnail(spec,code,family,selected,blob))
        coverage.append(dict(code=code,selected_definition=part_id,selected_project=key,selected_root=root['path'],complete=choice['complete'],occurrences=all_occurrences[code]))
    report=dict(open_documents=len(survey['documents']),survey_sha256=sha(survey_path),context_preserved=True,
        read_only=True,source_codes_observed=len(expected),candidate_count=len(items),selectable_count=sum(r['selectable'] for r in items),
        source_codes_without_saved_geometry=sorted(expected-set(candidates)),policy='One explicitly selected source variant per raw code; no equivalence inferred from name',coverage=coverage)
    (output/'catalog.json').write_text(json.dumps(dict(schema='rockpro.source-parts/1',items=items,report=report),ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'render-mapping.json').write_text(json.dumps(dict(items=renders),ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='coverage'},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle');p.add_argument('index');p.add_argument('survey');p.add_argument('output');a=p.parse_args()
    extract(a.bundle,a.index,a.survey,a.output)
