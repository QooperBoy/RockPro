"""One-time local deployment: same registration, no configuration/data replacement."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
import winreg

REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'Integracja/rockpro_cad'
sys.path.insert(0,str(SOURCE.parent))
from rockpro_cad.cad_lock import cad_writer_lock

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    process=subprocess.run(['powershell.exe','-NoProfile','-Command',
        "if(Get-Process -Name IRONCAD -ErrorAction SilentlyContinue){exit 17}else{exit 0}"],capture_output=True)
    if process.returncode:raise RuntimeError('IronCAD must be closed before deployment')
    key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Classes\CLSID\{B7659903-7C95-4E26-923F-DB5119AD1460}\InprocServer32')
    uri=winreg.QueryValueEx(key,'CodeBase')[0]
    target=Path(urllib.request.url2pathname(urllib.parse.urlparse(uri).path)).resolve(strict=True)
    installed=(REPO.parent/'Integracja/rockpro_cad').resolve(strict=True)
    if (target.name!='RockPro.CAD.dll' or not target.is_relative_to(installed)
            or target.parent.parent.parent!=installed or target.parent.parent.name!='addin'):
        raise RuntimeError('Registered add-in is outside intended installation')
    binary=SOURCE/'addin/bin-verify-20261021T215524662684Z/RockPro.CAD.dll'
    if not binary.is_file():raise RuntimeError('Verified binary missing')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence=REPO/'artifacts'/('deployment-'+stamp)
    evidence.mkdir(exist_ok=False)
    rows=[]
    files=[SOURCE/'cad_lock.py']
    files += [SOURCE/'mcp'/name for name in ('server.py','worker.py','core_service.py')]
    files += [p for p in (SOURCE/'parts').glob('*.py') if not p.name.startswith('test_')]
    files += [p for p in (SOURCE/'core_case').rglob('*') if p.is_file() and p.suffix in ('.py','.cs','.json') and '__pycache__' not in p.parts and not p.name.startswith('test_')]
    files += list((SOURCE/'addin').glob('*.cs'))+[SOURCE/'addin/Build.ps1']
    db=installed/'data/projects.sqlite3'
    db_before=sha(db) if db.exists() else None
    report=dict(status='PREPARED',commit='158e2ef',registered_dll=str(target),
                registry_unchanged=True,config_preserved=True,files=rows)
    def checkpoint():
        temporary=evidence/'deployment.pending.json'
        with temporary.open('w',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,evidence/'deployment.json')
    checkpoint()
    with cad_writer_lock():
        if db.exists():
            original=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
            backup=sqlite3.connect(evidence/'projects.sqlite3')
            original.backup(backup)
            check=backup.execute('pragma integrity_check').fetchone()[0]
            original.close();backup.close()
            if check!='ok':raise RuntimeError('Database backup integrity failure')
        report['database_backup']='PASS' if db.exists() else 'NOT PRESENT'
        checkpoint()
        qa=installed/'qa/core-native-158e2ef'
        models=[(REPO/'artifacts/core-native/native-A-20261021-02/case_prototype.ics',qa/'case_prototype.ics'),
                (REPO/'artifacts/core-native/real-H7159-20261021-03/rigid_catalog_reuse.ics',qa/'H7159_native.ics')]
        if any(not src.is_file() for src,_ in models):raise RuntimeError('Verified native QA model missing')
        replacements=[(p,installed/p.relative_to(SOURCE)) for p in files]+models+[(binary,target)]
        for src,dst in replacements:
            relative=dst.relative_to(installed)
            old=sha(dst) if dst.is_file() else None
            if old is not None:
                backup_path=evidence/'runtime-before'/relative
                backup_path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(dst,backup_path)
                if sha(backup_path)!=old:raise RuntimeError('Runtime backup hash mismatch')
            row=dict(path=str(dst),before_sha256=old,after_sha256=sha(src),source=str(src),state='PREPARED',
                     created=old is None,backup=str(evidence/'runtime-before'/relative) if old else None)
            rows.append(row)
            # Durable inventory BEFORE replacing an existing or newly created path.
            # If replacement finishes but checkpoint fails, compare current SHA
            # to before/after to reconcile; never assume PREPARED means unchanged.
            checkpoint()
            dst.parent.mkdir(parents=True,exist_ok=True)
            temporary=dst.with_name(dst.name+'.deploy-'+uuid.uuid4().hex)
            shutil.copy2(src,temporary)
            if sha(temporary)!=sha(src):raise RuntimeError('Copy hash mismatch')
            os.replace(temporary,dst)
            if sha(dst)!=row['after_sha256']:raise RuntimeError('Installed hash mismatch')
            row['state']='APPLIED'
            checkpoint()
        if (sha(db) if db.exists() else None)!=db_before:
            raise RuntimeError('Database changed during code deployment')
    report.update(status='PASS',dll_sha256=sha(target),database_preserved=True,database_sha256=db_before)
    checkpoint()
    print(json.dumps(dict(status='PASS',report=str(evidence/'deployment.json'),dll_sha256=sha(target)),ensure_ascii=True),flush=True)

if __name__=='__main__':main()
