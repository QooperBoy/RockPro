"""Snapshot the transposed company catalogue and embedded cell images, read-only."""
import collections
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sys
import xml.etree.ElementTree as E
import zipfile

MAIN='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS={'m':MAIN}


def column_number(text):
    value=0
    for c in text:value=value*26+ord(c)-64
    return value


def first_rows(z,path,limit,strings):
    rows={}
    with z.open(path) as f:
        for _,node in E.iterparse(f,events=['end']):
            if node.tag!='{'+MAIN+'}row':continue
            n=int(node.get('r'))
            if n>limit:break
            for cell in node:
                v=cell.find('m:v',NS);formula=cell.find('m:f',NS);kind=cell.get('t','n')
                text=v.text if v is not None else None
                if kind=='s' and text is not None:text=strings[int(text)]
                if kind=='inlineStr':text=''.join(t.text or '' for t in cell.iter('{'+MAIN+'}t'))
                rows[cell.get('r')]=dict(value=text,type=kind,formula_present=formula is not None,
                    formula=formula.text if formula is not None else None,vm=cell.get('vm'))
            node.clear()
    return rows


def cell_images(z):
    """Resolve vm -> value metadata -> rich value -> image relationship."""
    if 'xl/metadata.xml' not in z.namelist() or 'xl/richData/rdrichvalue.xml' not in z.namelist():return {}
    metadata=E.fromstring(z.read('xl/metadata.xml'))
    future=next(x for x in metadata if x.tag.endswith('}futureMetadata') and x.get('name')=='XLRICHVALUE')
    values=metadata.find('m:valueMetadata',NS)
    rich=E.fromstring(z.read('xl/richData/rdrichvalue.xml'))
    links=E.fromstring(z.read('xl/richData/richValueRel.xml'))
    rels={x.get('Id'):x for x in E.fromstring(z.read('xl/richData/_rels/richValueRel.xml.rels'))}
    result={}
    types=metadata.find('m:metadataTypes',NS)
    rich_type=next(i for i,x in enumerate(types,1) if x.get('name')=='XLRICHVALUE')
    for i,bk in enumerate(values,1):
        try:
            rc=bk.find('m:rc',NS)
            if int(rc.get('t'))!=rich_type:continue
            slot=int(rc.get('v'))
            rvb=next(x for x in future[slot].iter() if x.tag.endswith('}rvb'))
            value=rich[int(rvb.get('i'))];link_index=int(value[0].text)
            rid=links[link_index].get('{'+REL+'}id');relationship=rels[rid]
            if relationship.get('TargetMode')=='External':continue
            path=posixpath.normpath('xl/richData/'+relationship.get('Target'))
            if not path.startswith('xl/media/'):raise ValueError('Image outside embedded media')
            result[str(i)]=path
        except (IndexError,KeyError,ValueError,StopIteration):continue
    return result


def extract(path,output):
    path,output=Path(path),Path(output);output.mkdir(parents=True,exist_ok=True)
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    snapshot=output/'snapshots'/sha/'source.xlsx';snapshot.parent.mkdir(parents=True,exist_ok=True)
    if not snapshot.exists():snapshot.write_bytes(raw)
    if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=sha:raise ValueError('Snapshot checksum differs')
    with zipfile.ZipFile(snapshot) as z:
        strings=[''.join(t.text or '' for t in x.iter('{'+MAIN+'}t')) for x in E.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
        book=E.fromstring(z.read('xl/workbook.xml'))
        sheets={s.get('name'):s.get('{'+REL+'}id') for s in book.find('m:sheets',NS)}
        rels={x.get('Id'):x.get('Target') for x in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        target=rels[sheets['Stany magazynowe']]
        sheet_path=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
        cells=first_rows(z,sheet_path,12,strings);images=cell_images(z)
        def value(col,row):return cells.get(col+str(row),{}).get('value')
        if value('A',2)!='Opis' or value('A',9)!='Stany początkowe' or value('A',10)!='Pozostałe sztuki w magazynie':
            raise ValueError('Workbook layout changed; review column mapping before import')
        # Explicit order also covers columns BA..KB; first column A is a row label.
        codes={re.match('[A-Z]+',a)[0]:c['value'] for a,c in cells.items()
               if re.fullmatch('[A-Z]+5',a) and a!='A5' and c['value'] not in (None,'')}
        duplicate=collections.Counter(codes.values());rows=[];category=None;image_count=0
        known_bands={'Narożniki','Klamry','ZAMKI','Zawiasy','Uchwyty','MISKI, Wentylacje, Etykiety','Koła Nogi','Profile i listwy'}
        for col,code in sorted(codes.items(),key=lambda x:column_number(x[0])):
            band=value(col,1)
            if band in known_bands:category=band
            family=category
            if column_number('IF')<=column_number(col)<=column_number('JE'):family='Płyty i sklejki'
            if column_number(col)>=column_number('JF'):family='Pianki i wykładziny'
            ident='company-'+hashlib.sha256((col+'\0'+code).encode()).hexdigest()[:24]
            source_image=images.get(cells.get(col+'4',{}).get('vm'));image=None
            if source_image:
                data=z.read(source_image)
                suffix='.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if data.startswith(b'\xff\xd8\xff') else None
                if suffix and len(data)<=2*1024*1024:
                    file='images/'+sha[:16]+'/'+ident+suffix;dest=output/file;dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(data);image=dict(file=file,sha256=hashlib.sha256(data).hexdigest());image_count+=1
            url=value(col,3);url=url if isinstance(url,str) and url.startswith(('https://','http://')) else None
            rows.append(dict(id=ident,code=code,name=value(col,2) or code,category=family or 'Do klasyfikacji',
                manufacturer='Adam Hall' if url and 'adamhall.' in url else 'Penn Elcom' if url and 'penn-elcom.' in url else None,
                source_url=url,image=image,mass_raw=value(col,6),price_raw=value(col,7),currency=None,unit=None,
                cutout_note=value(col,8),opening_stock_raw=value(col,9),cached_stock_raw=value(col,10),
                cached_usage_raw=value(col,11),stock_is_formula=cells.get(col+'10',{}).get('formula_present',False),
                stock_error=value(col,10) if cells.get(col+'10',{}).get('type')=='e' else None,
                duplicate_code=duplicate[code]>1,source=dict(sheet='Stany magazynowe',column=col,code_cell=col+'5',stock_cell=col+'10',cutout_cell=col+'8'),
                geometry_approved=False,production_approved=False))
        core=E.fromstring(z.read('docProps/core.xml'))
        modified=next((x.text for x in core if x.tag.endswith('}modified')),None)
        package=dict(schema='rockpro.company-catalog/1',source=dict(filename=path.name,sha256=sha,workbook_modified_utc=modified,
                    imported_at=datetime.now(timezone.utc).isoformat(),stock_status='saved_formula_cache_not_live',original_unchanged=True),
                    items=rows,summary=dict(records=len(rows),unique_codes=len(duplicate),images=image_count,
                    duplicate_codes={k:v for k,v in duplicate.items() if v>1},cutout_notes=sum(bool(r['cutout_note']) for r in rows),
                    categories=dict(collections.Counter(r['category'] for r in rows))))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Original changed during import')
    target=output/'catalog.json';tmp=output/'catalog.json.tmp';tmp.write_text(json.dumps(package,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(target)
    print(json.dumps(package['summary'],ensure_ascii=True,indent=2));return package


if __name__=='__main__':extract(sys.argv[1],sys.argv[2])
