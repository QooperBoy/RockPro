"""Archive downloaded supplier STEP files and report coverage without approving CAD.

Only explicit browser-download evidence and pinned prior supplier imports are used.
No original files are moved, no archives are executed, no customer assemblies copied.
"""
import argparse
import collections
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import re
from urllib.parse import parse_qs,urlsplit
import zipfile

def digest(raw):return hashlib.sha256(raw).hexdigest()
def norm(s):return re.sub('[^A-Z0-9]','',str(s or '').upper())
def step_info(raw):
    if len(raw)>40*1024*1024:raise ValueError('STEP size limit exceeded')
    if not raw.lstrip().startswith(b'ISO-10303-21;') or b'END-ISO-10303-21;' not in raw:raise ValueError('Invalid STEP envelope')
    names=('MANIFOLD_SOLID_BREP','FACETED_BREP','SHELL_BASED_SURFACE_MODEL','ADVANCED_FACE','SHAPE_REPRESENTATION')
    entities={name:len(re.findall(rb'\b'+name.encode()+rb'\s*\(',raw)) for name in names}
    if not any(entities.values()):raise ValueError('No supported geometric entities in STEP')
    return dict(bytes=len(raw),sha256=digest(raw),entities=entities,validation='STEP container and entities checked; native CAD validation not run',mounting_approved=False,production_approved=False)

def safe_step_entries(raw):
    out=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(x.file_size for x in z.infolist())>160*1024*1024:raise ValueError('Archive size limit exceeded')
        for info in z.infolist():
            name=info.filename.replace('\\','/');p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or ':' in name or ((info.external_attr>>16)&0o170000)==0o120000:raise ValueError('Unsafe archive entry')
            if info.is_dir() or p.suffix.lower() not in ('.step','.stp'):continue
            if info.file_size>40*1024*1024:raise ValueError('STEP size limit exceeded')
            b=z.read(info);step_info(b);out.append((p.name,b))
    if not out:raise ValueError('Archive contains no valid STEP')
    return out

def write_preserved(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if digest(path.read_bytes())!=digest(raw):
            path=path.with_name(path.stem+'-'+digest(raw)[:12]+path.suffix)
            if path.exists() and digest(path.read_bytes())!=digest(raw):raise ValueError('Conflicting content hash')
    if not path.exists():path.write_bytes(raw)
    return path

def ingest(evidence,output):
    discovery=json.loads((evidence/'discovery.json').read_text(encoding='utf-8'))
    downloads=json.loads((evidence/'browser-downloads.json').read_text(encoding='utf-8'))
    old=evidence.parent/'requested-native-20261028/vendor-import-01/result.json'
    if old.exists():
        prior=json.loads(old.read_text(encoding='utf-8'))
        if not prior['passed']:raise ValueError('Prior supplier import did not pass')
        ids={'C1339-30':'686188','L944-537-10MOL3':'1239394','D0536-07':'875643'}
        for x in prior['outputs']:
            if x['key'] not in ids:continue
            file=Path(x['input']);raw=file.read_bytes()
            if digest(raw)!=x['input_sha256']:raise ValueError('Prior supplier STEP changed')
            downloads.append(dict(model_id=ids[x['key']],configuration=x['key'],result=str(file),source_url=x['input'],prior_supplier_import=True))
    assets=[];errors=[];seen=set()
    for row in downloads:
        try:
            source=Path(row['result']);raw=source.read_bytes();archive_hash=digest(raw)
            key=(row['model_id'],archive_hash)
            if key in seen:continue
            seen.add(key);folder=output/'Penn_Elcom'/row['model_id']
            entries=safe_step_entries(raw) if zipfile.is_zipfile(io.BytesIO(raw)) else [(source.name,raw)]
            archive=write_preserved(folder/('source-'+archive_hash[:16]+source.suffix.lower()),raw)
            for name,b in entries:
                info=step_info(b);name=re.sub(r'[^A-Za-z0-9._ -]','_',name)
                file=write_preserved(folder/name,b)
                assets.append(dict(model_id=row['model_id'],configuration=row.get('configuration'),heading=row.get('heading'),file=str(file.resolve()),original_archive=str(archive.resolve()),archive_sha256=archive_hash,source_url=row.get('source_url'),download_source=str(source),configuration_controls=row.get('controls'),**info))
        except Exception as exc:errors.append(dict(source=row.get('result'),model_id=row.get('model_id'),error=str(exc)))
    rows=[]
    protected={x['company_id']:x for x in json.loads((evidence/'adam-hall-downloads.json').read_text(encoding='utf-8'))} if (evidence/'adam-hall-downloads.json').exists() else {}
    for item in discovery['items']:
        ids={parse_qs(urlsplit(u).query).get('id',[''])[0] for u in item.get('cad_links',[]) if urlsplit(u).hostname=='www.3dcontentcentral.com'}
        references=[a for a in assets if a['model_id'] in ids]
        candidates=list(references)
        wanted=norm(item.get('primary_manufacturer_sku'));options={wanted,wanted[:-1]} if wanted.endswith(('K','Z')) else {wanted}
        explicit=[a for a in candidates if a.get('configuration') and norm(a['configuration']) in options]
        if explicit:candidates=explicit
        elif any(a.get('configuration_controls') and any(s['id'] not in ('ddFormats','ddVersions','ddUnits') for s in a['configuration_controls']['selects']) for a in candidates):candidates=[]
        status='downloaded_candidate' if candidates else ('configuration_needs_review' if references else 'model_download_pending' if ids else 'no_public_3d_link_found')
        if item['id'] in protected:status='supplier_3d_access_requires_login'
        if item['status']=='supplier_or_product_url_missing':status='supplier_or_model_not_identified'
        if item['category'] in ('Płyty i sklejki','Pianki i wykładziny'):status='parametric_raw_material'
        if item['status']=='other_supplier_requires_lookup':status='other_supplier_requires_lookup'
        if item['status']=='page_unavailable':status='product_page_unavailable'
        if candidates and item.get('identity')=='different_product_or_variant':status='downloaded_candidate_catalog_code_conflict'
        rows.append(dict(id=item['id'],code=item['code'],name=item['name'],category=item['category'],manufacturer=item['manufacturer'],source_url=item['source_url'],original_source_url=item.get('original_source_url'),primary_manufacturer_sku=item.get('primary_manufacturer_sku'),identity=item.get('identity'),status=status,asset_files=[a['file'] for a in candidates],reference_files=[a['file'] for a in references if a not in candidates],geometry_approved=False,mounting_approved=False,production_approved=False))
    report=dict(schema='rockpro.company-cad-assets/1',updated_at=datetime.now(timezone.utc).isoformat(),catalog_sha256=discovery['catalog_sha256'],summary=dict(records=len(rows),downloaded_model_definitions=len({(a['model_id'],a.get('configuration') or a['sha256']) for a in assets}),unique_step_files=len({a['sha256'] for a in assets}),coverage=dict(collections.Counter(r['status'] for r in rows)),errors=len(errors)),assets=assets,items=rows,errors=errors)
    output.mkdir(parents=True,exist_ok=True);(output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (output/'DOSTEPNOSC_MODELI.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,delimiter=';');writer.writerow(['Kod w Excelu','Nazwa','Kod producenta','Status','Pliki STEP','Referencje innego wariantu','Zatwierdzenie montażu'])
        for r in rows:writer.writerow([r['code'],r['name'],r['primary_manufacturer_sku'],r['status'],' | '.join(r['asset_files']),' | '.join(r['reference_files']),'NIE'])
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('evidence',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=ingest(a.evidence,a.output);print(json.dumps(r['summary']))
if __name__=='__main__':main()
