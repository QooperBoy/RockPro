"""Restore a RockPro transfer snapshot into a new isolated directory only.

Checks archive members, hashes, SQLite integrity and the captured Git commit.
Does not configure an add-in, rewrite database paths or touch a CAD document.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import zipfile


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def restore(snapshot,output):
    snapshot=snapshot.resolve(strict=True);output=output.resolve()
    checks=json.loads((snapshot/'checksums.json').read_text(encoding='utf-8'))
    required={'manifest.json','projects.sqlite3','source-and-projects.zip','source.bundle'}
    if set(checks)!=required:raise ValueError('Exact supported snapshot files required')
    for name,expected in checks.items():
        if sha(snapshot/name)!=expected:raise ValueError('Snapshot checksum mismatch: '+name)
    manifest=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
    expected={r['path']:r for r in manifest['files']}
    if len(expected)!=len(manifest['files']):raise ValueError('Duplicate manifest path')
    output.mkdir(parents=True,exist_ok=False)
    restored=output/'files';restored.mkdir()
    with zipfile.ZipFile(snapshot/'source-and-projects.zip') as archive:
        members=archive.infolist()
        if {m.filename for m in members}!=set(expected) or len(members)!=len(expected):raise ValueError('Archive member set differs')
        if sum(m.file_size for m in members)>4*1024**3:raise ValueError('Restore exceeds 4 GiB limit')
        for member in members:
            target=(restored/member.filename).resolve()
            if (not target.is_relative_to(restored) or ':' in member.filename or
                member.is_dir() or (member.external_attr>>16)&0o170000==0o120000):raise ValueError('Unsafe archive member')
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(member) as source,target.open('xb') as dest:shutil.copyfileobj(source,dest)
            row=expected[member.filename]
            if target.stat().st_size!=row['size'] or sha(target)!=row['sha256']:raise ValueError('Restored file differs: '+member.filename)
    database=output/'projects.sqlite3';shutil.copyfile(snapshot/'projects.sqlite3',database)
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as conn:
        integrity=conn.execute('PRAGMA quick_check').fetchall()
        if integrity!=[('ok',)]:raise ValueError('Restored database integrity failed')
        project_count=conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
    history=output/'history'
    subprocess.run(['git','clone','--no-checkout',str(snapshot/'source.bundle'),str(history)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(history),'cat-file','-e',manifest['git_head']+'^{commit}'],check=True,capture_output=True)
    result=dict(passed=True,restored_files=len(expected),git_commit=manifest['git_head'],sqlite_quick_check='ok',
        project_rows=project_count,cad_open='NOT_RUN',addin_install='NOT_RUN',paths_migrated=False,
        original_snapshot_unchanged=all(sha(snapshot/name)==value for name,value in checks.items()))
    (output/'restore_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(restore(a.snapshot,a.output)))
