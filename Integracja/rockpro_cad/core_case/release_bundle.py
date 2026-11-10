"""ROC-21: immutable draft release packages bound to one model revision.

Checksums establish consistency, not constructor approval or manufacturing fit.
Only explicitly supplied files are copied. Missing deliverables remain visible.
"""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re

from ..part_registry import contract

ROLES={'ics','bom','drawing','production','viewer','evidence'}
BINDING={'project_id','revision_id','model_sha256','input_version','input_sha256',
         'rule_version','rules_sha256','template_version','template_sha256'}


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def _binding(binding):
    if not isinstance(binding,dict) or set(binding)!=BINDING:raise ValueError('Exact revision binding required')
    for key,value in binding.items():
        if not isinstance(value,str) or not value or len(value)>200:raise ValueError('Invalid binding field: '+key)
        if key.endswith('sha256') and not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('Invalid checksum: '+key)
    return dict(binding)


def _checks(checks):
    if not isinstance(checks,list) or not 1<=len(checks)<=100:raise ValueError('Explicit bounded check results required')
    names=set()
    for check in checks:
        if (not isinstance(check,dict) or set(check)!={'name','status'} or
            not isinstance(check['name'],str) or not check['name'].strip() or len(check['name'])>200 or
            check['status'] not in ('PASS','FAIL','NOT RUN')):raise ValueError('Invalid check')
        name=check['name'].strip().casefold()
        if name in names:raise ValueError('Duplicate check name')
        names.add(name)


def create_bundle(model,output,binding,artifacts,checks,manual_steps=None):
    binding=_binding(binding);model=Path(model).resolve(strict=True);output=Path(output).resolve()
    if output.exists():raise ValueError('Release directory already exists; use a new revision')
    if sha(model)!=binding['model_sha256']:raise ValueError('Model changed before release')
    if not isinstance(artifacts,list) or len(artifacts)>100:raise ValueError('Bounded artifacts required')
    _checks(checks)
    prepared=[];seen=set()
    for artifact in artifacts:
        if set(artifact)!={'role','path','model_sha256','revision_id'}:raise ValueError('Exact artifact binding required')
        if artifact['role'] not in ROLES-{'ics'}:raise ValueError('Unsupported artifact role')
        if any(artifact[k]!=binding[k] for k in ('model_sha256','revision_id')):raise ValueError('Artifact belongs to another model revision')
        path=Path(artifact['path']).resolve(strict=True)
        if not path.is_file() or path==model:raise ValueError('Artifact must be a distinct file')
        name=path.name
        if name.lower() in seen or name.lower() in ('manifest.json','model.ics'):raise ValueError('Duplicate or reserved release filename')
        seen.add(name.lower());prepared.append((artifact['role'],path,name,sha(path)))
    # Check every source before publishing a new directory. Recheck after copies
    # to detect a source changed while it was being read.
    output.mkdir(parents=True,exist_ok=False)
    files=[]
    sources=[('ics',model,'model.ics',binding['model_sha256'])]+prepared
    for role,source,name,expected in sources:
        destination=output/name
        with source.open('rb') as src,destination.open('xb') as dst:
            for block in iter(lambda:src.read(1024*1024),b''):dst.write(block)
        if sha(destination)!=expected or sha(source)!=expected:raise ValueError('Source changed during release: '+name)
        files.append(dict(role=role,path=name,sha256=expected,bytes=destination.stat().st_size,
                          revision_id=binding['revision_id'],model_sha256=binding['model_sha256']))
    pending=[role for role in ('bom','drawing','production') if role not in {r['role'] for r in files}]
    manifest=dict(schema_version=1,kind='rockpro_draft_release',binding=binding,
        created_at=datetime.now(timezone.utc).isoformat(),files=files,checks=checks,
        pending_roles=pending,manual_steps=list(manual_steps or []),
        production_approved=False,status='draft',source_model_unchanged=sha(model)==binding['model_sha256'])
    with (output/'manifest.json').open('x',encoding='utf-8') as stream:json.dump(manifest,stream,ensure_ascii=False,indent=2,allow_nan=False)
    return manifest


