"""Optional native-run collector. Parent SDK jobs are spans, never fake leaf counts."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
from . import process_runs
from .part_registry import stage_for


def stamp():return datetime.now(timezone.utc).isoformat()


@contextmanager
def capture(descriptor, folder):
    if descriptor is None:
        yield
        return
    allowed={'run_id','origin','intervention_id','part_id','occurrence_id','stage','occurrence_map'}
    if not isinstance(descriptor,dict) or set(descriptor)-allowed:
        raise ValueError('Nieprawidłowe powiązanie śladu Studio')
    run_id=descriptor['run_id'];report=process_runs.read(run_id)
    if report['state']!='running':raise ValueError('Przebieg Studio nie jest aktywny')
    origin=descriptor.get('origin','unknown')
    if origin not in process_runs.ORIGINS:raise ValueError('Nieznane pochodzenie decyzji')
    mapping=descriptor.get('occurrence_map',{})
    if not isinstance(mapping,dict) or len(mapping)>1000:raise ValueError('Nieprawidłowa mapa wystąpień')
    for source,target in mapping.items():
        process_runs.identity(source);process_runs.identity(target)
    if origin=='ai' and not any(e['kind']=='intervention' and e['operation_id']==descriptor.get('intervention_id') for e in report['events']):
        raise ValueError('Najpierw zapisz powód interwencji AI')
    base={k:descriptor[k] for k in ('intervention_id','part_id','occurrence_id') if k in descriptor}
    operation='job/'+uuid.uuid4().hex;stage=descriptor.get('stage','native')
    start=time.perf_counter()
    def parent(status):
        return dict(base,event_id=uuid.uuid4().hex,kind='span',operation_id=operation,stage=stage,
            label='Wywołanie wykonawcy CAD — czas łączny',origin=origin,executor='sdk',status=status,
            duration_ms=(time.perf_counter()-start)*1000,timestamp_utc=stamp())
    process_runs.append(run_id,[parent('running')])
    try:
        yield
    except BaseException:
        process_runs.append(run_id,[parent('failed')])
        import_native_progress(run_id,folder,descriptor,operation)
        raise
    else:
        process_runs.append(run_id,[parent('success')])
        import_native_progress(run_id,folder,descriptor,operation)


def import_native_progress(run_id, folder, descriptor, prefix):
    path=Path(folder)/'native_progress.jsonl'
    if not path.exists():return 0  # Never infer per-part operations from an old receipt/BOM.
    raw=path.read_bytes()
    if len(raw)>8*1024*1024:raise ValueError('Ślad natywny przekracza 8 MB')
    if raw and not raw.endswith(b'\n'):raise ValueError('Niepełny ślad natywny')
    digest=hashlib.sha256(raw).hexdigest();events=[]
    supported={'native.create','native.regenerate','native.measure','native.save','native.reopen'}
    for index,line in enumerate(raw.splitlines()):
        row=json.loads(line)
        if row.get('operation') not in supported or row.get('event')!='operation_finished':continue
        status={'passed':'success','success':'success','failed':'failed','error':'failed','skipped':'skipped'}.get(row.get('result',{}).get('status'))
        if status is None:continue
        e=dict(event_id=f'{prefix}/line/{index}',operation_id=f'{prefix}/line/{index}',kind='operation',
            stage=descriptor.get('stage') or stage_for(row.get('family_id') or row.get('family') or row.get('occurrence_id')),label=row['operation'],
            origin=descriptor.get('origin','unknown'),executor='sdk',status=status,evidence_sha256=digest)
        # Association is explicit; no SKU matching or attribution from part names.
        for key in ('part_id','intervention_id'):
            if descriptor.get(key):e[key]=descriptor[key]
        occurrence=row.get('occurrence_id') or descriptor.get('occurrence_id')
        occurrence=descriptor.get('occurrence_map',{}).get(occurrence,occurrence)
        if occurrence:e['occurrence_id']=occurrence
        if row.get('duration_ms') is not None:e['duration_ms']=row['duration_ms']
        if row.get('timestamp_utc'):e['timestamp_utc']=row['timestamp_utc']
        events.append(e)
    for i in range(0,len(events),500):process_runs.append(run_id,events[i:i+500])
    return len(events)
