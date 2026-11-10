"""Import explicit reference archives without overwriting or moving originals.

All paths are validated before extraction. SHA256 is compared with a second
read from disk; ZIP CRC is verified by ZipFile while reading every entry.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from zipfile import ZipFile

PACKS = [
 ('wetransfer_kufer_2026-10-28_1124.zip','01_Kufry'),
 ('wetransfer_miksery_2026-10-28_1128.zip','02_Miksery'),
 ('wetransfer_racki_2026-10-28_1133.zip','03_Racki'),
 ('wetransfer_telewizory_2026-10-28_1139.zip','04_Telewizory'),
 ('wetransfer_serwisy-szufladowe_2026-10-28_1152.zip','05_Serwisy_szufladowe'),
]

def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def safe_target(root,name):
    path=PurePosixPath(name.replace('\\','/'))
    if path.is_absolute() or '..' in path.parts or ':' in name or not path.parts:
        raise ValueError('Unsafe ZIP path: '+name)
    for component in path.parts:
        if component.endswith((' ','.')) or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',component,re.I):
            raise ValueError('Invalid Windows filename: '+name)
    target=root.joinpath(*path.parts).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('Path outside library')
    return target

def import_archives(downloads,library):
    downloads=downloads.resolve(strict=True);library=library.resolve()
    if library.exists():raise ValueError('Use a new library folder; existing import must remain preserved')
    planned=[];seen=set();total=0
    for archive_name,category in PACKS:
        archive=downloads/archive_name
        with ZipFile(archive) as z:
            for info in z.infolist():
                target=safe_target(library/category/'oryginaly',info.filename)
                if ((info.external_attr>>16)&0o170000)==0o120000:raise ValueError('ZIP symlink rejected')
                if info.is_dir():continue
                key=str(target).casefold()
                if key in seen:raise ValueError('Duplicate Windows destination')
                seen.add(key);total+=info.file_size
                planned.append((archive,category,info.filename,info.file_size,info.CRC,target))
    if total>10*1024**3:raise ValueError('Import exceeds expected limit')
    if shutil.disk_usage(library.parent).free<total+1024**3:raise ValueError('Not enough free space')
    library.mkdir(parents=True)
    archives=[];files=[]
    for archive_name,category in PACKS:
        archive=downloads/archive_name
        archive_sha=sha_file(archive)
        archives.append(dict(file=str(archive),bytes=archive.stat().st_size,sha256=archive_sha,category=category))
        with ZipFile(archive) as z:
            for _,_,name,size,crc,target in [r for r in planned if r[0]==archive]:
                target.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
                with z.open(name) as src,target.open('xb') as dst:
                    for chunk in iter(lambda:src.read(1024*1024),b''):dst.write(chunk);h.update(chunk)
                if target.stat().st_size!=size or sha_file(target)!=h.hexdigest():raise ValueError('Extracted file mismatch')
                files.append(dict(category=category,archive=archive_name,archive_entry=name,
                    path=target.relative_to(library).as_posix(),bytes=size,crc32=f'{crc:08x}',sha256=h.hexdigest(),
                    role={'.ics':'model_3d_zrodlowy','.icd':'rysunek_2d_zrodlowy','.jpg':'zdjecie_montazowe','.txt':'opis_pusty' if not size else 'opis_zrodlowy'}.get(target.suffix.lower(),'plik_zrodlowy'),
                    native_open_test='NOT RUN',parametric_status='niezweryfikowany',production_approved=False))
        if sha_file(archive)!=archive_sha:raise ValueError('Source ZIP changed during import')
        print(category,'PASS',flush=True)
    result=dict(schema='rockpro.reference-library/1',imported_at=datetime.now(timezone.utc).isoformat(),
        files=len(files),models_3d=sum(r['role']=='model_3d_zrodlowy' for r in files),bytes=total,
        originals_preserved=True,archives=archives,items=files)
    (library/'INWENTARZ.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (library/'KATALOG_PROJEKTOW.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['Kategoria','Plik','Rodzaj','Ścieżka względna','Bajty','SHA256','Parametryzacja','Test otwarcia CAD'])
        for row in files:w.writerow([row['category'],Path(row['path']).name,row['role'],row['path'],row['bytes'],row['sha256'],row['parametric_status'],row['native_open_test']])
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('downloads',type=Path);p.add_argument('library',type=Path);a=p.parse_args()
    r=import_archives(a.downloads,a.library);print(json.dumps({k:r[k] for k in ('files','models_3d','bytes')}))