def inspect_bundle(manifest_path,current_model):
    manifest_path=Path(manifest_path).resolve(strict=True);folder=manifest_path.parent
    if manifest_path.stat().st_size>1024*1024:raise ValueError('Release manifest too large')
    data=json.loads(manifest_path.read_text(encoding='utf-8'))
    if data.get('kind')!='rockpro_draft_release' or data.get('schema_version')!=1:raise ValueError('Unknown release manifest')
    binding=_binding(data['binding']);errors=[];names=set()
    _checks(data.get('checks'))
    if not isinstance(data.get('files'),list) or not 1<=len(data['files'])<=101:raise ValueError('Invalid release files')
    for row in data['files']:
        if not isinstance(row,dict) or set(row)!={'role','path','sha256','bytes','revision_id','model_sha256'}:raise ValueError('Exact release file metadata required')
        if row['role'] not in ROLES:raise ValueError('Unknown release file role')
        if type(row['bytes']) is not int or row['bytes']<0:raise ValueError('Invalid release file size')
        if not isinstance(row['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('Invalid release file checksum')
        name=row['path']
        if (not isinstance(name,str) or Path(name).name!=name or '/' in name or '\\' in name or
                name in ('.','..') or name.lower() in names):raise ValueError('Unsafe or duplicate release path')
        names.add(name.lower());path=(folder/name).resolve()
        if not path.is_relative_to(folder):raise ValueError('Release path escapes package')
        if row['model_sha256']!=binding['model_sha256'] or row['revision_id']!=binding['revision_id']:
            errors.append(dict(path=name,code='REVISION_MISMATCH'))
        if row['role']=='ics' and row['sha256']!=binding['model_sha256']:
            errors.append(dict(path=name,code='MODEL_BINDING_MISMATCH'))
        if not path.is_file():errors.append(dict(path=name,code='FILE_MISSING'))
        elif path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:errors.append(dict(path=name,code='FILE_CHANGED'))
    stale=sha(current_model)!=binding['model_sha256']
    if stale:errors.append(dict(path=None,code='MODEL_REVISION_CHANGED'))
    roles={r['role'] for r in data['files']}
    if 'ics' not in roles:errors.append(dict(path=None,code='MODEL_COPY_MISSING'))
    if sum(r['role']=='ics' for r in data['files'])!=1:errors.append(dict(path=None,code='MODEL_COPY_COUNT'))
    pending=[role for role in ('bom','drawing','production') if role not in roles]
    return dict(valid=not errors,status='outdated' if stale else 'invalid' if errors else 'draft',
        revision_id=binding['revision_id'],errors=errors,pending_roles=pending,
        checks=data['checks'],manual_steps=data.get('manual_steps',[]),production_approved=False,
        ready_for_review=not errors and not pending and all(r['status']=='PASS' for r in data['checks']))


def prototype_bom(registry_report):
    """Managed root occurrence accounting; not physical or purchase quantities."""
    if registry_report.get('passed') is not True or registry_report['registry']!=contract():raise ValueError('Verified current registry report required')
    rows=registry_report['bindings'];ids=[r['occurrence_id'] for r in rows];nodes=[r['node_id'] for r in rows]
    if len(set(ids))!=len(ids) or len(set(nodes))!=len(nodes):raise ValueError('Duplicate managed occurrence identity')
    output=io.StringIO(newline='');writer=csv.writer(output,lineterminator='\n')
    writer.writerow(['occurrence_id','cad_node_id','family_id','stage_id','managed_root_occurrences','purchase_quantity','approved_material','model_sha256'])
    for row in rows:
        if contract()['families'].get(row['family_id'])!=row['stage_id']:raise ValueError('Family/stage mismatch')
        identity=row['occurrence_id']
        if not re.fullmatch(r'[A-Za-z0-9_/-]{1,160}',identity):raise ValueError('Unsafe occurrence ID')
        writer.writerow([identity,row['node_id'],row['family_id'],row['stage_id'],1,'','',registry_report['result_sha256']])
    return output.getvalue().encode('utf-8-sig')
