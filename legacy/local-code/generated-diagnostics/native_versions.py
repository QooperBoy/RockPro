import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('../Integracja/rockpro_cad/mcp').resolve()))
import worker,layout,project_store as store
pid=Path('../Integracja/rockpro_cad/qa/layout_demo_id.txt').read_text().strip()
r=layout.get_layout(pid)
report=worker.dispatch('change_dimensions_on_copy',dict(project_id=pid,changes=r['parameters'],layout_revision=r['revision'],label='Weryfikacja wersjonowania układu'))
assert report['passed'] and report['source_unchanged']
snap=report['snapshot'];assert snap['layout_binding']['sha256']==r['sha256']
next_version=layout.save_layout(pid,r['spec'],r['revision'])
assert layout.get_layout(pid,r['revision'])['sha256']==r['sha256']
assert store.list_snapshots(pid)['snapshots'][0]['layout_binding']==snap['layout_binding']
try:layout.save_layout(pid,r['spec'],r['revision'])
except ValueError as exc:assert 'LAYOUT_CONFLICT' in str(exc)
else:raise AssertionError('Stale save accepted')
evidence=dict(passed=True,source_unchanged=report['source_unchanged'],copy=report['copy'],snapshot_id=snap['id'],layout_binding=snap['layout_binding'],current_revision=next_version['revision'],integrity=store.list_snapshots(pid)['snapshots'][0]['integrity'])
Path('artifacts/native_versions.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(evidence,ensure_ascii=True))
