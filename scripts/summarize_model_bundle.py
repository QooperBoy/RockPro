"""Summarize source-pinned inventories; labels remain candidates, never a purchasing BOM."""
import argparse
from collections import Counter, defaultdict
import csv
import itertools
import json
import math
from pathlib import Path
import re
from survey_model_bundle import sha

CODE = re.compile(r'^(?:[A-Z]{1,3}[- ]?)?\d{3,}[A-Z0-9_./+ -]*$')


def code_candidate(name):
    return bool(CODE.fullmatch(name))


def world_box(row):
    """Conservative world AABB transformed from body-local AABB; not a cut contour."""
    b=row.get('bounds_local_m');m=row.get('world_mm')
    def finite_vector(v,n):
        return isinstance(v,list) and len(v)==n and all(type(x) in (int,float) and math.isfinite(x) for x in v)
    try:
        if (not finite_vector(b,6) or any(b[i]>b[i+3] for i in range(3)) or
                not isinstance(m,list) or len(m)!=4 or any(not finite_vector(r,4) for r in m) or
                any(abs(m[i][3])>1e-8 for i in range(3)) or abs(m[3][3]-1)>1e-8):
            return None
        points=[[sum(p[i]*1000*m[i][j] for i in range(3))+m[3][j] for j in range(3)]
                for p in itertools.product(*[(b[i],b[i+3]) for i in range(3)])]
    except OverflowError:
        return None
    if any(not math.isfinite(v) for p in points for v in p):return None
    return [min(p[i] for p in points) for i in range(3)]+[max(p[i] for p in points) for i in range(3)]


def summarize(data,key,known):
    rows=data['rows'];by_path={r['path']:r for r in rows}
    parts=[r for r in rows if r['type']=='Z_ELEMENT_PART']
    codes=defaultdict(list)
    for r in rows:
        name=r['name']
        if not code_candidate(name):continue
        segments=r['path'].split('/')
        # An assembly and its identically named solid represent one candidate occurrence.
        if any(by_path.get('/'.join(segments[:i]),{}).get('name')==name for i in range(1,len(segments))):continue
        codes[name].append(r['id'])
    boxes=[b for r in parts if (b:=world_box(r)) is not None]
    envelope=None if not boxes else [min(b[i] for b in boxes) for i in range(3)]+[max(b[i+3] for b in boxes) for i in range(3)]
    return {'key':key,'source':data['source'],'source_sha256':data['source_sha256'],
            'api_version':data['api_version'],'nodes':len(rows),'parts':len(parts),
            'assemblies':sum(r['type']=='Z_ELEMENT_ASSEMBLY' for r in rows),
            'valid_body_bounds':len(boxes),'read_errors':data['errors'],
            'history_complete':bool(parts) and all(isinstance(r.get('features'),list) for r in parts) and
                not any(e['field']=='feature_metadata' for e in data['errors']),
            'scene_envelope_conservative_mm':envelope,
            'scene_size_conservative_mm':None if envelope is None else [envelope[i+3]-envelope[i] for i in range(3)],
            'envelope_scope':'All scene parts including possible equipment/rendering/reference bodies; not certified case dimensions',
            'named_assemblies':[{'id':r['id'],'name':r['name'],'path':r['path']} for r in rows if r['type']=='Z_ELEMENT_ASSEMBLY' and r['path'].count('/')<=2],
            'catalog_candidates':[{'label':name,'occurrences':len(ids),'ids':ids,
                'new_label_vs_baselines':name not in known,'requires_plywood_cutout':'unknown',
                'sku_confirmed':False,'mount_template_confirmed':False} for name,ids in sorted(codes.items())],
            'executable_template':False,'production_approved':False}


def write_csv(path,fields,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as out:
        writer=csv.DictWriter(out,fieldnames=fields,delimiter=';');writer.writeheader();writer.writerows(rows)


def build(manifest_path,native,output,baselines):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    native,output=Path(native),Path(output);output.mkdir(parents=True,exist_ok=False)
    known=set();baseline_provenance=[]
    for path in baselines:
        path=Path(path);data=json.loads(path.read_text(encoding='utf-8-sig'))
        known.update(r['name'] for r in data['rows'] if code_candidate(r['name']))
        baseline_provenance.append({'path':str(path.resolve()),'inventory_sha256':sha(path)})
    summaries=[];flat=[];candidates=[]
    for model in manifest['models']:
        path=native/(model['key']+'-inventory.json')
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if data['source_sha256']!=model['sha256']:raise ValueError('Inventory revision mismatch')
        summary=summarize(data,model['key'],known);summary['name']=model['name'];summary['inventory_sha256']=sha(path);summaries.append(summary)
        for c in summary['catalog_candidates']:
            candidates.append({'model':model['key'],'nazwa_w_CAD':c['label'],
                'liczba_wystapien_kandydata':c['occurrences'],'id_zrodlowe':','.join(map(str,c['ids'])),
                'nowa_etykieta_wzgledem_T1_T2':c['new_label_vs_baselines'],
                'wyciecie_w_sklejce':'BRAK DANYCH','kod_producenta_potwierdzony':'NIE',
                'szablon_montazu':'DO MAPOWANIA','rola_konstruktora':''})
        for row in data['rows']:
            if row['type']!='Z_ELEMENT_PART':continue
            b=row.get('bounds_local_m');box=world_box(row)
            flat.append({'model':model['key'],'id':row['id'],'sciezka_drzewa':row['path'],'nazwa':row['name'],
                'obrys_lokalny_mm':json.dumps(None if b is None else [v*1000 for v in b]),
                'obrys_swiat_konserwatywny_mm':json.dumps(box),
                'liczba_operacji':len(row['features']) if 'features' in row else 'BRAK ODCZYTU',
                'operacje_ujemne_wewnatrz_czesci':sum(f['operation']=='Z_SUBTRACT' for f in row.get('features',[])),
                'material_potwierdzony':'BRAK DANYCH','rola_konstruktora':''})
    report={'contract':'rockpro-library-survey-draft-v1','models':summaries,
            'baseline_inventories':baseline_provenance,'parts_total':len(flat),
            'unique_code_candidates':sorted({c['nazwa_w_CAD'] for c in candidates}),
            'new_code_labels_vs_baselines':sorted({c['nazwa_w_CAD'] for c in candidates if c['nowa_etykieta_wzgledem_T1_T2']}),
            'production_approved':False,'executable_template':False}
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=list(flat[0]) if flat else ['model','id','sciezka_drzewa','nazwa','obrys_lokalny_mm',
        'obrys_swiat_konserwatywny_mm','liczba_operacji','operacje_ujemne_wewnatrz_czesci',
        'material_potwierdzony','rola_konstruktora']
    write_csv(output/'czesci.csv',fields,flat)
    if candidates:write_csv(output/'kandydaci_biblioteki.csv',list(candidates[0]),candidates)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('native',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline',type=Path,action='append',default=[])
    a=p.parse_args();r=build(a.manifest,a.native,a.output,a.baseline)
    print(json.dumps({'models':len(r['models']),'parts':r['parts_total'],'candidate_labels':len(r['unique_code_candidates']),'new_labels':len(r['new_code_labels_vs_baselines'])}))
