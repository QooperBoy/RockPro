"""Archive a verified private native prototype; never publish or overwrite snapshots."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def archive(plan_file, native_folder, presentation_folder, snapshot_tag='SNAPSHOT'):
    q=read(plan_file)
    native=Path(native_folder);presentation=Path(presentation_folder)
    r=read(native/'result.json');p=read(presentation/'result.json')
    if not r.get('passed') or not p.get('passed'):
        raise ValueError('Native and presentation checks must pass before archiving')
    model=Path(q['output']).resolve();project=model.parents[2]
    if model.parent.name!='Do_sprawdzenia' or model.parent.parent.name!='03_CAD':
        raise ValueError('Expected a review revision in its private project folder')
    if sha(q['source'])!=q['sha256']:
        raise ValueError('Reference source changed')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',snapshot_tag):
        raise ValueError('Invalid snapshot tag')
    snapshot=project/'04_Snapshoty'/(model.stem+'_'+snapshot_tag+'.ics')
    if snapshot.exists():
        raise FileExistsError('Snapshots are immutable by convention; select a new revision')
    snapshot.parent.mkdir(exist_ok=True)
    shutil.copy2(model,snapshot)
    if sha(snapshot)!=sha(model):
        raise ValueError('Snapshot copy verification failed')
    review=project/'06_Odbior';review.mkdir(exist_ok=True)
    shutil.copy2(presentation/'final.png',review/'01_zamknieta.png')
    for file in native.glob('*.png'):
        if file.name!='final.png':shutil.copy2(file,review/file.name)
    with (review/'PARAMETRY.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['Parametr','Równanie domyślne','Jednostka','Opis'])
        for x in q['parameters']:w.writerow([x['name'],x['expression'],'mm',x['notes']])
    rows={x['id']:x for x in q['inventory']}
    with (review/'MAPA_CZESCI.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['ID źródła','ID prototypu','Rodzaj','Nazwa źródłowa','Opis polski','Rodzic źródłowy'])
        for x in q['names']:
            i=x['id'];w.writerow([i,r['aliases'].get(str(i),i),rows[i]['type'],rows[i]['name'],x['name'],rows[i]['parent']])
    report=dict(status='PASS',production_approved=False,model=str(model),snapshot=str(snapshot),model_sha256=sha(model),source_sha256=q['sha256'],source_unchanged=True,
                controls=len(q['parameters']),physical_parts=len(q['parts']),dimensioned_parts=len(q['dimensions']),operations=len(q['operations']),
                native_evidence=str(native.resolve()),presentation_evidence=str(presentation.resolve()),checks=r['checks'],presentation=p)
    for dest in (project/'CURRENT.json',review/'WYNIKI_NATYWNE.json'):
        dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('plan');parser.add_argument('native');parser.add_argument('presentation')
    parser.add_argument('--snapshot-tag',default='SNAPSHOT')
    args=parser.parse_args();archive(args.plan,args.native,args.presentation,args.snapshot_tag)
