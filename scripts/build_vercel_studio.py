"""Build a clean Vercel demo from an explicit source/asset allowlist.

Never copy the checkout, company workbook, SQLite, client models or family bundles.
Run again into a new folder for each release; inspect manifest before deploy.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad import studio_parts,part_images,manufacturer_images,company_catalog,studio_examples


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve()
    if out.exists():raise ValueError('Use a new empty release directory; previous release stays preserved.')
    if not out.is_relative_to(ROOT/'artifacts'):raise ValueError('Release must stay inside ignored artifacts.')
    public=out/'public';public.mkdir(parents=True)
    def write(path,data):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    def cp(source,target):
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    package=ROOT/'Integracja/rockpro_cad';static=package/'reference_studio'
    # API has pure computation modules only: no project_store, executor or customer DB.
    modules=['configurator.py','studio_parts.py','studio_placement.py','studio_structure.py','studio_closures.py','studio_joints.py','source_parts.py','part_registry.py',
             'core_case/t1_mounting.py','core_case/machining_rules.py','core_case/profile_rules.py']
    for name in modules:cp(package/name,out/'Integracja/rockpro_cad'/name)
    (out/'Integracja/rockpro_cad/__init__.py').write_text('',encoding='utf-8')
    (out/'Integracja/rockpro_cad/core_case/__init__.py').write_text('',encoding='utf-8')
    cp(ROOT/'docs/catalog/hardware-reference.json',out/'docs/catalog/hardware-reference.json')
    cp(ROOT/'deploy/vercel/api/index.py',out/'api/index.py')
    names=['wizard.html','wizard.js','wizard.css','wizard3d.js','parts-picker.js','placement-editor.js','closure-editor.js','placement3d.js','structure3d.js',
           'placement_math.mjs','preview_math.mjs','scene-controls.js','viewport-ui.js','studio-shell.js','studio-shell.css','part-preferences.js','part-preferences.css','favicon.svg',
           'company-parts.html','company-parts.js','company-parts.css','style.css','cost-summary.js','cost_math.mjs']
    for name in names:cp(static/name,public/name)
    for name in ['three.module.min.js','three.core.min.js','OrbitControls.js','three-viewport-gizmo.js','LICENSE','three-viewport-gizmo.LICENSE','PROVENANCE.json']:
        cp(package/'viewer3d/vendor'/name,public/'vendor'/name)
    for name in ['cloud-storage.js','cloud.css','demo-library.js','photos.html','photos.js']:cp(ROOT/'deploy/vercel'/name,public/name)
    company_html=(public/'company-parts.html').read_text(encoding='utf-8').replace('<head>','<head><script src="cloud-storage.js"></script><link rel="stylesheet" href="cloud.css">').replace('Stan zapisany w przekazanym pliku. Ten widok nie rezerwuje ani nie zmienia zapasów.','Pełny wykaz części i materiałów z cenami z arkusza. Stany magazynowe nie są udostępniane online.')
    (public/'company-parts.html').write_text(company_html,encoding='utf-8')
    photo_html=(public/'photos.html').read_text(encoding='utf-8').replace('data-studio-page="company"','data-studio-page="photos"')
    (public/'photos.html').write_text(photo_html,encoding='utf-8')
    cp(ROOT/'deploy/vercel/demo-library.html',public/'index.html')
    examples=studio_examples.catalog();write(public/'examples.json',examples)
    for example in examples['items']:
        thumbnail=ROOT/'artifacts/studio-example-images'/(example['id']+'.png')
        if thumbnail.exists():cp(thumbnail,public/example['image'])
    html=(public/'wizard.html').read_text(encoding='utf-8').replace('<head>','<head><script src="cloud-storage.js"></script><link rel="stylesheet" href="cloud.css">')
    html=html.replace('Studio · koncepcja','Demo · zapis w przeglądarce').replace('Zapis w lokalnej bazie zachowuje kolejne rewizje. JSON pozwala przenieść koncepcję. To nie jest plik CAD.','Drafty i ulubione są zapisane tylko w tej przeglądarce. Pobierz JSON, żeby przekazać projekt lub zachować kopię. Wersja demo bez połączenia z IronCAD i ERP.')
    html=html.replace('lokalnej bazie','przeglądarce').replace('w bazie','w przeglądarce')
    (public/'wizard.html').write_text(html,encoding='utf-8')
    js=(public/'wizard.js').read_text(encoding='utf-8').replace('w lokalnej bazie','w tej przeglądarce').replace('w bazie','w przeglądarce')
    (public/'wizard.js').write_text(js,encoding='utf-8')
    # Only the generic base SKU definitions, never source-client candidates.
    catalog=studio_parts.catalog();catalog['items']=[r for r in catalog['items'] if not r.get('source_project') and not r['id'].startswith('source-') or r['id']=='source-caster-epson'];catalog['source_report']={}
    ids={r['id'] for r in catalog['items']}
    images={k:v for k,v in part_images.load(part_images.DEFAULT_FOLDER).items() if k in ids}
    part_images.decorate(catalog,images);manufacturer_images.decorate(catalog)
    photos=manufacturer_images.routes()
    photo_rows=[]
    photo_index=json.loads((manufacturer_images.DEFAULT_FOLDER/'index.json').read_text(encoding='utf-8')) if photos else {'images':{}}
    for key,photo in photos.items():
        cp(photo['path'],public/photo['metadata']['url'])
        row=photo_index['images'][key]
        photo_rows.append(dict(id=key,code=row['code'],manufacturer=row['manufacturer'],url=photo['metadata']['url'],page_url=row['page_url']))
    write(public/'manufacturer-photos.json',dict(items=photo_rows))
    for row in catalog['items']:
        image=row.get('image')
        if not image:continue
        asset=photos.get(row['id']) or images[row['id']]
        cp(asset['path'],public/image['url'])
        if image.get('mesh_url'):cp(images[row['id']]['mesh_path'],public/image['mesh_url'])
        # Keep attribution, without private native IDs/paths or source-project reports.
        if image['kind']=='cad_render':image['source']={'description':'Podgląd pojedynczej części katalogowej z lokalnego prototypu.'}
        row.pop('company_references',None)
    # User approved the full parts list and source prices for the cost summary.
    # Stock, consumption, orders and workbook itself remain local.
    company=company_catalog.catalog(catalog);company_rows=[];workbook_images=company_catalog.images()
    for row in company['items']:
        safe={key:copy.deepcopy(row.get(key)) for key in ('id','code','name','category','manufacturer','source_url','cutout_note','duplicate_code','geometry_candidates','price_raw','currency','unit')}
        image=row.get('image');safe['image']=None
        if image:
            asset=photos.get(row['id']) or dict(path=workbook_images['company-images/'+row['id']][0])
            target='company-images/'+row['id']+asset['path'].suffix.lower();cp(asset['path'],public/target)
            safe['image']=dict(url=target)
            if image.get('source'):safe['image'].update({k:copy.deepcopy(image[k]) for k in ('kind','label','source') if k in image})
        company_rows.append(safe)
    clean_company=dict(items=company_rows,source=dict(filename='Katalog części RockPro'),summary={key:copy.deepcopy(company['summary'][key]) for key in ('records','unique_codes','categories','duplicate_codes','cutout_notes','images')})
    write(public/'company-catalog.json',clean_company)
    company_catalog.picker_entries(catalog,clean_company)
    write(public/'catalog-parts.json',catalog)
    from rockpro_cad import configurator
    write(public/'options.json',dict(types=configurator.TYPES,faces=configurator.FACES))
    config=dict(version=2,framework=None,outputDirectory='public',buildCommand=None,
                functions={'api/index.py':{'excludeFiles':'public/**','maxDuration':30}},
                redirects=[{'source':'/','destination':'/wizard.html','permanent':False}],
                rewrites=[{'source':'/wizard/options','destination':'/options.json'},
                          {'source':'/company/catalog','destination':'/company-catalog.json'},
                          {'source':'/wizard/parts','destination':'/catalog-parts.json'},
                          {'source':'/wizard/preview','destination':'/api/index?endpoint=preview'},
                          {'source':'/wizard/convert','destination':'/api/index?endpoint=convert'}],
                headers=[{'source':'/(.*)','headers':[{'key':'X-Content-Type-Options','value':'nosniff'},
                          {'key':'Referrer-Policy','value':'strict-origin-when-cross-origin'},
                          {'key':'X-Robots-Tag','value':'noindex, nofollow'},
                          {'key':'Content-Security-Policy','value':"default-src 'self'; script-src 'self' 'sha256-"+__import__('base64').b64encode(hashlib.sha256(b'{"imports":{"three":"./vendor/three.module.min.js"}}').digest()).decode()+"'; style-src 'self'; img-src 'self' data: blob:; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"}]}])
    # Root opens the wizard; the library link gets the explicit demo library.
    shell=(public/'studio-shell.js').read_text(encoding='utf-8').replace("['library','./',","['library','index.html',").replace("['company','company-parts.html',","['photos','photos.html','Zdjęcia producentów','M3 3h18v18H3zM3 15l6-6 4 4 3-3 5 5'],['company','company-parts.html',")
    (public/'studio-shell.js').write_text(shell,encoding='utf-8')
    write(out/'vercel.json',config)
    (out/'requirements.txt').write_text('# Standard library only. No COM, SQLite driver service or CAD runtime.\n',encoding='utf-8')
    (out/'.python-version').write_text('3.12\n',encoding='utf-8')
    (public/'robots.txt').write_text('User-agent: *\nDisallow: /\n',encoding='utf-8')
    # Fail closed if sensitive records accidentally enter the public asset set.
    for file in public.rglob('*'):
        if not file.is_file():continue
        if file.suffix.lower() in ('.db','.sqlite3','.xlsx','.ics','.zip','.xlsb'):raise ValueError('Forbidden public asset')
        if file.suffix.lower() in ('.json','.js','.html'):
            value=file.read_text(encoding='utf-8')
            sensitive=['C:\\Users\\','C:/Users/','7d2616b00b3433def8c4c9f0339b429c076ca1f67313b21859ee2185e23c8924']
            if file.suffix.lower()=='.json':sensitive+=['cached_stock_raw','opening_stock_raw','cached_usage_raw','stock_cell']
            if any(s in value for s in sensitive):
                raise ValueError('Private path or workbook field in '+file.name)
    manifest=[dict(path=f.relative_to(out).as_posix(),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in out.rglob('*') if f.is_file()]
    write(out.parent/(out.name+'-manifest.json'),manifest)
    print(json.dumps(dict(folder=str(out),files=len(manifest),bytes=sum(f['bytes'] for f in manifest),parts=len(catalog['items']))))


if __name__=='__main__':main()
